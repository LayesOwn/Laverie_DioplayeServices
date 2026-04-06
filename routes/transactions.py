"""
Blueprint Transactions - recettes clients avec gestion du credit.
"""
from datetime import date, datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DateField, FloatField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from config import Config
from extensions import db
from models import Client, Paiement, Service, Transaction
from routes import require_admin

transactions_bp = Blueprint("transactions", __name__)


def _normalize_phone(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _normalize_name(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _find_client_matches(query: str) -> list[Client]:
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    phone_query = _normalize_phone(normalized_query)
    name_query = _normalize_name(normalized_query)
    matches: list[tuple[int, str, Client]] = []

    for client in Client.query.order_by(Client.nom).all():
        client_phone = _normalize_phone(client.telephone)
        client_name = _normalize_name(client.nom)

        if phone_query and client_phone:
            if client_phone == phone_query:
                matches.append((0, client.nom, client))
                continue
            if phone_query in client_phone:
                matches.append((1, client.nom, client))
                continue

        if name_query and client_name:
            if client_name == name_query:
                matches.append((0, client.nom, client))
                continue
            if name_query in client_name:
                matches.append((2, client.nom, client))

    matches.sort(key=lambda item: (item[0], item[1]))
    return [client for _, _, client in matches]


def _find_existing_client_by_identity(name: str | None, phone: str | None) -> Client | None:
    normalized_phone = _normalize_phone(phone)
    normalized_name = _normalize_name(name)

    for client in Client.query.order_by(Client.nom).all():
        if normalized_phone and _normalize_phone(client.telephone) == normalized_phone:
            return client
        if normalized_name and _normalize_name(client.nom) == normalized_name:
            return client
    return None


def _build_clients_data() -> list[dict]:
    return [
        {
            "id": client.id,
            "nom": client.nom,
            "telephone": client.telephone or "",
            "adresse": client.adresse or "",
            "remarque": client.remarque or "",
            "solde_du": round(float(client.solde_du or 0), 2),
        }
        for client in Client.query.order_by(Client.nom).all()
    ]


class DecimalFloatField(FloatField):
    """FloatField qui accepte la virgule comme separateur decimal."""

    def process_formdata(self, valuelist):
        if not valuelist:
            return
        raw_value = (valuelist[0] or "").strip().replace(" ", "").replace(",", ".")
        if raw_value == "":
            self.data = None
            return
        try:
            self.data = float(raw_value)
        except ValueError as exc:
            self.data = None
            raise ValueError("Nombre invalide.") from exc


class StrictIntegerField(IntegerField):
    """IntegerField strict: refuse les decimales, accepte les espaces."""

    def process_formdata(self, valuelist):
        if not valuelist:
            return
        raw_value = (valuelist[0] or "").strip().replace(" ", "")
        if raw_value == "":
            self.data = None
            return
        if "," in raw_value or "." in raw_value:
            self.data = None
            raise ValueError("Le montant doit etre un entier.")
        try:
            self.data = int(raw_value)
        except ValueError as exc:
            self.data = None
            raise ValueError("Nombre entier invalide.") from exc


class TransactionForm(FlaskForm):
    client_search = StringField(
        "Recherche client",
        validators=[Optional(), Length(max=100)],
    )
    client_id = SelectField("Client existant", coerce=int, validators=[Optional()])

    new_client_nom = StringField("Nouveau client - Nom complet", validators=[Optional(), Length(max=100)])
    new_client_telephone = StringField("Nouveau client - Telephone", validators=[Optional(), Length(max=20)])
    new_client_adresse = StringField("Nouveau client - Adresse", validators=[Optional(), Length(max=200)])
    new_client_remarque = StringField("Nouveau client - Remarque", validators=[Optional(), Length(max=300)])

    service_id = SelectField("Service", coerce=int, validators=[DataRequired()])
    quantite = DecimalFloatField(
        "Quantite",
        default=1.0,
        validators=[DataRequired(), NumberRange(min=0.01)],
    )
    avance = StrictIntegerField(
        "Avance a la commande (XOF)",
        default=0,
        validators=[Optional(), NumberRange(min=0)],
    )
    date_transaction = DateField("Date", default=date.today, validators=[DataRequired()])
    notes = StringField("Notes", validators=[Optional()])
    submit = SubmitField("Enregistrer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id.choices = [(0, "-- Nouveau client --")] + [
            (c.id, f"{c.nom} - {c.telephone}" if c.telephone else c.nom)
            for c in Client.query.order_by(Client.nom).all()
        ]
        self.service_id.choices = [
            (s.id, f"{s.nom} - {s.prix_unitaire:,.0f} XOF")
            for s in Service.query.filter_by(actif=True).order_by(Service.nom).all()
        ]

    def validate(self, extra_validators=None):
        valid = super().validate(extra_validators=extra_validators)

        has_existing_client = bool(self.client_id.data and self.client_id.data > 0)
        has_search_query = bool((self.client_search.data or "").strip())
        has_new_client = bool((self.new_client_nom.data or "").strip())

        if has_existing_client and has_new_client:
            msg = "Choisissez un client existant OU saisissez un nouveau client."
            self.client_id.errors.append(msg)
            self.new_client_nom.errors.append(msg)
            valid = False
        elif not has_existing_client and not has_new_client and not has_search_query:
            msg = "Selectionnez, recherchez ou creez un client avant d'enregistrer la transaction."
            self.client_id.errors.append(msg)
            self.new_client_nom.errors.append(msg)
            valid = False

        return valid


class PaiementForm(FlaskForm):
    """Formulaire pour enregistrer un paiement partiel ou total sur une transaction."""

    montant = StrictIntegerField(
        "Montant recu (XOF)",
        validators=[DataRequired(), NumberRange(min=1)],
    )
    date_paiement = DateField("Date du paiement", default=date.today, validators=[DataRequired()])
    notes = StringField("Notes", validators=[Optional()])
    submit = SubmitField("Enregistrer le paiement")


@transactions_bp.route("/")
@login_required
def index():
    page = request.args.get("page", 1, type=int)
    filtre = request.args.get("filtre", "tous")

    query = Transaction.query.filter(
        Transaction.deleted_at == None  # noqa: E711
    ).order_by(Transaction.date_transaction.desc())

    if filtre == "non_soldes":
        query = query.filter(Transaction.montant_paye < Transaction.total)

    pagination = query.paginate(page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False)
    return render_template(
        "transactions/index.html",
        transactions=pagination.items,
        pagination=pagination,
        filtre=filtre,
    )


@transactions_bp.route("/nouvelle", methods=["GET", "POST"])
@login_required
def create():
    form = TransactionForm()

    def render_create():
        return render_template(
            "transactions/form.html",
            form=form,
            titre="Nouvelle transaction",
            clients_data=_build_clients_data(),
        )

    if form.validate_on_submit():
        service = db.session.get(Service, form.service_id.data)
        if not service:
            flash("Service introuvable.", "danger")
            return render_create()

        if form.quantite.data <= 0:
            flash("La quantite doit etre superieure a 0.", "danger")
            return render_create()

        client = None
        created_new_client = False
        reused_existing_client = False

        if form.client_id.data and form.client_id.data > 0:
            client = db.session.get(Client, form.client_id.data)
            if not client:
                flash("Client introuvable.", "danger")
                return render_create()
        elif (form.client_search.data or "").strip():
            matches = _find_client_matches(form.client_search.data)
            if len(matches) == 1:
                client = matches[0]
            elif len(matches) > 1:
                form.client_search.errors.append(
                    "Plusieurs clients correspondent. Choisissez-en un dans la liste."
                )
                return render_create()
        if client is None:
            existing_client = _find_existing_client_by_identity(
                form.new_client_nom.data,
                form.new_client_telephone.data,
            )
            if existing_client:
                client = existing_client
                reused_existing_client = True
            else:
                client = Client(
                    nom=(form.new_client_nom.data or "").strip(),
                    telephone=(form.new_client_telephone.data or "").strip() or None,
                    adresse=(form.new_client_adresse.data or "").strip() or None,
                    remarque=(form.new_client_remarque.data or "").strip() or None,
                )
                db.session.add(client)
                db.session.flush()
                created_new_client = True

        old_solde_du = float(client.solde_du or 0)
        quantite = float(form.quantite.data)
        total = int(round(float(service.prix_unitaire) * quantite))
        avance = int(form.avance.data or 0)
        avance = min(max(avance, 0), total)

        transaction = Transaction(
            client_id=client.id,
            service_id=form.service_id.data,
            quantite=quantite,
            total=total,
            montant_paye=0.0,
            date_transaction=form.date_transaction.data,
            notes=form.notes.data,
            created_by_id=current_user.id,
        )
        db.session.add(transaction)
        db.session.flush()

        if avance > 0:
            transaction.enregistrer_paiement(
                montant=avance,
                date_paiement=form.date_transaction.data,
                notes="Avance a la commande",
                created_by_id=current_user.id,
            )

        db.session.commit()

        if created_new_client:
            flash(f"Nouveau client '{client.nom}' cree et lie a la transaction.", "info")
        elif reused_existing_client or (form.client_search.data or "").strip():
            flash(f"Client existant reconnu : {client.nom}.", "info")

        flash(
            f"Transaction enregistree - Total : {total:,.0f} XOF | "
            f"Avance : {avance:,.0f} XOF | "
            f"Reste : {transaction.solde_restant:,.0f} XOF",
            "success",
        )

        if old_solde_du > 0:
            flash(
                f"Ancienne dette : {old_solde_du:,.0f} XOF | "
                f"Encours total client apres cette transaction : {client.solde_du:,.0f} XOF",
                "warning",
            )

        if avance <= 0:
            flash("Aucune avance : paiement prevu au retrait.", "warning")
        elif avance < total:
            flash("Avance partielle enregistree : solde a regler au retrait.", "info")

        if client.solde_du > 0:
            flash(
                f"Etat client : debiteur ({client.solde_du:,.0f} XOF restant du).",
                "warning",
            )
        else:
            flash("Etat client : solde (aucun montant du).", "success")
        return redirect(url_for("transactions.index"))

    return render_create()


@transactions_bp.route("/<int:tx_id>/paiement", methods=["GET", "POST"])
@login_required
def paiement(tx_id: int):
    tx = db.get_or_404(Transaction, tx_id)
    form = PaiementForm()

    if form.validate_on_submit():
        paye = tx.enregistrer_paiement(
            montant=form.montant.data,
            date_paiement=form.date_paiement.data,
            notes=form.notes.data,
            created_by_id=current_user.id,
        )
        if paye <= 0:
            flash("Aucun paiement enregistre (transaction deja soldee).", "warning")
            return redirect(url_for("clients.detail", client_id=tx.client_id))

        db.session.commit()
        flash(
            f"Paiement de {paye:,.0f} XOF enregistre. "
            f"Reste du : {tx.solde_restant:,.0f} XOF",
            "success",
        )
        return redirect(url_for("clients.detail", client_id=tx.client_id))

    historique = tx.paiements.order_by(Paiement.date_paiement.desc(), Paiement.created_at.desc()).all()
    return render_template("transactions/paiement.html", form=form, transaction=tx, historique=historique)


@transactions_bp.route("/<int:tx_id>/supprimer", methods=["POST"])
@login_required
@require_admin
def delete(tx_id: int):
    tx = db.get_or_404(Transaction, tx_id)
    client_id = tx.client_id
    tx.deleted_at = datetime.utcnow()
    db.session.commit()
    flash("Transaction deplacee dans la corbeille.", "warning")
    return redirect(url_for("clients.detail", client_id=client_id))


@transactions_bp.route("/corbeille")
@login_required
@require_admin
def corbeille():
    page = request.args.get("page", 1, type=int)
    pagination = (
        Transaction.query.filter(Transaction.deleted_at != None)  # noqa: E711
        .order_by(Transaction.deleted_at.desc())
        .paginate(page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False)
    )
    return render_template(
        "transactions/corbeille.html",
        transactions=pagination.items,
        pagination=pagination,
    )


@transactions_bp.route("/<int:tx_id>/restaurer", methods=["POST"])
@login_required
@require_admin
def restaurer(tx_id: int):
    tx = db.get_or_404(Transaction, tx_id)
    tx.deleted_at = None
    db.session.commit()
    flash("Transaction restauree.", "success")
    return redirect(url_for("transactions.corbeille"))


@transactions_bp.route("/api/service-prix/<int:service_id>")
@login_required
def api_service_prix(service_id: int):
    service = db.get_or_404(Service, service_id)
    return jsonify({"prix": service.prix_unitaire, "nom": service.nom})
