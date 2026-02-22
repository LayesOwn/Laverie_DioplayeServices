"""
Modeles SQLAlchemy - DIOLAVERIE
Tables : User, Client, Service, Transaction, Paiement, DepenseInterne
"""
from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20), nullable=True)
    adresse = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship(
        "Transaction",
        back_populates="client",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    @property
    def total_facture(self) -> float:
        result = db.session.query(
            db.func.coalesce(db.func.sum(Transaction.total), 0)
        ).filter(
            Transaction.client_id == self.id,
            Transaction.type_transaction == "recette",
        ).scalar()
        return float(result or 0)

    @property
    def total_paye(self) -> float:
        result = db.session.query(
            db.func.coalesce(db.func.sum(Paiement.montant), 0)
        ).join(
            Transaction, Transaction.id == Paiement.transaction_id
        ).filter(
            Transaction.client_id == self.id,
            Transaction.type_transaction == "recette",
        ).scalar()
        return float(result or 0)

    @property
    def solde_du(self) -> float:
        return max(0.0, self.total_facture - self.total_paye)

    def __repr__(self):
        return f"<Client {self.nom}>"


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, unique=True)
    prix_unitaire = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship("Transaction", back_populates="service", lazy="dynamic")

    def __repr__(self):
        return f"<Service {self.nom} - {self.prix_unitaire} XOF>"


class Transaction(db.Model):
    __tablename__ = "transactions"

    TYPE_CHOICES = ["recette"]

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    quantite = db.Column(db.Integer, nullable=False, default=1)
    total = db.Column(db.Float, nullable=False)
    montant_paye = db.Column(db.Float, default=0.0)
    type_transaction = db.Column(db.String(20), default="recette")
    date_transaction = db.Column(db.Date, default=date.today)
    notes = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship("Client", back_populates="transactions")
    service = db.relationship("Service", back_populates="transactions")
    paiements = db.relationship(
        "Paiement",
        back_populates="transaction",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    @property
    def total_paye(self) -> float:
        if not self.id:
            return float(self.montant_paye or 0)
        result = db.session.query(
            db.func.coalesce(db.func.sum(Paiement.montant), 0)
        ).filter(
            Paiement.transaction_id == self.id
        ).scalar()
        return float(result or 0)

    @property
    def solde_restant(self) -> float:
        return max(0.0, float(self.total or 0) - self.total_paye)

    @property
    def est_solde(self) -> bool:
        return self.solde_restant <= 0

    def calculer_total(self):
        if self.service:
            self.total = self.service.prix_unitaire * self.quantite

    def enregistrer_paiement(self, montant: float, date_paiement: date = None, notes: str = None) -> float:
        """Enregistre un paiement plafonne au reste du."""
        if not self.id:
            db.session.flush()

        restant = self.solde_restant
        if restant <= 0:
            return 0.0

        paye = min(max(float(montant or 0), 0.0), restant)
        if paye <= 0:
            return 0.0

        paiement = Paiement(
            transaction_id=self.id,
            montant=paye,
            date_paiement=date_paiement or date.today(),
            notes=notes,
        )
        db.session.add(paiement)

        # Denormalized value kept for compatibility with existing screens/filters
        self.montant_paye = float(self.montant_paye or 0) + paye
        return paye

    def __repr__(self):
        return f"<Transaction #{self.id} - {self.total} XOF>"


class Paiement(db.Model):
    __tablename__ = "paiements"

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id"), nullable=False, index=True)
    montant = db.Column(db.Float, nullable=False)
    date_paiement = db.Column(db.Date, default=date.today, nullable=False)
    notes = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transaction = db.relationship("Transaction", back_populates="paiements")

    def __repr__(self):
        return f"<Paiement tx={self.transaction_id} montant={self.montant}>"


class DepenseInterne(db.Model):
    __tablename__ = "depenses_internes"

    TYPE_CHOICES = ["depense", "achat"]

    id = db.Column(db.Integer, primary_key=True)
    libelle = db.Column(db.String(200), nullable=False)
    montant = db.Column(db.Float, nullable=False)
    type_depense = db.Column(db.String(20), nullable=False, default="depense")
    categorie = db.Column(db.String(100), nullable=True)
    date_depense = db.Column(db.Date, default=date.today)
    notes = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<DepenseInterne {self.libelle} - {self.montant} XOF>"
