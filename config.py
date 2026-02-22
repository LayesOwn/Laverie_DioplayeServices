"""Configuration de l'application DIOLAVERIE."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SECRET_KEY = "diolaverie-secret-key-change-in-prod-2024"


class Config:
    """Configuration de base."""

    SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)
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
    ADMIN_DEFAULT_PASSWORD = os.environ.get("ADMIN_DEFAULT_PASSWORD", "admin123")
    INVITE_DEFAULT_USERNAME = os.environ.get("INVITE_DEFAULT_USERNAME", "invite")
    INVITE_DEFAULT_EMAIL = os.environ.get("INVITE_DEFAULT_EMAIL", "invite@dioplaye.sn")
    INVITE_DEFAULT_PASSWORD = os.environ.get("INVITE_DEFAULT_PASSWORD", "invite123")


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
        secret_key = app_config.get("SECRET_KEY", "")
        if not secret_key or secret_key == DEFAULT_SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY must be set to a strong unique value in production."
            )


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
