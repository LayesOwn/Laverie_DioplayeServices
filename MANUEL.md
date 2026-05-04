# Manuel d'utilisation — Dioplaye Services
**Application de gestion de laverie**
URL : https://layes03.pythonanywhere.com

---

## Table des matières
1. [Connexion](#1-connexion)
2. [Tableau de bord](#2-tableau-de-bord)
3. [Clients](#3-clients)
4. [Transactions](#4-transactions)
5. [Paiements](#5-paiements)
6. [Dépenses internes](#6-dépenses-internes)
7. [Services](#7-services)
8. [Recettes historiques](#8-recettes-historiques)
9. [Exports](#9-exports)
10. [Corbeille (admin)](#10-corbeille-admin)
11. [Comptes utilisateurs](#11-comptes-utilisateurs)
12. [Installer l'app sur téléphone](#12-installer-lapp-sur-téléphone)

---

## 1. Connexion

Ouvrir l'application → page de connexion automatique.

| Compte | Rôle | Accès |
|---|---|---|
| Abdoulaye Diop | Administrateur | Accès complet |
| invite | Invité | Saisie uniquement, pas de suppression |

**Différence Admin / Invité :**
- L'invité peut : créer clients, enregistrer transactions, enregistrer paiements
- L'invité ne peut pas : supprimer clients, supprimer transactions, supprimer dépenses, gérer les services, voir la corbeille, créer d'autres comptes

---

## 2. Tableau de bord

Page d'accueil après connexion. Affiche en temps réel :

**Indicateurs du jour**
- Recettes du jour (paiements reçus aujourd'hui)
- Dépenses du jour
- Bénéfice net du jour

**Indicateurs du mois**
- Recettes du mois en cours
- Dépenses du mois
- Bénéfice net mensuel

**Indicateurs de l'année**
- Totaux annuels recettes / dépenses / bénéfice

**Créances**
- Nombre de transactions non soldées
- Montant total encore dû par les clients

**Graphiques**
- Évolution mensuelle sur 12 mois (barres recettes/dépenses + courbe bénéfice)
- Répartition des services (camembert)
- Recettes par mois et par année (courbes historiques)
- Totaux annuels (barres)

**Top clients** — les 5 clients ayant le plus payé
**Top services** — les 5 services les plus demandés

---

## 3. Clients

Menu → **Clients**

### Voir la liste
- Affiche tous les clients avec leur solde dû
- Barre de recherche : taper le nom du client
- 15 clients par page, navigation par pagination

### Ajouter un client
Cliquer **+ Nouveau client**

Remplir :
- **Nom complet** (obligatoire)
- **Téléphone** (optionnel, recommandé)
- **Adresse** (optionnel)
- **Remarque** (ex: "préfère le séchage fort", optionnel)

Option : créer une première transaction directement sur ce formulaire en choisissant un service et en saisissant l'avance.

### Fiche client
Cliquer sur le nom d'un client → voir :
- Informations du client
- Total facturé, total payé, solde restant dû
- Historique de toutes ses transactions avec statut (soldée / en cours)

### Modifier un client
Dans la liste → icône crayon — modifier nom, téléphone, adresse, remarque.

### Supprimer un client
**Admin uniquement** — supprime définitivement le client ET toutes ses transactions.

---

## 4. Transactions

Menu → **Transactions**

Une transaction = une commande de service pour un client.

### Voir la liste
- Liste de toutes les transactions actives
- Filtre : **Toutes** ou **Non soldées** (clients qui doivent encore de l'argent)

### Créer une transaction
Cliquer **+ Nouvelle transaction**

**Étape 1 — Client**
Trois façons de choisir le client :
- Sélectionner dans la liste déroulante
- Rechercher par nom ou téléphone dans le champ de recherche
- Créer un nouveau client directement (remplir Nom, Téléphone, Adresse)

> Si un client avec le même nom ou téléphone existe déjà, l'application le détecte et le réutilise automatiquement.

**Étape 2 — Service et quantité**
- Choisir le service (prix s'affiche automatiquement)
- Saisir la quantité (ex: 2 pour 2 machines)
- Le total est calculé automatiquement

**Étape 3 — Avance (optionnel)**
- Saisir le montant payé immédiatement (avance à la commande)
- Laisser 0 si le client paye au retrait

**Étape 4 — Date et notes**
- Date de la transaction (aujourd'hui par défaut)
- Notes libres (ex: "chemises blanches, délicat")

### Supprimer une transaction
**Admin uniquement** — la transaction va dans la corbeille (récupérable).

---

## 5. Paiements

Depuis la **fiche client** ou la liste des transactions → bouton **Enregistrer un paiement**

Utilisé quand un client revient récupérer son linge et paye le solde restant.

**Formulaire :**
- **Montant reçu** (en XOF, entier — pas de décimales)
- **Date du paiement** (aujourd'hui par défaut)
- **Notes** (optionnel, ex: "payé en deux fois")

> L'application plafonne automatiquement le paiement au solde restant dû. Il est impossible de saisir un paiement supérieur à ce qui est dû.

La page affiche aussi l'**historique des paiements** de cette transaction.

---

## 6. Dépenses internes

Menu → **Dépenses**

Enregistre les charges de la laverie (pas liées à un client).

### Ajouter une dépense
Cliquer **+ Nouvelle dépense**

- **Libellé** : description (ex: "Achat lessive Ariel 5kg")
- **Montant** (XOF)
- **Type** : Dépense ou Achat
- **Catégorie** : Lessive/Produits, Électricité/Eau, Matériel/Équipement, Loyer, Transport, Salaires, Maintenance, Autre
- **Date**
- **Notes** (optionnel)

### Modifier une dépense
Icône crayon dans la liste.

### Supprimer une dépense
**Admin uniquement** — va dans la corbeille (récupérable).

---

## 7. Services

Menu → **Services** (admin uniquement pour créer/modifier/supprimer)

Les services sont les prestations proposées.

**Services par défaut :**
| Service | Prix |
|---|---|
| Lavage simple | 1 500 XOF |
| Lavage + Séchage | 2 500 XOF |
| Lavage + Séchage + Repassage | 4 000 XOF |

### Ajouter un service
- Nom, prix unitaire, description
- Un service peut être désactivé (n'apparaît plus dans les nouveaux formulaires)

### Modifier un service
Le prix mis à jour ne change pas les transactions déjà enregistrées.

---

## 8. Recettes historiques

Menu → **Recettes historiques** (admin uniquement)

Permet de saisir les recettes des jours/semaines/mois passés avant l'utilisation de l'application, pour avoir un historique complet dans les graphiques.

### Ajouter une recette historique
- Date (une seule entrée par jour)
- Montant total de la journée
- Notes

### Vue unifiée
Menu → **Recettes unifiées** — combine les recettes historiques saisies manuellement ET les paiements enregistrés dans l'app. Donne une vision complète de l'activité.

---

## 9. Exports

Menu sidebar → section **Exports**

### Export CSV (transactions)
Télécharge un fichier `.csv` de toutes les transactions (ouvrable dans Excel, LibreOffice, Google Sheets).

Colonnes : ID, Date, Client, Service, Quantité, Total, Payé, Reste dû, Notes.

### Export Excel (transactions)
Télécharge un fichier `.xlsx` formaté avec entêtes colorés et largeurs automatiques.

### Reçu PDF
Depuis la fiche d'une transaction → bouton **Reçu PDF**
Génère un reçu au format A5 à imprimer ou envoyer au client.

Contient : nom du client, service, quantité, total, montant payé, reste dû, date.

### Export CSV (dépenses)
Depuis le menu Exports → **Export CSV dépenses**
Exporte uniquement les dépenses actives (pas celles dans la corbeille).

---

## 10. Corbeille (admin)

Les suppressions dans l'app ne sont pas définitives — les éléments vont dans une corbeille.

### Corbeille transactions
Menu → **Transactions** → lien **Corbeille**
- Voir les transactions supprimées
- Bouton **Restaurer** pour les remettre dans la liste active

### Corbeille dépenses
Menu → **Dépenses** → lien **Corbeille**
- Même fonctionnement

> La suppression depuis la corbeille n'existe pas (protection des données). Pour supprimer définitivement, contacter le support technique.

---

## 11. Comptes utilisateurs

### Créer un compte invité
**Admin uniquement** → Menu → **Créer un invité**

- Saisir nom d'utilisateur, email, mot de passe
- Le compte est créé avec le rôle "invité"
- Utile pour les employés qui saisissent les transactions

### Déconnexion
Menu → bas de la sidebar → **Déconnexion**

---

## 12. Installer l'app sur téléphone

L'application peut être installée comme une vraie application sur Android.

**Étapes sur Android (Chrome) :**
1. Ouvrir Chrome
2. Aller sur `https://layes03.pythonanywhere.com`
3. Se connecter
4. Appuyer sur les **⋮ 3 points** en haut à droite
5. **"Ajouter à l'écran d'accueil"**
6. Confirmer → l'icône apparaît sur l'écran d'accueil

L'app s'ouvre ensuite sans barre de navigation, comme une application native.

---

## Résumé des raccourcis utiles

| Action | Chemin |
|---|---|
| Nouvelle transaction | Transactions → + Nouvelle transaction |
| Nouveau client | Clients → + Nouveau client |
| Encaisser un paiement | Fiche client → bouton Payer |
| Nouvelle dépense | Dépenses → + Nouvelle dépense |
| Télécharger Excel | Sidebar → Export Excel |
| Imprimer un reçu | Transaction → Reçu PDF |
| Voir les impayés | Transactions → filtre "Non soldées" |
| Corbeille | Transactions ou Dépenses → lien Corbeille |

---

*Dioplaye Services — Gestion Laverie | Support : dioplayes@gmail.com*
