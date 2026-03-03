"""
Blueprint Clients - CRUD, historique et solde.
"""
from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from config import Config
from extensions import db
from models import Client, Service, Transaction
from routes import require_admin

clients_bp = Blueprint("clients", __name__)


class StrictIntegerField(IntegerField):
    """IntegerField qui accepte les espaces mais refuse les décimales."""

    def process_formdata(self, valuelist):
        if not valuelist:
            return
        raw = (valuelist[0] or "").strip().replace(" ", "")
        if raw == "":
            self.data = None
            return
        if "," in raw or "." in raw:
            self.data = None
            raise ValueError("Le montant doit être un entier.")
        try:
            self.data = int(raw)
        except ValueError as exc:
            self.data = None
            raise ValueError("Nombre entier invalide.") from exc


class ClientForm(FlaskForm):
    # ---- Infos client ----
    nom = StringField("Nom complet", validators=[DataRequired(), Length(1, 100)])
    telephone = StringField("Téléphone", validators=[Optional(), Length(max=20)])
    adresse = StringField("Adresse", validators=[Optional(), Length(max=200)])
    remarque = StringField("Remarque", validators=[Optional(), Length(max=300)])

    # ---- Première transaction (optionnelle) ----
    service_id = SelectField("Service", coerce=int, validators=[Optional()])
    montant_paye = StrictIntegerField(
        "Montant payé (XOF)",
        validators=[Optional(), NumberRange(min=0)],
    )
    date_transaction = DateField("Date de la transaction", validators=[Optional()])

    submit = SubmitField("Enregistrer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_id.choices = [(0, "-- Aucune transaction --")] + [
            (s.id, f"{s.nom}  —  {s.prix_unitaire:,.0f} XOF")
            for s in Service.query.filter_by(actif=True).order_by(Service.nom).all()
        ]


@clients_bp.route("/")
@login_required
def index():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "")

    query = Client.query.order_by(Client.created_at.desc())
    if search:
        query = query.filter(Client.nom.ilike(f"%{search}%"))

    pagination = query.paginate(page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False)
    return render_template(
        "clients/index.html",
        clients=pagination.items,
        pagination=pagination,
        search=search,
    )


@clients_bp.route("/nouveau", methods=["GET", "POST"])
@login_required
def create():
    form = ClientForm()
    if form.validate_on_submit():
        client = Client(
            nom=form.nom.data.strip(),
            telephone=form.telephone.data.strip() if form.telephone.data else None,
            adresse=form.adresse.data.strip() if form.adresse.data else None,
            remarque=form.remarque.data.strip() if form.remarque.data else None,
        )
        db.session.add(client)
        db.session.flush()

        # ---- Transaction optionnelle ----
        if form.service_id.data and form.service_id.data > 0:
            service = db.session.get(Service, form.service_id.data)
            if service:
                total = int(round(service.prix_unitaire))
                avance = int(form.montant_paye.data or 0)
                avance = min(max(avance, 0), total)
                date_tx = form.date_transaction.data or date.today()

                transaction = Transaction(
                    client_id=client.id,
                    service_id=service.id,
                    quantite=1.0,
                    total=total,
                    montant_paye=0.0,
                    date_transaction=date_tx,
                    created_by_id=current_user.id,
                )
                db.session.add(transaction)
                db.session.flush()

                if avance > 0:
                    transaction.enregistrer_paiement(
                        montant=avance,
                        date_paiement=date_tx,
                        notes="Paiement à la création",
                        created_by_id=current_user.id,
                    )

                flash(
                    f"Transaction enregistrée — Total : {total:,.0f} XOF | "
                    f"Payé : {avance:,.0f} XOF | "
                    f"Reste : {transaction.solde_restant:,.0f} XOF",
                    "info",
                )

        db.session.commit()
        flash(f"Client '{client.nom}' ajouté avec succès.", "success")
        return redirect(url_for("clients.index"))

    return render_template("clients/form.html", form=form, titre="Nouveau client", client=None)


@clients_bp.route("/<int:client_id>/modifier", methods=["GET", "POST"])
@login_required
def edit(client_id: int):
    client = db.get_or_404(Client, client_id)
    form = ClientForm(obj=client)

    if form.validate_on_submit():
        client.nom = form.nom.data.strip()
        client.telephone = form.telephone.data.strip() if form.telephone.data else None
        client.adresse = form.adresse.data.strip() if form.adresse.data else None
        client.remarque = form.remarque.data.strip() if form.remarque.data else None
        db.session.commit()
        flash("Client mis à jour.", "success")
        return redirect(url_for("clients.index"))

    return render_template("clients/form.html", form=form, titre="Modifier le client", client=client)


@clients_bp.route("/<int:client_id>/supprimer", methods=["POST"])
@login_required
@require_admin
def delete(client_id: int):
    client = db.get_or_404(Client, client_id)
    nom = client.nom
    db.session.delete(client)
    db.session.commit()
    flash(f"Client '{nom}' supprimé.", "warning")
    return redirect(url_for("clients.index"))


@clients_bp.route("/<int:client_id>")
@login_required
def detail(client_id: int):
    client = db.get_or_404(Client, client_id)
    page = request.args.get("page", 1, type=int)

    pagination = (
        Transaction.query.filter_by(client_id=client_id)
        .filter(Transaction.deleted_at == None)  # noqa: E711
        .order_by(Transaction.date_transaction.desc())
        .paginate(page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False)
    )

    return render_template(
        "clients/detail.html",
        client=client,
        transactions=pagination.items,
        pagination=pagination,
    )
