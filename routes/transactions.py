"""
Blueprint Transactions - Recettes clients avec gestion du crédit.
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


class DecimalFloatField(FloatField):
    """FloatField qui accepte la virgule comme séparateur décimal."""

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
    """IntegerField strict: refuse les décimales, accepte les espaces."""

    def process_formdata(self, valuelist):
        if not valuelist:
            return
        raw_value = (valuelist[0] or "").strip().replace(" ", "")
        if raw_value == "":
            self.data = None
            return
        if "," in raw_value or "." in raw_value:
            self.data = None
            raise ValueError("Le montant doit être un entier.")
        try:
            self.data = int(raw_value)
        except ValueError as exc:
            self.data = None
            raise ValueError("Nombre entier invalide.") from exc


class TransactionForm(FlaskForm):
    client_id = SelectField("Client existant", coerce=int, validators=[Optional()])

    new_client_nom = StringField("Nouveau client - Nom complet", validators=[Optional(), Length(max=100)])
    new_client_telephone = StringField("Nouveau client - Téléphone", validators=[Optional(), Length(max=20)])
    new_client_adresse = StringField("Nouveau client - Adresse", validators=[Optional(), Length(max=200)])
    new_client_remarque = StringField("Nouveau client - Remarque", validators=[Optional(), Length(max=300)])

    service_id = SelectField("Service", coerce=int, validators=[DataRequired()])
    quantite = DecimalFloatField(
        "Quantité",
        default=1.0,
        validators=[DataRequired(), NumberRange(min=0.01)],
    )
    avance = StrictIntegerField(
        "Avance à la commande (XOF)",
        default=0,
        validators=[Optional(), NumberRange(min=0)],
    )
    date_transaction = DateField("Date", default=date.today, validators=[DataRequired()])
    notes = StringField("Notes", validators=[Optional()])
    submit = SubmitField("Enregistrer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id.choices = [(0, "-- Nouveau client --")] + [
            (c.id, c.nom) for c in Client.query.order_by(Client.nom).all()
        ]
        self.service_id.choices = [
            (s.id, f"{s.nom} - {s.prix_unitaire:,.0f} XOF")
            for s in Service.query.filter_by(actif=True).order_by(Service.nom).all()
        ]

    def validate(self, extra_validators=None):
        valid = super().validate(extra_validators=extra_validators)

        has_existing_client = bool(self.client_id.data and self.client_id.data > 0)
        has_new_client = bool((self.new_client_nom.data or "").strip())

        if has_existing_client and has_new_client:
            msg = "Choisissez un client existant OU saisissez un nouveau client."
            self.client_id.errors.append(msg)
            self.new_client_nom.errors.append(msg)
            valid = False
        elif not has_existing_client and not has_new_client:
            msg = "Sélectionnez un client existant ou saisissez le nom du nouveau client."
            self.client_id.errors.append(msg)
            self.new_client_nom.errors.append(msg)
            valid = False

        return valid


class PaiementForm(FlaskForm):
    """Formulaire pour enregistrer un paiement partiel/total sur une transaction."""

    montant = StrictIntegerField(
        "Montant reçu (XOF)",
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
    if form.validate_on_submit():
        service = db.session.get(Service, form.service_id.data)
        if not service:
            flash("Service introuvable.", "danger")
            return render_template("transactions/form.html", form=form, titre="Nouvelle transaction")

        if form.quantite.data <= 0:
            flash("La quantité doit être supérieure à 0.", "danger")
            return render_template("transactions/form.html", form=form, titre="Nouvelle transaction")

        client = None
        created_new_client = False

        if form.client_id.data and form.client_id.data > 0:
            client = db.session.get(Client, form.client_id.data)
            if not client:
                flash("Client introuvable.", "danger")
                return render_template("transactions/form.html", form=form, titre="Nouvelle transaction")
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
                notes="Avance à la commande",
                created_by_id=current_user.id,
            )

        db.session.commit()

        if created_new_client:
            flash(f"Nouveau client '{client.nom}' créé et lié à la transaction.", "info")

        flash(
            f"Transaction enregistrée - Total : {total:,.0f} XOF | "
            f"Avance : {avance:,.0f} XOF | "
            f"Reste : {transaction.solde_restant:,.0f} XOF",
            "success",
        )

        if avance <= 0:
            flash("Aucune avance: paiement prévu au retrait.", "warning")
        elif avance < total:
            flash("Avance partielle enregistrée: solde à régler au retrait.", "info")

        if client.solde_du > 0:
            flash(
                f"État client: débiteur ({client.solde_du:,.0f} XOF restant dû).",
                "warning",
            )
        else:
            flash("État client: soldé (aucun montant dû).", "success")
        return redirect(url_for("transactions.index"))

    return render_template("transactions/form.html", form=form, titre="Nouvelle transaction")


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
            flash("Aucun paiement enregistré (transaction déjà soldée).", "warning")
            return redirect(url_for("clients.detail", client_id=tx.client_id))

        db.session.commit()
        flash(
            f"Paiement de {paye:,.0f} XOF enregistré. "
            f"Reste dû : {tx.solde_restant:,.0f} XOF",
            "success",
        )
        return redirect(url_for("clients.detail", client_id=tx.client_id))

    historique = tx.paiements.order_by(Paiement.date_paiement.desc(), Paiement.created_at.desc()).all()
    return render_template("transactions/paiement.html", form=form, transaction=tx, historique=historique)


@transactions_bp.route("/<int:tx_id>/supprimer", methods=["POST"])
@login_required
def delete(tx_id: int):
    tx = db.get_or_404(Transaction, tx_id)
    client_id = tx.client_id
    tx.deleted_at = datetime.utcnow()
    db.session.commit()
    flash("Transaction déplacée dans la corbeille.", "warning")
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
    flash("Transaction restaurée.", "success")
    return redirect(url_for("transactions.corbeille"))


@transactions_bp.route("/api/service-prix/<int:service_id>")
@login_required
def api_service_prix(service_id: int):
    service = db.get_or_404(Service, service_id)
    return jsonify({"prix": service.prix_unitaire, "nom": service.nom})
