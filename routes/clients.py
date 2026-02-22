"""
Blueprint Clients — CRUD complet + historique + solde
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional
from extensions import db
from models import Client, Transaction
from config import Config

clients_bp = Blueprint("clients", __name__)


# ── Formulaire ───────────────────────────────────
class ClientForm(FlaskForm):
    nom = StringField("Nom complet", validators=[DataRequired(), Length(1, 100)])
    telephone = StringField("Téléphone", validators=[Optional(), Length(max=20)])
    adresse = StringField("Adresse", validators=[Optional(), Length(max=200)])
    submit = SubmitField("Enregistrer")


# ── Liste ─────────────────────────────────────────
@clients_bp.route("/")
@login_required
def index():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "")
    query = Client.query.order_by(Client.created_at.desc())
    if search:
        query = query.filter(Client.nom.ilike(f"%{search}%"))
    pagination = query.paginate(page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False)
    return render_template("clients/index.html",
                           clients=pagination.items,
                           pagination=pagination,
                           search=search)


# ── Création ──────────────────────────────────────
@clients_bp.route("/nouveau", methods=["GET", "POST"])
@login_required
def create():
    form = ClientForm()
    if form.validate_on_submit():
        client = Client(
            nom=form.nom.data.strip(),
            telephone=form.telephone.data.strip() if form.telephone.data else None,
            adresse=form.adresse.data.strip() if form.adresse.data else None,
        )
        db.session.add(client)
        db.session.commit()
        flash(f"Client « {client.nom} » créé avec succès.", "success")
        return redirect(url_for("clients.index"))
    return render_template("clients/form.html", form=form, titre="Nouveau client")


# ── Modification ──────────────────────────────────
@clients_bp.route("/<int:client_id>/modifier", methods=["GET", "POST"])
@login_required
def edit(client_id: int):
    client = db.get_or_404(Client, client_id)
    form = ClientForm(obj=client)
    if form.validate_on_submit():
        client.nom = form.nom.data.strip()
        client.telephone = form.telephone.data.strip() if form.telephone.data else None
        client.adresse = form.adresse.data.strip() if form.adresse.data else None
        db.session.commit()
        flash("Client mis à jour.", "success")
        return redirect(url_for("clients.index"))
    return render_template("clients/form.html", form=form, titre="Modifier le client", client=client)


# ── Suppression ───────────────────────────────────
@clients_bp.route("/<int:client_id>/supprimer", methods=["POST"])
@login_required
def delete(client_id: int):
    client = db.get_or_404(Client, client_id)
    nom = client.nom
    db.session.delete(client)
    db.session.commit()
    flash(f"Client « {nom} » supprimé.", "warning")
    return redirect(url_for("clients.index"))


# ── Fiche client + historique ─────────────────────
@clients_bp.route("/<int:client_id>")
@login_required
def detail(client_id: int):
    client = db.get_or_404(Client, client_id)
    page = request.args.get("page", 1, type=int)
    pagination = (Transaction.query
                  .filter_by(client_id=client_id)
                  .order_by(Transaction.date_transaction.desc())
                  .paginate(page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False))
    return render_template("clients/detail.html",
                           client=client,
                           transactions=pagination.items,
                           pagination=pagination)