# CLAUDE.md — règles de travail sur Voyara

Plateforme de réservation d'activités touristiques (Tunisie) : **microservices FastAPI**
derrière un gateway + **micro-frontends** (client Next.js SSR, admin Vite).
Référence complète : [docs/architecture.md](docs/architecture.md) · avancement : [docs/plan.md](docs/plan.md) ·
modèle de données : [docs/mcd.md](docs/mcd.md) · moteur IA : [docs/ia/README.md](docs/ia/README.md).

> Le site client a ses propres consignes (Next.js 16, API différentes de l'habituel) :
> [frontend/apps/client/CLAUDE.md](frontend/apps/client/CLAUDE.md) — à lire avant de toucher `apps/client`.

## 1. Architecture en bref

| Composant | Port | Base | Rôle |
|---|---|---|---|
| `gateway/` | 8000 | — | Point d'entrée unique, routage par préfixe, CORS, **bloque tout `/internal`**, `/health` agrégé |
| `services/auth` | 8001 | `voyara` (Alembic) | Comptes, JWT HS256, refresh rotatif, e-mail, avatars |
| `services/catalog` | 8002 | `voyara_catalog` | Activités, catégories, créneaux (réserve/libère atomiquement), offres de voyage |
| `services/booking` | 8003 | `voyara_booking` | Réservations (saga avec catalog), codes promo, QR, expiration des `pending` |
| `services/payment` | 8004 | `voyara_payment` | Stripe (ou simulation), webhook signé + idempotent |
| `services/review` | 8005 | `voyara_review` | Avis et favoris |
| `services/notification` | 8006 | — | E-mails SMTP — interne uniquement |
| `services/admin` | 8007 | — | BFF de l'espace admin (agrégation `asyncio.gather` + `/batch`) |
| `services/ai` *(partiel — ADR-007)* | 8008 | `voyara_ai` (pgvector, conteneur `postgres-ai` :5435) | Moteur IA — étape 1 : modèles + scripts (POI, météo) ; scaffold FastAPI à l'étape 3 |
| `frontend/apps/client` | 5173 | — | Next.js 16 App Router (SSR/SEO) |
| `frontend/apps/admin` | 5174 (`/admin`) | — | SPA Vite/React |

PostgreSQL 16 en Docker, **port hôte 5434**, une base par service ; la base `voyara_ai` est dans un
conteneur dédié **`postgres-ai`** (`pgvector/pgvector:pg16`, **port hôte 5435**).
Packages front partagés : `frontend/packages/@voyara/{ui,api,auth,i18n}`.

## 2. Conventions (obligatoires)

- **Français partout** : code, commentaires, messages de commit, messages d'erreur, docs.
  Champs métier en français (`nom`, `prix`, `duree`, `places_disponibles`…).
- **Database-per-service** : aucune jointure SQL ni clé étrangère entre services. Une référence
  vers un autre domaine est un simple entier, validé par appel HTTP au service propriétaire.
- **Communication inter-services** : endpoints `/internal/*` protégés par `require_internal_key`
  (header `X-Internal-Api-Key` = `INTERNAL_API_KEY`), appelés via `voyara_common.internal.ServiceClient`.
  Jamais exposés par le gateway. Préférer les appels groupés (`/batch?ids=`) au N+1.
- **Réutiliser `libs/common/voyara_common`** au lieu de réécrire : `config`, `auth`
  (`get_current_identity`, `require_admin`), `internal`, `database`, `pagination`, `exceptions`,
  `logging`, `limiter`, `security`.
- **Découpage par domaine** : un nouveau besoin va dans le service qui possède la donnée
  (ex. les tags IA d'une activité vivent dans catalog, pas dans ai).
- **i18n** : tout texte d'interface passe par `@voyara/i18n` en **fr / en / ar** (RTL vérifié en arabe).
  Contenu métier traduit en base via colonnes `*_en` / `*_ar` (repli sur le français).
- **Secrets** : uniquement dans les fichiers `.env` (non versionnés). Jamais de clé API dans le code,
  les tests, les rapports ou les messages de commit.
- **Environnement** : Windows + PowerShell 5.1 (pas de `&&` : utiliser `;` ou `if ($?) { … }`).

## 3. Commandes utiles (PowerShell, depuis la racine)

```powershell
# Installation (une fois)
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\pip install -e libs/common

# Démarrage
docker compose up -d postgres         # Postgres sur localhost:5434
.\scripts\dev.ps1                     # postgres-ai (:5435) + gateway + 7 services (-Seed : crée l'admin initial)
.\scripts\stop-dev.ps1                # arrête les ports 8000-8007 et le conteneur postgres-ai
cd frontend; npm run dev              # client :5173 + admin :5174/admin

# Vérifications
# http://localhost:8000/health  ·  http://localhost:800X/docs (Swagger par service)

# Tests
cd services\auth; ..\..\.venv\Scripts\python -m pytest     # backend (parcours auth)
cd services\ai; ..\..\.venv\Scripts\python -m pytest       # moteur IA (postgres-ai démarré, réseau simulé)
cd frontend; npm run test                                   # vitest (client)
cd frontend; npm run typecheck                              # TypeScript strict (2 apps)
```

Guide d'installation complet pour un nouveau poste : [RUN.md](RUN.md).

## 4. Moteur IA — méthode de travail

- **Source des étapes** : [AgentIA_Voyara/Guide_Moteur_IA_Voyara.html](AgentIA_Voyara/Guide_Moteur_IA_Voyara.html)
  (étapes 0 à 13, un prompt par étape) et la présentation
  [AgentIA_Voyara/PresProjCom.pdf](AgentIA_Voyara/PresProjCom.pdf) (6 modules, 3 scénarios).
- **Une étape à la fois**, sur une branche dédiée `ia/etape-NN`, en plan mode : proposer le plan,
  attendre la validation, puis coder.
- Avant chaque étape : relire ce fichier, `docs/architecture.md`, `docs/plan.md`, `docs/mcd.md`,
  `docs/ia/` et **tous** les rapports de `docs/ia/rapports/`.
- Principe directeur : **le LLM comprend et explique ; les faits viennent de la base, le classement
  d'un score mesurable, le planning d'un solveur.**
- Ne jamais écrire qu'un test passe sans l'avoir lancé ; citer la sortie réelle des commandes.

## 5. Règle de clôture

**Chaque tâche se termine par un rapport dans `docs/ia/rapports/` selon le modèle de
[docs/ia/README.md](docs/ia/README.md#6-modèle-de-rapport-détape)**, puis :
une ligne dans [docs/ia/journal.md](docs/ia/journal.md) (date, étape, résumé),
la tâche cochée dans [docs/plan.md](docs/plan.md), le résumé du rapport affiché dans le chat
et un message de commit proposé.
