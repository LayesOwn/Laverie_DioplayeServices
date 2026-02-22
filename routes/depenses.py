"""
Blueprint Dépenses Internes — charges de la laverie (sans client)
"""
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange, Length
from extensions import db
from models import DepenseInterne
from config import Config

depenses_bp = Blueprint("depenses", __name__)

CATEGORIES = [
    "Lessive / Produits",
    "Électricité / Eau",
    "Matériel / Équipement",
    "Loyer",
    "Transport",
    "Salaires",
    "Maintenance",
    "Autre",
]


# ── Formulaire ───────────────────────────────────
class DepenseForm(FlaskForm):
    libelle = StringField("Libellé", validators=[DataRequired(), Length(1, 200)])
    montant = FloatField("Montant (XOF)", validators=[DataRequired(), NumberRange(min=0)])
    type_depense = SelectField("Type", choices=[("depense", "Dépense"), ("achat", "Achat")])
    categorie = SelectField("Catégorie", choices=[(c, c) for c in CATEGORIES],
                            validators=[Optional()])
    date_depense = DateField("Date", default=date.today, validators=[DataRequired()])
    notes = StringField("Notes", validators=[Optional()])
    submit = SubmitField("Enregistrer")


# ── Liste ─────────────────────────────────────────
@depenses_bp.route("/")
@login_required
def index():
    page = request.args.get("page", 1, type=int)
    pagination = (DepenseInterne.query
                  .order_by(DepenseInterne.date_depense.desc())
                  .paginate(page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False))
    return render_template("transactions/depenses.html",
                           depenses=pagination.items,
                           pagination=pagination)


# ── Création ──────────────────────────────────────
@depenses_bp.route("/nouvelle", methods=["GET", "POST"])
@login_required
def create():
    form = DepenseForm()
    if form.validate_on_submit():
        dep = DepenseInterne(
            libelle=form.libelle.data.strip(),
            montant=form.montant.data,
            type_depense=form.type_depense.data,
            categorie=form.categorie.data,
            date_depense=form.date_depense.data,
            notes=form.notes.data,
        )
        db.session.add(dep)
        db.session.commit()
        flash(f"Dépense « {dep.libelle} » enregistrée.", "success")
        return redirect(url_for("depenses.index"))
    return render_template("transactions/depense_form.html", form=form, titre="Nouvelle dépense")


# ── Modification ──────────────────────────────────
@depenses_bp.route("/<int:dep_id>/modifier", methods=["GET", "POST"])
@login_required
def edit(dep_id: int):
    dep = db.get_or_404(DepenseInterne, dep_id)
    form = DepenseForm(obj=dep)
    if form.validate_on_submit():
        dep.libelle = form.libelle.data.strip()
        dep.montant = form.montant.data
        dep.type_depense = form.type_depense.data
        dep.categorie = form.categorie.data
        dep.date_depense = form.date_depense.data
        dep.notes = form.notes.data
        db.session.commit()
        flash("Dépense mise à jour.", "success")
        return redirect(url_for("depenses.index"))
    return render_template("transactions/depense_form.html", form=form, titre="Modifier la dépense")


# ── Suppression ───────────────────────────────────
@depenses_bp.route("/<int:dep_id>/supprimer", methods=["POST"])
@login_required
def delete(dep_id: int):
    dep = db.get_or_404(DepenseInterne, dep_id)
    db.session.delete(dep)
    db.session.commit()
    flash("Dépense supprimée.", "warning")
    return redirect(url_for("depenses.index"))