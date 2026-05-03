"""
DIOLAVERIE - Point d'entrée de l'application Flask
Pattern : Application Factory
"""
import os
from flask import Flask, current_app, jsonify, render_template, send_from_directory
from sqlalchemy import inspect, text
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
    from routes.recettes_historiques import recettes_historiques_bp
    from routes.exports import exports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(clients_bp, url_prefix="/clients")
    app.register_blueprint(services_bp, url_prefix="/services")
    app.register_blueprint(transactions_bp, url_prefix="/transactions")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(depenses_bp, url_prefix="/depenses")
    app.register_blueprint(recettes_historiques_bp, url_prefix="/recettes-historiques")
    app.register_blueprint(exports_bp, url_prefix="/exports")
    _register_healthcheck(app)
    _register_pwa_routes(app)
    _register_error_handlers(app)

    with app.app_context():
        db.create_all()
        _ensure_schema_compatibility()
        _seed_default_data()
        _backfill_legacy_payments()

    return app


def _register_pwa_routes(app: Flask):
    """Sert le service worker depuis la racine (scope = /)."""

    @app.get("/sw.js")
    def service_worker():
        response = send_from_directory(app.static_folder, "sw.js",
                                       mimetype="application/javascript")
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/manifest.json")
    def web_manifest():
        return send_from_directory(app.static_folder, "manifest.json",
                                   mimetype="application/manifest+json")


def _register_healthcheck(app: Flask):
    """Point de contrôle simple pour validation pré-production."""

    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            database = "ok"
            status_code = 200
        except Exception:
            database = "error"
            status_code = 503

        return jsonify(
            {
                "status": "ok" if database == "ok" else "degraded",
                "database": database,
                "environment": os.environ.get("FLASK_ENV", "default"),
            }
        ), status_code


def _register_error_handlers(app: Flask):
    """Gestionnaires d'erreurs HTTP globaux."""

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500


def _seed_default_data():
    """Insère les données par défaut si la DB est vide."""
    from models import User, Service

    admin_username = current_app.config["ADMIN_DEFAULT_USERNAME"]
    admin_email = current_app.config["ADMIN_DEFAULT_EMAIL"]
    admin_password = current_app.config["ADMIN_DEFAULT_PASSWORD"]
    invite_username = current_app.config["INVITE_DEFAULT_USERNAME"]
    invite_email = current_app.config["INVITE_DEFAULT_EMAIL"]
    invite_password = current_app.config["INVITE_DEFAULT_PASSWORD"]

    admin = User.query.filter_by(role="admin").first()
    if not admin:
        admin = User.query.filter_by(username="admin").first()

    if not admin:
        admin = User(username=admin_username, email=admin_email, role="admin")
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f"Administrateur général créé: {admin_username}")
    else:
        changed_admin = False
        if admin.role != "admin":
            admin.role = "admin"
            changed_admin = True
        if admin.username == "admin" and not User.query.filter_by(username=admin_username).first():
            admin.username = admin_username
            changed_admin = True
        if admin.email == "admin@diolaverie.sn" and not User.query.filter_by(email=admin_email).first():
            admin.email = admin_email
            changed_admin = True
        if changed_admin:
            db.session.commit()
            print(f"Compte admin mis à jour: {admin_username}")

    invite_exists = User.query.filter(
        (User.username == invite_username) | (User.email == invite_email)
    ).first()
    if not invite_exists:
        invite = User(username=invite_username, email=invite_email, role="invite")
        invite.set_password(invite_password)
        db.session.add(invite)
        db.session.commit()
        print(f"Compte invité créé: {invite_username}")

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


def _ensure_schema_compatibility():
    """
    Applique les ajustements minimaux de schéma pour les DB existantes
    quand aucune migration formelle n'a encore été jouée.
    """
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    if "clients" in table_names:
        client_columns = {col["name"] for col in inspector.get_columns("clients")}
        if "remarque" not in client_columns:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE clients ADD COLUMN remarque VARCHAR(300)"))

    if "users" in table_names:
        user_columns = {col["name"] for col in inspector.get_columns("users")}
        if "role" not in user_columns:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'invite'"))
        with db.engine.begin() as conn:
            conn.execute(text("UPDATE users SET role = 'admin' WHERE username = 'admin' AND (role IS NULL OR role = '')"))
            conn.execute(text("UPDATE users SET role = 'invite' WHERE role IS NULL OR role = ''"))

    # Traçabilité : created_by_id
    for table, col_sql in [
        ("transactions",      "ALTER TABLE transactions ADD COLUMN created_by_id INTEGER REFERENCES users(id)"),
        ("paiements",         "ALTER TABLE paiements ADD COLUMN created_by_id INTEGER REFERENCES users(id)"),
        ("depenses_internes", "ALTER TABLE depenses_internes ADD COLUMN created_by_id INTEGER REFERENCES users(id)"),
    ]:
        if table in table_names:
            existing = {col["name"] for col in inspector.get_columns(table)}
            if "created_by_id" not in existing:
                with db.engine.begin() as conn:
                    conn.execute(text(col_sql))

    # Soft delete : deleted_at
    for table, col_sql in [
        ("transactions",      "ALTER TABLE transactions ADD COLUMN deleted_at DATETIME"),
        ("depenses_internes", "ALTER TABLE depenses_internes ADD COLUMN deleted_at DATETIME"),
    ]:
        if table in table_names:
            existing = {col["name"] for col in inspector.get_columns(table)}
            if "deleted_at" not in existing:
                with db.engine.begin() as conn:
                    conn.execute(text(col_sql))


if __name__ == "__main__":
    app = create_app("development")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
