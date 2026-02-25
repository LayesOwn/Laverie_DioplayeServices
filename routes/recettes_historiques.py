"""
Bloc parallèle: saisie des recettes journalières historiques.
N'affecte pas la logique transactionnelle existante.
"""
from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from flask_wtf import FlaskForm
from sqlalchemy import extract
from wtforms import DateField, IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from config import Config
from extensions import db
from sqlalchemy import func
from models import RecetteJournaliereHistorique, Paiement, Transaction
from routes import require_admin

recettes_historiques_bp = Blueprint("recettes_historiques", __name__)


def _normalize_integer(value):
    if isinstance(value, str):
        return value.strip().replace(" ", "")
    return value


class RecetteHistoriqueForm(FlaskForm):
    date_recette = DateField("Date", default=date.today, validators=[DataRequired()])
    montant = IntegerField(
        "Recette du jour (XOF)",
        validators=[DataRequired(), NumberRange(min=0)],
        filters=[_normalize_integer],
    )
    notes = StringField("Notes", validators=[Optional(), Length(max=300)])
    submit = SubmitField("Enregistrer / Mettre à jour")


class ImportRecettesForm(FlaskForm):
    lignes = TextAreaField(
        "Import en bloc",
        validators=[DataRequired()],
        description="Format: YYYY-MM-DD;montant;notes (notes optionnelles).",
    )
    submit = SubmitField("Importer")


