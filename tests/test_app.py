import unittest
from datetime import date
from pathlib import Path

from app import create_app
from extensions import db
from models import User, Client as ModelClient, Service, Transaction, Paiement


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = Path(__file__).resolve().parent / "test_app.db"
        try:
            if cls.test_db_path.exists():
                cls.test_db_path.unlink()
        except PermissionError:
            pass

        cls.app = create_app(
            "development",
            {
                "TESTING": True,
                "WTF_CSRF_ENABLED": False,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{cls.test_db_path.as_posix()}",
            },
        )

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        try:
            if cls.test_db_path.exists():
                cls.test_db_path.unlink()
        except PermissionError:
            pass

    def setUp(self):
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()

            admin = User(username="admin", email="admin@test.local")
            admin.set_password("admin123")
            db.session.add(admin)

            seed_client = ModelClient(nom="Client Seed", telephone="770000000")
            seed_service = Service(nom="Service Seed", prix_unitaire=1500, description="Seed", actif=True)
            db.session.add(seed_client)
            db.session.add(seed_service)
            db.session.commit()

            self.seed_client_id = seed_client.id
            self.seed_service_id = seed_service.id

    def login(self, username="admin", password="admin123", next_path=None):
        url = "/auth/login"
        if next_path:
            url = f"{url}?next={next_path}"
        return self.client.post(
            url,
            data={"username": username, "password": password, "remember_me": "y"},
            follow_redirects=False,
        )

    def test_login_guard_and_safe_next(self):
        resp = self.client.get("/clients/", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.headers.get("Location", ""))

        resp_external = self.login(next_path="https://evil.example/")
        self.assertEqual(resp_external.status_code, 302)
        self.assertEqual(resp_external.headers.get("Location"), "/")

        self.client.get("/auth/logout", follow_redirects=False)
        resp_local = self.login(next_path="/clients/")
        self.assertEqual(resp_local.status_code, 302)
        self.assertEqual(resp_local.headers.get("Location"), "/clients/")

    def test_clients_crud(self):
        self.login()

        create_route_resp = self.client.get("/clients/nouveau", follow_redirects=False)
        self.assertEqual(create_route_resp.status_code, 302)
        self.assertEqual(create_route_resp.headers.get("Location"), "/transactions/nouvelle")

        create_tx_resp = self.client.post(
            "/transactions/nouvelle",
            data={
                "client_id": "0",
                "new_client_nom": "Mamadou Diallo",
                "new_client_telephone": "771234567",
                "new_client_adresse": "Dakar",
                "new_client_remarque": "Client prioritaire",
                "service_id": str(self.seed_service_id),
                "quantite": "1",
                "avance": "0",
                "date_transaction": date.today().isoformat(),
                "notes": "Client créé avec transaction",
            },
            follow_redirects=False,
        )
        self.assertEqual(create_tx_resp.status_code, 302)

        with self.app.app_context():
            created = ModelClient.query.filter_by(nom="Mamadou Diallo").first()
            self.assertIsNotNone(created)
            self.assertEqual(created.remarque, "Client prioritaire")
            created_id = created.id

        edit_resp = self.client.post(
            f"/clients/{created_id}/modifier",
            data={
                "nom": "Mamadou D.",
                "telephone": "779999999",
                "adresse": "Thies",
                "remarque": "Suivi hebdomadaire",
            },
            follow_redirects=False,
        )
        self.assertEqual(edit_resp.status_code, 302)

        with self.app.app_context():
            edited = db.session.get(ModelClient, created_id)
            self.assertEqual(edited.nom, "Mamadou D.")
            self.assertEqual(edited.telephone, "779999999")
            self.assertEqual(edited.remarque, "Suivi hebdomadaire")

        delete_resp = self.client.post(f"/clients/{created_id}/supprimer", follow_redirects=False)
        self.assertEqual(delete_resp.status_code, 302)

        with self.app.app_context():
            self.assertIsNone(db.session.get(ModelClient, created_id))

    def test_services_crud(self):
        self.login()

        create_resp = self.client.post(
            "/services/nouveau",
            data={
                "nom": "Lavage premium",
                "prix_unitaire": "2500",
                "description": "Avec parfum",
                "actif": "y",
            },
            follow_redirects=False,
        )
        self.assertEqual(create_resp.status_code, 302)

        with self.app.app_context():
            created = Service.query.filter_by(nom="Lavage premium").first()
            self.assertIsNotNone(created)
            service_id = created.id

        edit_resp = self.client.post(
            f"/services/{service_id}/modifier",
            data={
                "nom": "Lavage premium plus",
                "prix_unitaire": "3000",
                "description": "Avec parfum et repassage",
                "actif": "y",
            },
            follow_redirects=False,
        )
        self.assertEqual(edit_resp.status_code, 302)

        with self.app.app_context():
            edited = db.session.get(Service, service_id)
            self.assertEqual(edited.nom, "Lavage premium plus")
            self.assertAlmostEqual(float(edited.prix_unitaire), 3000.0)

        delete_resp = self.client.post(f"/services/{service_id}/supprimer", follow_redirects=False)
        self.assertEqual(delete_resp.status_code, 302)

        with self.app.app_context():
            self.assertIsNone(db.session.get(Service, service_id))

    def test_transaction_payment_history_and_dashboard(self):
        self.login()

        create_tx_resp = self.client.post(
            "/transactions/nouvelle",
            data={
                "client_id": str(self.seed_client_id),
                "service_id": str(self.seed_service_id),
                "quantite": "2,5",
                "avance": "1000",
                "date_transaction": date.today().isoformat(),
                "notes": "Initial",
            },
            follow_redirects=False,
        )
        self.assertEqual(create_tx_resp.status_code, 302)

        with self.app.app_context():
            tx = Transaction.query.order_by(Transaction.id.desc()).first()
            self.assertIsNotNone(tx)
            self.assertAlmostEqual(tx.quantite, 2.5)
            self.assertAlmostEqual(tx.total, 3750.0)
            self.assertAlmostEqual(tx.total_paye, 1000.0)
            self.assertEqual(Paiement.query.filter_by(transaction_id=tx.id).count(), 1)
            tx_id = tx.id

        pay_resp = self.client.post(
            f"/transactions/{tx_id}/paiement",
            data={
                "montant": "500",
                "date_paiement": date.today().isoformat(),
                "notes": "Complement",
            },
            follow_redirects=False,
        )
        self.assertEqual(pay_resp.status_code, 302)

        with self.app.app_context():
            tx_after = db.session.get(Transaction, tx_id)
            self.assertAlmostEqual(tx_after.total_paye, 1500.0)
            self.assertAlmostEqual(tx_after.solde_restant, 2250.0)
            self.assertEqual(Paiement.query.filter_by(transaction_id=tx_id).count(), 2)

        dashboard_resp = self.client.get("/")
        self.assertEqual(dashboard_resp.status_code, 200)
        self.assertIn(b"Tableau de bord", dashboard_resp.data)

    def test_amount_fields_reject_decimals(self):
        self.login()

        invalid_create_resp = self.client.post(
            "/transactions/nouvelle",
            data={
                "client_id": str(self.seed_client_id),
                "service_id": str(self.seed_service_id),
                "quantite": "1",
                "avance": "1000,5",
                "date_transaction": date.today().isoformat(),
                "notes": "Invalid decimal avance",
            },
            follow_redirects=False,
        )
        self.assertEqual(invalid_create_resp.status_code, 200)

        with self.app.app_context():
            self.assertEqual(Transaction.query.count(), 0)

        valid_create_resp = self.client.post(
            "/transactions/nouvelle",
            data={
                "client_id": str(self.seed_client_id),
                "service_id": str(self.seed_service_id),
                "quantite": "1",
                "avance": "0",
                "date_transaction": date.today().isoformat(),
                "notes": "Valid transaction",
            },
            follow_redirects=False,
        )
        self.assertEqual(valid_create_resp.status_code, 302)

        with self.app.app_context():
            tx = Transaction.query.order_by(Transaction.id.desc()).first()
            tx_id = tx.id

        invalid_payment_resp = self.client.post(
            f"/transactions/{tx_id}/paiement",
            data={
                "montant": "200,5",
                "date_paiement": date.today().isoformat(),
                "notes": "Invalid decimal payment",
            },
            follow_redirects=False,
        )
        self.assertEqual(invalid_payment_resp.status_code, 200)

        with self.app.app_context():
            tx_after = db.session.get(Transaction, tx_id)
            self.assertAlmostEqual(tx_after.total_paye, 0.0)
            self.assertEqual(Paiement.query.filter_by(transaction_id=tx_id).count(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
