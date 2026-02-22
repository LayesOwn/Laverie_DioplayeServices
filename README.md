# DIOLAVERIE — Dioplaye Services
Application web de gestion de laverie — Flask / Python 3.11+

---

## 🚀 Installation locale

### 1. Cloner / télécharger le projet
```bash
cd diolaverie
```

### 2. Créer l'environnement virtuel
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer l'environnement
```bash
cp .env.example .env
# Éditez .env et changez la SECRET_KEY
```

### 5. Lancer l'application
```bash
python app.py
```

Ouvrir dans le navigateur : **http://localhost:5000**

---

## 🔐 Connexion par défaut
- **Utilisateur** : `admin`
- **Mot de passe** : `admin123`

⚠️ **Changez le mot de passe immédiatement** en production !

---

## 📁 Structure du projet
```
diolaverie/
├── app.py              # Factory Flask
├── config.py           # Configurations dev/prod
├── extensions.py       # Extensions (db, login, csrf…)
├── models.py           # Modèles SQLAlchemy
├── wsgi.py             # Point d'entrée Gunicorn
├── routes/
│   ├── auth.py         # Login / Logout
│   ├── clients.py      # CRUD clients
│   ├── services.py     # CRUD services
│   ├── transactions.py # Recettes + paiements
│   ├── depenses.py     # Dépenses internes
│   ├── dashboard.py    # KPIs + graphiques
│   └── exports.py      # CSV / Excel / PDF
├── templates/          # Templates HTML Jinja2
├── static/             # CSS / JS / images
└── instance/
    └── database.db     # Base SQLite (auto-créée)
```

---

## 🌍 Déploiement production (Gunicorn)

### Avec Gunicorn directement
```bash
gunicorn wsgi:app --bind 0.0.0.0:8000 --workers 2
```

### Avec Nginx (recommandé)
Fichier `/etc/nginx/sites-available/diolaverie` :
```nginx
server {
    listen 80;
    server_name votre-domaine.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Démarrage automatique avec systemd
Fichier `/etc/systemd/system/diolaverie.service` :
```ini
[Unit]
Description=Diolaverie Flask App
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/diolaverie
ExecStart=/var/www/diolaverie/venv/bin/gunicorn wsgi:app --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable diolaverie
sudo systemctl start diolaverie
```

---

## 📊 Fonctionnalités
- ✅ Authentification sécurisée (CSRF + sessions)
- ✅ Gestion clients (CRUD + solde dû)
- ✅ Gestion services (3 par défaut)
- ✅ Transactions avec crédit (paiement différé)
- ✅ Dépenses internes (par catégorie)
- ✅ Dashboard avec graphiques Plotly
- ✅ Export CSV, Excel, PDF reçu
- ✅ Interface responsive mobile (Bootstrap 5)
- ✅ Pagination sur toutes les listes

---

## 🔧 Variables d'environnement
| Variable | Description | Défaut |
|---|---|---|
| `FLASK_ENV` | `development` ou `production` | `development` |
| `SECRET_KEY` | Clé secrète Flask | auto |
| `DATABASE_URL` | URL base de données | SQLite local |