def _parse_bulk_line(line: str):
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None

    if ";" in raw:
        parts = [p.strip() for p in raw.split(";", 2)]
    else:
        parts = [p.strip() for p in raw.split(",", 2)]

    if len(parts) < 2:
        raise ValueError("format invalide")

    try:
        parsed_date = datetime.strptime(parts[0], "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("date invalide (attendu YYYY-MM-DD)") from exc

    montant_raw = parts[1].replace(" ", "")
    if "," in montant_raw or "." in montant_raw:
        raise ValueError("montant entier uniquement")

    try:
        montant = int(montant_raw)
    except ValueError as exc:
        raise ValueError("montant invalide") from exc

    if montant < 0:
        raise ValueError("montant négatif interdit")

    notes = parts[2] if len(parts) >= 3 else None
    return parsed_date, montant, notes


@recettes_historiques_bp.route("/")
@login_required
@require_admin
def index():
    form = RecetteHistoriqueForm()
    import_form = ImportRecettesForm()
    page = request.args.get("page", 1, type=int)
    annee = request.args.get("annee", type=int)

    query = RecetteJournaliereHistorique.query
    if annee:
        query = query.filter(extract("year", RecetteJournaliereHistorique.date_recette) == annee)

    pagination = query.order_by(RecetteJournaliereHistorique.date_recette.desc()).paginate(
        page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False
    )

    annees = [
        int(value)
        for (value,) in db.session.query(
            extract("year", RecetteJournaliereHistorique.date_recette)
        ).distinct().order_by(extract("year", RecetteJournaliereHistorique.date_recette).desc()).all()
        if value is not None
    ]

    return render_template(
        "recettes_historiques/index.html",
        form=form,
        import_form=import_form,
        recettes=pagination.items,
        pagination=pagination,
        annee=annee,
        annees=annees,
    )


@recettes_historiques_bp.route("/ajouter", methods=["POST"])
@login_required
@require_admin
def add():
    form = RecetteHistoriqueForm()
    if not form.validate_on_submit():
        for field_errors in form.errors.values():
            for msg in field_errors:
                flash(msg, "danger")
        return redirect(url_for("recettes_historiques.index"))

    entry = RecetteJournaliereHistorique.query.filter_by(date_recette=form.date_recette.data).first()
    if entry:
        entry.montant = int(form.montant.data)
        entry.notes = (form.notes.data or "").strip() or None
        flash(f"Recette du {entry.date_recette.strftime('%d/%m/%Y')} mise à jour.", "info")
    else:
        entry = RecetteJournaliereHistorique(
            date_recette=form.date_recette.data,
            montant=int(form.montant.data),
            notes=(form.notes.data or "").strip() or None,
        )
        db.session.add(entry)
        flash(f"Recette du {entry.date_recette.strftime('%d/%m/%Y')} ajoutée.", "success")

    db.session.commit()
    return redirect(url_for("recettes_historiques.index"))


@recettes_historiques_bp.route("/importer", methods=["POST"])
@login_required
@require_admin
def importer():
    form = ImportRecettesForm()
    if not form.validate_on_submit():
        flash("Le bloc d'import est vide.", "danger")
        return redirect(url_for("recettes_historiques.index"))

    created = 0
    updated = 0
    errors = []

    for idx, line in enumerate((form.lignes.data or "").splitlines(), start=1):
        try:
            parsed = _parse_bulk_line(line)
            if parsed is None:
                continue
            parsed_date, montant, notes = parsed
        except ValueError as exc:
            errors.append(f"Ligne {idx}: {exc}")
            continue

        existing = RecetteJournaliereHistorique.query.filter_by(date_recette=parsed_date).first()
        if existing:
            existing.montant = montant
            existing.notes = notes
            updated += 1
        else:
            db.session.add(
                RecetteJournaliereHistorique(
                    date_recette=parsed_date,
                    montant=montant,
                    notes=notes,
                )
            )
            created += 1

    db.session.commit()
    flash(f"Import terminé: {created} ajoutée(s), {updated} mise(s) à jour.", "success")
    if errors:
        flash(f"{len(errors)} ligne(s) ignorée(s). Exemple: {errors[0]}", "warning")

    return redirect(url_for("recettes_historiques.index"))


@recettes_historiques_bp.route("/<int:entry_id>/supprimer", methods=["POST"])
@login_required
@require_admin
def delete(entry_id: int):
    entry = db.get_or_404(RecetteJournaliereHistorique, entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash("Recette historique supprimée.", "warning")
    return redirect(url_for("recettes_historiques.index"))


@recettes_historiques_bp.route("/unifiees")
@login_required
def unifiees():
    """Vue unifiée : recettes historiques + recettes transactionnelles, par mois et par année."""
    from collections import defaultdict

    MOIS_LABELS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
                   "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]

    # ── 1. Recettes historiques par jour ──────────────────────────────────────
    hist_rows = RecetteJournaliereHistorique.query.all()
    hist_par_jour = {row.date_recette: float(row.montant) for row in hist_rows}

    # ── 2. Paiements transactionnels par jour ─────────────────────────────────
    paiement_rows = (
        db.session.query(
            Paiement.date_paiement,
            func.sum(Paiement.montant).label("total"),
        )
        .join(Transaction, Transaction.id == Paiement.transaction_id)
        .filter(Transaction.deleted_at == None)  # noqa: E711
        .group_by(Paiement.date_paiement)
        .all()
    )
    actuel_par_jour = {row.date_paiement: float(row.total) for row in paiement_rows}

    # ── 3. Fusion : agrégation par (année, mois) ──────────────────────────────
    # Stratégie : additionner les deux sources (pas de double-comptage prévu car
    # les dates historiques précèdent l'utilisation du système transactionnel)
    monthly = defaultdict(lambda: {"montant": 0.0, "has_hist": False, "has_actuel": False})

    for d, montant in hist_par_jour.items():
        key = (d.year, d.month)
        monthly[key]["montant"] += montant
        monthly[key]["has_hist"] = True

    for d, montant in actuel_par_jour.items():
        key = (d.year, d.month)
        monthly[key]["montant"] += montant
        monthly[key]["has_actuel"] = True

    # ── 4. Liste des années présentes ─────────────────────────────────────────
    years = sorted({k[0] for k in monthly.keys()}) if monthly else []

    # ── 5. Tableau mensuel (12 lignes × N années) ─────────────────────────────
    tableau = []
    annual_totals = {y: 0.0 for y in years}

    for m in range(1, 13):
        row = {"mois": MOIS_LABELS[m - 1], "num": m, "values": {}}
        for y in years:
            cell = monthly.get((y, m), {"montant": 0.0, "has_hist": False, "has_actuel": False})
            row["values"][y] = cell
            annual_totals[y] += cell["montant"]
        tableau.append(row)

    # ── 6. Totaux annuels avec indication de source ───────────────────────────
    annuel = []
    for y in years:
        has_hist = any(monthly.get((y, m), {}).get("has_hist") for m in range(1, 13))
        has_actuel = any(monthly.get((y, m), {}).get("has_actuel") for m in range(1, 13))
        if has_hist and has_actuel:
            source = "mixte"
        elif has_hist:
            source = "historique"
        else:
            source = "actuel"
        annuel.append({"annee": y, "total": annual_totals[y], "source": source})

    grand_total = sum(annual_totals.values())

    return render_template(
        "recettes_historiques/unifiees.html",
        tableau=tableau,
        years=years,
        annuel=annuel,
        grand_total=grand_total,
    )
