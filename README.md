# Voyara

Plateforme de réservation d'activités touristiques — **microservices (backend) + micro-frontends (frontend)**.

```text
frontend/apps/      client Next.js SSR/SEO (5173) · admin Vite (5174/admin)
frontend/packages/  @voyara/{ui, api, auth, i18n}       ← packages partagés
gateway/            API Gateway (port 8000)
services/           auth · catalog · booking · payment · review · notification · admin
libs/               voyara_common (code partagé Python)
infra/              init PostgreSQL · nginx    scripts/    dev.ps1, stop-dev.ps1…
```

📖 **Architecture détaillée : [docs/architecture.md](docs/architecture.md)**

## Démarrage rapide (dev)

```powershell
# 1. Environnement Python (une fois)
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\pip install -e libs/common

# 2. Base de données (Docker) puis tous les services backend
docker compose up -d postgres
.\scripts\dev.ps1 -Seed        # -Seed crée l'admin initial (1re fois)

# 3. Micro-frontends (les deux apps)
cd frontend
npm install
npm run dev
```

- Site client : http://localhost:5173
- Espace admin : http://localhost:5174/admin (login admin dédié)
- API (gateway) : http://localhost:8000 — santé : http://localhost:8000/health
- Swagger par service : http://localhost:8001/docs … http://localhost:8007/docs
- Arrêt des services backend : `.\scripts\stop-dev.ps1`

## Tout en Docker

```powershell
copy .env.example .env    # remplir les secrets
docker compose up --build
```

## Tests

```powershell
cd services/auth
..\..\.venv\Scripts\python -m pytest
```
# Terminal 1 (racine du projet)
docker compose up -d postgres     # 1. la base
.\scripts\dev.ps1                 # 2. le backend (8 fenêtres minimisées)

# Terminal 2
cd frontend
npm run dev                       # 3. les 2 frontends
