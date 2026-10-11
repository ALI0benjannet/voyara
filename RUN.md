# RUN — Lancer Voyara sur ton PC (Windows)

Guide pas à pas pour faire tourner le projet en local après l'avoir cloné.
Toutes les commandes sont à taper dans **PowerShell**, à la racine du projet sauf indication contraire.

---

## 0. Prérequis à installer (une seule fois)

| Outil | Version | Lien |
|---|---|---|
| Git | récent | https://git-scm.com/download/win |
| Python | **3.12** (cocher « Add to PATH ») | https://www.python.org/downloads/ |
| Node.js | **22 LTS** ou plus | https://nodejs.org/ |
| Docker Desktop | récent (doit être **lancé**) | https://www.docker.com/products/docker-desktop/ |

Vérifier :

```powershell
git --version
python --version
node --version
npm --version
docker --version
```

Si PowerShell refuse de lancer les scripts `.ps1`, exécuter une fois :

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 1. Cloner le projet

```powershell
git clone https://github.com/ALI0benjannet/voyara.git
cd voyara
```

> Le dépôt est privé ? Ali doit d'abord t'ajouter comme collaborateur sur GitHub
> (Settings → Collaborators → Add people), puis tu acceptes l'invitation reçue par e-mail.

---

## 2. Mettre les fichiers `.env` (secrets)

Les fichiers `.env` ne sont **pas** dans Git. Ali te les envoie à part
(ne jamais les commiter ni les partager publiquement).

Il en faut **9**, chacun à sa place exacte :

```text
Voyara/
├── .env
├── gateway/.env
└── services/
    ├── admin/.env
    ├── auth/.env
    ├── booking/.env
    ├── catalog/.env
    ├── notification/.env
    ├── payment/.env
    └── review/.env
```

Vérifier qu'ils sont tous là :

```powershell
Get-ChildItem -Recurse -Force -Filter .env -File | Where-Object { $_.FullName -notmatch 'node_modules|\.venv' } | Select-Object FullName
```

> Important : dans `services/*/.env`, `POSTGRES_PORT` doit valoir **5434**
> (c'est le port du conteneur Postgres de `docker-compose.yml`).

Les fichiers `.env` du frontend (`frontend/apps/*/.env.development`) sont déjà dans Git, rien à faire.

---

## 3. Installer le backend Python (une seule fois)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\pip install -e libs/common
```

---

## 4. Démarrer la base de données (Docker)

Docker Desktop doit être ouvert.

```powershell
docker compose up -d postgres
docker compose ps          # attendre que postgres soit "healthy"
```

---

## 5. Première fois seulement : créer les bases, les tables et les données de démo

```powershell
# 5.1 Créer les 5 bases (voyara, voyara_catalog, voyara_booking, voyara_payment, voyara_review)
.venv\Scripts\python scripts\create_databases.py

# 5.2 Tables du service auth (migrations Alembic)
cd services\auth
..\..\.venv\Scripts\alembic upgrade head
cd ..\..

# 5.3 Démarrer tout le backend + créer le compte admin initial
.\scripts\dev.ps1 -Seed
```

Attendre ~10 secondes que les services démarrent (ils créent leurs tables), puis remplir le catalogue :

```powershell
# 5.4 Catalogue de démo (catégories, activités, créneaux, traductions, photos)
cd services\catalog
..\..\.venv\Scripts\python scripts\seed_catalog.py
..\..\.venv\Scripts\python scripts\add_translation_columns.py
..\..\.venv\Scripts\python scripts\add_places_totales.py
..\..\.venv\Scripts\python scripts\seed_translations.py
..\..\.venv\Scripts\python scripts\seed_photos.py
cd ..\..

# 5.5 Codes promo de démo
cd services\booking
..\..\.venv\Scripts\python scripts\seed_promos.py
cd ..\..
```

Le backend tourne déjà (étape 5.3) → passer directement à l'étape **7**.

---

## 6. Les fois suivantes : démarrer le backend

```powershell
docker compose up -d postgres
.\scripts\dev.ps1
```

Cela ouvre 8 fenêtres minimisées (auth, catalog, booking, payment, review, notification, admin, gateway).

---

## 7. Démarrer le frontend (dans un **2e terminal**)

```powershell
cd frontend
npm install        # la première fois (ou après un git pull qui change les dépendances)
npm run dev
```

---

## 8. Ouvrir l'application

| Quoi | URL |
|---|---|
| Site client | http://localhost:5173 |
| Espace admin | http://localhost:5174/admin |
| API Gateway | http://localhost:8000 |
| Santé de tous les services | http://localhost:8000/health |
| Swagger par service | http://localhost:8001/docs … http://localhost:8007/docs |

Connexion admin : les identifiants `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` du fichier `.env` racine.

---

## 9. Arrêter

```powershell
# Frontend : Ctrl+C dans son terminal

# Backend
.\scripts\stop-dev.ps1

# Base de données (les données sont conservées)
docker compose stop postgres
```

---

## Récap rapide (au quotidien)

```powershell
# Terminal 1 — racine du projet
git pull
docker compose up -d postgres
.\scripts\dev.ps1

# Terminal 2
cd frontend
npm run dev
```

---

## Problèmes fréquents

| Problème | Solution |
|---|---|
| `PostgreSQL injoignable` | Docker Desktop n'est pas lancé, ou Postgres pas prêt → `docker compose up -d postgres` puis attendre 10 s |
| `Venv introuvable` | Refaire l'étape 3 |
| Port déjà utilisé (8000–8007, 5173, 5174, 5434) | `.\scripts\stop-dev.ps1`, ou fermer l'appli qui utilise le port |
| `relation "users" does not exist` | Refaire l'étape 5.2 (`alembic upgrade head`) |
| `/health` montre un service en erreur | Ouvrir sa fenêtre minimisée dans la barre des tâches pour lire l'erreur (souvent un `.env` manquant) |
| Catalogue vide sur le site | Refaire l'étape 5.4 |
| Les e-mails ne partent pas | Vérifier `MAIL_*` dans `services/notification/.env` |
| `npm install` échoue | `cd frontend`, supprimer `node_modules` puis relancer `npm install` |

## Lancer les tests

```powershell
cd services\auth
..\..\.venv\Scripts\python -m pytest
```
