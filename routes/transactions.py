"""
Blueprint Transactions - Recettes clients avec gestion du crédit
"""
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, FloatField, DateField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange
from extensions import db
from models import Transaction, Client, Service, Paiement
from config import Config

transactions_bp = Blueprint("transactions", __name__)


class TransactionForm(FlaskForm):
    client_id = SelectField("Client", coerce=int, validators=[DataRequired()])
    service_id = SelectField("Service", coerce=int, validators=[DataRequired()])
    quantite = IntegerField("Quantité", default=1, validators=[DataRequired(), NumberRange(min=1)])
    montant_paye = FloatField(
        "Montant payé maintenant (XOF)",
        default=0.0,
        validators=[Optional(), NumberRange(min=0)],
    )
    date_transaction = DateField("Date", default=date.today, validators=[DataRequired()])
    notes = StringField("Notes", validators=[Optional()])
    submit = SubmitField("Enregistrer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id.choices = [(c.id, c.nom) for c in Client.query.order_by(Client.nom).all()]
        self.service_id.choices = [
            (s.id, f"{s.nom} - {s.prix_unitaire:,.0f} XOF")
            for s in Service.query.filter_by(actif=True).order_by(Service.nom).all()
        ]


class PaiementForm(FlaskForm):
    """Formulaire pour enregistrer un paiement partiel/total sur une transaction."""

    montant = FloatField("Montant reçu (XOF)", validators=[DataRequired(), NumberRange(min=1)])
    date_paiement = DateField("Date du paiement", default=date.today, validators=[DataRequired()])
    notes = StringField("Notes", validators=[Optional()])
    submit = SubmitField("Enregistrer le paiement")


@transactions_bp.route("/")
@login_required
def index():
    page = request.args.get("page", 1, type=int)
    filtre = request.args.get("filtre", "tous")

    query = Transaction.query.order_by(Transaction.date_transaction.desc())
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
        total = service.prix_unitaire * form.quantite.data
        montant_paye = min(form.montant_paye.data or 0, total)

        transaction = Transaction(
            client_id=form.client_id.data,
            service_id=form.service_id.data,
            quantite=form.quantite.data,
            total=total,
            montant_paye=0.0,
            date_transaction=form.date_transaction.data,
            notes=form.notes.data,
        )
        db.session.add(transaction)
        db.session.flush()

        if montant_paye > 0:
            transaction.enregistrer_paiement(
                montant=montant_paye,
                date_paiement=form.date_transaction.data,
                notes="Paiement initial",
            )

        db.session.commit()

        flash(
            f"Transaction enregistrée - Total : {total:,.0f} XOF | "
            f"Payé : {montant_paye:,.0f} XOF | "
            f"Reste : {transaction.solde_restant:,.0f} XOF",
            "success",
        )
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

    historique = (
        tx.paiements.order_by(Paiement.date_paiement.desc(), Paiement.created_at.desc()).all()
    )
    return render_template("transactions/paiement.html", form=form, transaction=tx, historique=historique)


@transactions_bp.route("/<int:tx_id>/supprimer", methods=["POST"])
@login_required
def delete(tx_id: int):
    tx = db.get_or_404(Transaction, tx_id)
    client_id = tx.client_id
    db.session.delete(tx)
    db.session.commit()
    flash("Transaction supprimée.", "warning")
    return redirect(url_for("clients.detail", client_id=client_id))


@transactions_bp.route("/api/service-prix/<int:service_id>")
@login_required
def api_service_prix(service_id: int):
    service = db.get_or_404(Service, service_id)
    return jsonify({"prix": service.prix_unitaire, "nom": service.nom})
