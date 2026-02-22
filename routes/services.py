"""
Blueprint Services — CRUD
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
from extensions import db
from models import Service

services_bp = Blueprint("services", __name__)


# ── Formulaire ───────────────────────────────────
class ServiceForm(FlaskForm):
    nom = StringField("Nom du service", validators=[DataRequired(), Length(1, 100)])
    prix_unitaire = FloatField("Prix unitaire (XOF)",
                               validators=[DataRequired(), NumberRange(min=0)])
    description = StringField("Description", validators=[Optional(), Length(max=255)])
    actif = BooleanField("Service actif", default=True)
    submit = SubmitField("Enregistrer")


# ── Liste ─────────────────────────────────────────
@services_bp.route("/")
@login_required
def index():
    services = Service.query.order_by(Service.nom).all()
    return render_template("services/index.html", services=services)


# ── Création ──────────────────────────────────────
@services_bp.route("/nouveau", methods=["GET", "POST"])
@login_required
def create():
    form = ServiceForm()
    if form.validate_on_submit():
        service = Service(
            nom=form.nom.data.strip(),
            prix_unitaire=form.prix_unitaire.data,
            description=form.description.data,
            actif=form.actif.data,
        )
        db.session.add(service)
        db.session.commit()
        flash(f"Service « {service.nom} » créé.", "success")
        return redirect(url_for("services.index"))
    return render_template("services/form.html", form=form, titre="Nouveau service")


# ── Modification ──────────────────────────────────
@services_bp.route("/<int:service_id>/modifier", methods=["GET", "POST"])
@login_required
def edit(service_id: int):
    service = db.get_or_404(Service, service_id)
    form = ServiceForm(obj=service)
    if form.validate_on_submit():
        service.nom = form.nom.data.strip()
        service.prix_unitaire = form.prix_unitaire.data
        service.description = form.description.data
        service.actif = form.actif.data
        db.session.commit()
        flash("Service mis à jour.", "success")
        return redirect(url_for("services.index"))
    return render_template("services/form.html", form=form, titre="Modifier le service")


# ── Suppression ───────────────────────────────────
@services_bp.route("/<int:service_id>/supprimer", methods=["POST"])
@login_required
def delete(service_id: int):
    service = db.get_or_404(Service, service_id)
    # Vérifier si des transactions existent
    if service.transactions.count() > 0:
        flash("Impossible de supprimer un service utilisé dans des transactions.", "danger")
        return redirect(url_for("services.index"))
    nom = service.nom
    db.session.delete(service)
    db.session.commit()
    flash(f"Service « {nom} » supprimé.", "warning")
    return redirect(url_for("services.index"))