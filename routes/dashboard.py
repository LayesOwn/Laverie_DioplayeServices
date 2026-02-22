"""
Blueprint Dashboard - KPIs, graphiques Plotly, analyses
"""
import json
from datetime import date
from calendar import monthrange
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from extensions import db
from models import Transaction, DepenseInterne, Client, Service, Paiement

dashboard_bp = Blueprint("dashboard", __name__)


def _recette_periode(debut: date, fin: date) -> float:
    result = db.session.query(
        func.coalesce(func.sum(Paiement.montant), 0)
    ).filter(
        Paiement.date_paiement.between(debut, fin)
    ).scalar()
    return float(result or 0)


def _depense_periode(debut: date, fin: date) -> float:
    result = db.session.query(
        func.coalesce(func.sum(DepenseInterne.montant), 0)
    ).filter(
        DepenseInterne.date_depense.between(debut, fin)
    ).scalar()
    return float(result or 0)


@dashboard_bp.route("/")
@login_required
def index():
    aujourd_hui = date.today()
    debut_mois = aujourd_hui.replace(day=1)
    fin_mois = aujourd_hui.replace(day=monthrange(aujourd_hui.year, aujourd_hui.month)[1])
    debut_annee = aujourd_hui.replace(month=1, day=1)
    fin_annee = aujourd_hui.replace(month=12, day=31)

    recette_jour = _recette_periode(aujourd_hui, aujourd_hui)
    depense_jour = _depense_periode(aujourd_hui, aujourd_hui)
    benefice_jour = recette_jour - depense_jour

    recette_mois = _recette_periode(debut_mois, fin_mois)
    depense_mois = _depense_periode(debut_mois, fin_mois)
    benefice_mois = recette_mois - depense_mois

    recette_annee = _recette_periode(debut_annee, fin_annee)
    depense_annee = _depense_periode(debut_annee, fin_annee)
    benefice_annee = recette_annee - depense_annee

    nb_non_soldes = Transaction.query.filter(Transaction.montant_paye < Transaction.total).count()
    montant_creances = db.session.query(
        func.coalesce(func.sum(Transaction.total - Transaction.montant_paye), 0)
    ).filter(Transaction.montant_paye < Transaction.total).scalar()

    top_clients = (
        db.session.query(Client.nom, func.sum(Paiement.montant).label("total"))
        .join(Transaction, Transaction.client_id == Client.id)
        .join(Paiement, Paiement.transaction_id == Transaction.id)
        .group_by(Client.id)
        .order_by(func.sum(Paiement.montant).desc())
        .limit(5)
        .all()
    )

    top_services = (
        db.session.query(Service.nom, func.count(Transaction.id).label("nb"))
        .join(Transaction, Transaction.service_id == Service.id)
        .group_by(Service.id)
        .order_by(func.count(Transaction.id).desc())
        .limit(5)
        .all()
    )

    graph_mensuel = _graph_evolution_mensuelle(aujourd_hui)
    graph_services = _graph_services(top_services)

    return render_template(
        "dashboard/index.html",
        recette_jour=recette_jour,
        depense_jour=depense_jour,
        benefice_jour=benefice_jour,
        recette_mois=recette_mois,
        depense_mois=depense_mois,
        benefice_mois=benefice_mois,
        recette_annee=recette_annee,
        depense_annee=depense_annee,
        benefice_annee=benefice_annee,
        nb_non_soldes=nb_non_soldes,
        montant_creances=float(montant_creances or 0),
        top_clients=top_clients,
        top_services=top_services,
        graph_mensuel=graph_mensuel,
        graph_services=graph_services,
        aujourd_hui=aujourd_hui,
    )


def _graph_evolution_mensuelle(ref: date) -> str:
    mois_labels, recettes, depenses = [], [], []

    for i in range(11, -1, -1):
        mois_offset = ref.month - i
        annee = ref.year + (mois_offset - 1) // 12
        mois = ((mois_offset - 1) % 12) + 1
        debut = date(annee, mois, 1)
        fin = date(annee, mois, monthrange(annee, mois)[1])

        mois_labels.append(debut.strftime("%b %Y"))
        recettes.append(_recette_periode(debut, fin))
        depenses.append(_depense_periode(debut, fin))

    fig_data = {
        "data": [
            {
                "type": "bar",
                "name": "Recettes",
                "x": mois_labels,
                "y": recettes,
                "marker": {"color": "#198754"},
            },
            {
                "type": "bar",
                "name": "Dépenses",
                "x": mois_labels,
                "y": depenses,
                "marker": {"color": "#dc3545"},
            },
            {
                "type": "scatter",
                "name": "Bénéfice",
                "x": mois_labels,
                "y": [r - d for r, d in zip(recettes, depenses)],
                "mode": "lines+markers",
                "line": {"color": "#0d6efd", "width": 2},
            },
        ],
        "layout": {
            "barmode": "group",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "font": {"family": "Inter, sans-serif", "size": 12},
            "legend": {"orientation": "h", "y": -0.2},
            "margin": {"l": 40, "r": 20, "t": 20, "b": 60},
            "yaxis": {"tickformat": ",.0f", "ticksuffix": " XOF"},
        },
    }
    return json.dumps(fig_data)


def _graph_services(top_services) -> str:
    if not top_services:
        return json.dumps({"data": [], "layout": {}})

    labels = [s.nom for s in top_services]
    values = [s.nb for s in top_services]

    fig_data = {
        "data": [
            {
                "type": "pie",
                "hole": 0.5,
                "labels": labels,
                "values": values,
                "textinfo": "label+percent",
                "marker": {
                    "colors": ["#0d6efd", "#198754", "#0dcaf0", "#ffc107", "#6f42c1"]
                },
            }
        ],
        "layout": {
            "showlegend": False,
            "plot_bgcolor": "rgba(0,0,0,0)",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "margin": {"l": 20, "r": 20, "t": 20, "b": 20},
        },
    }
    return json.dumps(fig_data)
