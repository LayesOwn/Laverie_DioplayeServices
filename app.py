"""
DIOLAVERIE - Point d'entrée de l'application Flask
Pattern : Application Factory
"""
import os
from flask import Flask
from config import config
from extensions import db, login_manager, csrf, migrate


def create_app(config_name: str = None, test_config: dict | None = None) -> Flask:
    """Factory : crée et configure l'application Flask."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__, instance_relative_config=True)
    config_class = config[config_name]
    app.config.from_object(config_class)
    if test_config:
        app.config.update(test_config)
    if hasattr(config_class, "validate"):
        config_class.validate(app.config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    from models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    from routes.auth import auth_bp
    from routes.clients import clients_bp
    from routes.services import services_bp
    from routes.transactions import transactions_bp
    from routes.dashboard import dashboard_bp
    from routes.depenses import depenses_bp
    from routes.exports import exports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(clients_bp, url_prefix="/clients")
    app.register_blueprint(services_bp, url_prefix="/services")
    app.register_blueprint(transactions_bp, url_prefix="/transactions")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(depenses_bp, url_prefix="/depenses")
    app.register_blueprint(exports_bp, url_prefix="/exports")

    with app.app_context():
        db.create_all()
        _seed_default_data()
        _backfill_legacy_payments()

    return app


def _seed_default_data():
    """Insère les données par défaut si la DB est vide."""
    from models import User, Service

    if not User.query.first():
        admin = User(username="admin", email="admin@diolaverie.sn")
        admin.set_password("admin123")  # A changer en production
        db.session.add(admin)
        db.session.commit()
        print("Utilisateur admin créé. Mot de passe par défaut configuré.")

    if not Service.query.first():
        services_defaut = [
            Service(nom="Lavage simple", prix_unitaire=1500, description="Lavage en machine sans séchage"),
            Service(nom="Lavage + Séchage", prix_unitaire=2500, description="Lavage et séchage complet"),
            Service(
                nom="Lavage + Séchage + Repassage",
                prix_unitaire=4000,
                description="Service complet lavage, séchage et repassage",
            ),
        ]
        db.session.bulk_save_objects(services_defaut)
        db.session.commit()
        print("Services par défaut créés.")


def _backfill_legacy_payments():
    """
    Migre les anciennes transactions qui avaient seulement montant_paye
    vers des lignes dans la table Paiement.
    """
    from models import Transaction, Paiement

    legacy_transactions = Transaction.query.filter(Transaction.montant_paye > 0).all()
    changed = False

    for tx in legacy_transactions:
        existing_total = db.session.query(
            db.func.coalesce(db.func.sum(Paiement.montant), 0)
        ).filter(
            Paiement.transaction_id == tx.id
        ).scalar() or 0

        delta = float(tx.montant_paye or 0) - float(existing_total or 0)

        if delta > 0.0001:
            db.session.add(
                Paiement(
                    transaction_id=tx.id,
                    montant=delta,
                    date_paiement=tx.date_transaction,
                    notes="Reprise historique",
                )
            )
            changed = True
        elif delta < -0.0001:
            tx.montant_paye = float(existing_total)
            changed = True

    if changed:
        db.session.commit()


if __name__ == "__main__":
    app = create_app("development")
    app.run(host="0.0.0.0", port=5000, debug=True)
