"""Configuration de l'application DIOLAVERIE."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

_WEAK_SECRET_KEY = "diolaverie-secret-key-change-in-prod-2024"
_WEAK_ADMIN_PASSWORD = "admin123"
_WEAK_INVITE_PASSWORD = "invite123"


class Config:
    """Configuration de base."""

    SECRET_KEY = os.environ.get("SECRET_KEY", _WEAK_SECRET_KEY)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    # Session/cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # Pagination
    ITEMS_PER_PAGE = 15

    # Nom de la laverie
    LAVERIE_NOM = "Dioplaye Services"
    LAVERIE_DEVISE = "XOF"
    LAVERIE_TELEPHONE = "70.7301346"

    # Comptes par défaut
    ADMIN_DEFAULT_USERNAME = os.environ.get("ADMIN_DEFAULT_USERNAME", "Abdoulaye Diop")
    ADMIN_DEFAULT_EMAIL = os.environ.get("ADMIN_DEFAULT_EMAIL", "abdoulaye.diop@dioplaye.sn")
    ADMIN_DEFAULT_PASSWORD = os.environ.get("ADMIN_DEFAULT_PASSWORD", _WEAK_ADMIN_PASSWORD)
    INVITE_DEFAULT_USERNAME = os.environ.get("INVITE_DEFAULT_USERNAME", "invite")
    INVITE_DEFAULT_EMAIL = os.environ.get("INVITE_DEFAULT_EMAIL", "invite@dioplaye.sn")
    INVITE_DEFAULT_PASSWORD = os.environ.get("INVITE_DEFAULT_PASSWORD", _WEAK_INVITE_PASSWORD)


class DevelopmentConfig(Config):
    """Configuration developpement local."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'database.db'}"


class ProductionConfig(Config):
    """Configuration production."""

    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'database.db'}",
    )

    @staticmethod
    def validate(app_config: dict) -> None:
        errors = []

        secret_key = app_config.get("SECRET_KEY", "")
        if not secret_key or secret_key == _WEAK_SECRET_KEY:
            errors.append(
                "SECRET_KEY doit etre une valeur longue et aleatoire.\n"
                "  Generez-en une : python -c \"import secrets; print(secrets.token_hex(32))\""
            )

        admin_pwd = app_config.get("ADMIN_DEFAULT_PASSWORD", "")
        if not admin_pwd or admin_pwd == _WEAK_ADMIN_PASSWORD:
            errors.append(
                "ADMIN_DEFAULT_PASSWORD ne peut pas etre 'admin123' en production.\n"
                "  Definissez une valeur forte dans les variables d'environnement."
            )

        invite_pwd = app_config.get("INVITE_DEFAULT_PASSWORD", "")
        if not invite_pwd or invite_pwd == _WEAK_INVITE_PASSWORD:
            errors.append(
                "INVITE_DEFAULT_PASSWORD ne peut pas etre 'invite123' en production.\n"
                "  Definissez une valeur forte dans les variables d'environnement."
            )

        if errors:
            raise RuntimeError(
                "Configuration de production invalide :\n\n" + "\n\n".join(f"- {e}" for e in errors)
            )


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
