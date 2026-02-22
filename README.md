# DIOLAVERIE â€” Dioplaye Services
Application web de gestion de laverie â€” Flask / Python 3.11+

---

## ðŸš€ Installation locale

### 1. Cloner / tÃ©lÃ©charger le projet
```bash
cd diolaverie
```

### 2. CrÃ©er l'environnement virtuel
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Installer les dÃ©pendances
```bash
pip install -r requirements.txt
```

### 4. Configurer l'environnement
```bash
cp .env.example .env
# Ã‰ditez .env et changez la SECRET_KEY
```

### 5. Lancer l'application
```bash
python app.py
```

Ouvrir dans le navigateur : **http://localhost:5000**

---

## 🔐 Connexion par défaut
- **Admin (tous droits)** : `Abdoulaye Diop` / `admin123`
- **Invité (opérationnel limité)** : `invite` / `invite123`

Droits invité :
- peut ajouter/enregistrer clients, transactions et paiements
- ne peut pas supprimer un client
- ne peut pas modifier la structure des services (créer/modifier/supprimer un service)

âš ï¸ **Changez le mot de passe immÃ©diatement** en production !

---

## ðŸ“ Structure du projet
```
diolaverie/
â”œâ”€â”€ app.py              # Factory Flask
â”œâ”€â”€ config.py           # Configurations dev/prod
â”œâ”€â”€ extensions.py       # Extensions (db, login, csrfâ€¦)
â”œâ”€â”€ models.py           # ModÃ¨les SQLAlchemy
â”œâ”€â”€ wsgi.py             # Point d'entrÃ©e Gunicorn
â”œâ”€â”€ routes/
â”‚   â”œâ”€â”€ auth.py         # Login / Logout
â”‚   â”œâ”€â”€ clients.py      # CRUD clients
â”‚   â”œâ”€â”€ services.py     # CRUD services
â”‚   â”œâ”€â”€ transactions.py # Recettes + paiements
â”‚   â”œâ”€â”€ depenses.py     # DÃ©penses internes
â”‚   â”œâ”€â”€ dashboard.py    # KPIs + graphiques
â”‚   â””â”€â”€ exports.py      # CSV / Excel / PDF
â”œâ”€â”€ templates/          # Templates HTML Jinja2
â”œâ”€â”€ static/             # CSS / JS / images
â””â”€â”€ instance/
    â””â”€â”€ database.db     # Base SQLite (auto-crÃ©Ã©e)
```

---

## ðŸŒ DÃ©ploiement production (Gunicorn)

### Avec Gunicorn directement
```bash
gunicorn wsgi:app --bind 0.0.0.0:8000 --workers 2
```

### Avec Nginx (recommandÃ©)
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

### DÃ©marrage automatique avec systemd
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

## ðŸ“Š FonctionnalitÃ©s
- âœ… Authentification sÃ©curisÃ©e (CSRF + sessions)
- âœ… Gestion clients (CRUD + solde dÃ»)
- âœ… Gestion services (3 par dÃ©faut)
- âœ… Transactions avec crÃ©dit (paiement diffÃ©rÃ©)
- âœ… DÃ©penses internes (par catÃ©gorie)
- âœ… Dashboard avec graphiques Plotly
- âœ… Export CSV, Excel, PDF reÃ§u
- âœ… Interface responsive mobile (Bootstrap 5)
- âœ… Pagination sur toutes les listes

---

## ðŸ”§ Variables d'environnement
| Variable | Description | DÃ©faut |
|---|---|---|
| `FLASK_ENV` | `development` ou `production` | `development` |
| `SECRET_KEY` | ClÃ© secrÃ¨te Flask | auto |
| `DATABASE_URL` | URL base de donnÃ©es | SQLite local |

