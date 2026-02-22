"""
Blueprint Auth - Login / Logout
"""
from urllib.parse import urljoin, urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length
from models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _is_safe_next_url(target: str) -> bool:
    """Valide que la redirection reste sur le même hôte."""
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in {"http", "https"} and test_url.netloc == ref_url.netloc


class LoginForm(FlaskForm):
    username = StringField("Nom d'utilisateur", validators=[DataRequired(), Length(1, 64)])
    password = PasswordField("Mot de passe", validators=[DataRequired()])
    remember_me = BooleanField("Se souvenir de moi")
    submit = SubmitField("Connexion")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get("next", "")
            safe_next = _is_safe_next_url(next_page)
            flash(f"Bienvenue, {user.username} !", "success")
            if next_page and not safe_next:
                flash("Redirection externe bloquée.", "warning")
            return redirect(next_page if safe_next else url_for("dashboard.index"))
        flash("Identifiants incorrects.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for("auth.login"))
