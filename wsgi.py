"""
Point d'entrée WSGI pour Gunicorn
Usage : gunicorn wsgi:app
"""
from app import create_app

app = create_app("production")