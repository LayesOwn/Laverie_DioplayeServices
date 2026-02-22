"""Routes package + helpers d'autorisations."""
from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user


def require_admin(view_func):
    """Autorise uniquement les comptes admin."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            flash("Action réservée à l'administrateur général.", "danger")
            return redirect(url_for("dashboard.index"))
        return view_func(*args, **kwargs)

    return wrapped
