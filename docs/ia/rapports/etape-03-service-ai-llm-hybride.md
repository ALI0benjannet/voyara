# Étape 3 — Microservice `ai` et couche LLM hybride

> Date : 2026-10-30 · Branche : `ia/etape-03` · Module(s) : socle technique du moteur ·
> Source : [Guide_Moteur_IA_Voyara.pdf](../../../AgentIA_Voyara/Guide_Moteur_IA_Voyara.pdf) (v2, étape 3)

## 1. Objectif

Faire de `services/ai` un vrai microservice (port 8008, base `voyara_ai` + pgvector, gateway
`/api/ai`), doté d'une **interface LLM unique** (Claude API ou Ollama local, bascule automatique),
d'un **journal de chaque appel** (`llm_appels`) et d'un **client catalog** prêt pour les routes
internes de l'étape 2-bis.

Critère de « fini » du guide : *GET /api/ai/health OK via le gateway ; un appel test fonctionne avec
Ollama (et Claude si une clé est présente) ; le fallback se déclenche quand la clé Claude est
absente.* Résultat : **atteint pour la santé, Ollama et la bascule** (vrais appels en json, texte et outil ;
bascule `auto` sans clé vérifiée en réel). **Non vérifié pour Claude** : aucune clé n'était
disponible, donc le contrat est testé avec un faux client du SDK.

## 2. Réalisé

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `services/ai/app/main.py` | créé | FastAPI : logs, gestionnaires d'erreurs, slowapi, `lifespan` (extension `vector` + tables, client LLM, client catalog), `/health` |
| `services/ai/app/routes.py` | créé | `GET /api/ai/health` : base, version pgvector, fournisseur LLM, clé présente (oui/non), Ollama joignable |
| `services/ai/app/config.py` | modifié | `AUTO_CREATE_TABLES`, `CATALOG_SERVICE_URL`, variables LLM (`LLM_PROVIDER`, `CLAUDE_*`, `OLLAMA_*`) |
| `services/ai/app/llm/base.py` | créé | `Message`, `Outil`, `AppelOutil`, `ReponseLLM`, interface `LLMProvider.generer(...)`, erreurs typées |
| `services/ai/app/llm/claude.py` | créé | Fournisseur Claude (SDK `anthropic` 2.3.0) : outils natifs, `output_config` (format JSON, effort), repli serveur, refus |
| `services/ai/app/llm/ollama.py` | créé | Fournisseur Ollama (`/api/chat`) : JSON Schema, outils, `temperature`, tokens |
| `services/ai/app/llm/fabrique.py` | créé | `ClientLLM` : modes `claude` / `ollama` / `auto`, bascule, journalisation de chaque tentative |
| `services/ai/app/llm/journal.py` | créé | Écriture de `llm_appels` dans un thread, jamais bloquante ; `JournalMemoire` pour tests et scripts |
| `services/ai/app/llm/tarifs.py` | créé | Tarifs USD par million de tokens → `cout_estime` |
| `services/ai/app/models.py` | modifié | Modèle `LlmAppel` (table `llm_appels`) |
| `services/ai/app/clients/catalog.py` | créé | `ClientCatalog` (sur `ServiceClient`) : exports activités / séjours, aéroports, recherche vols / voitures / transferts, erreurs typées |
| `libs/common/voyara_common/internal.py` | modifié | `ServiceClient(transport=...)` facultatif (rétrocompatible) : tests avec `httpx.MockTransport` |
| `services/ai/scripts/essai_llm.py` | créé | Essai manuel réel : `--provider claude|ollama|auto`, `--mode texte|json|outil`, journalisé |
| `services/ai/tests/test_llm_claude.py`, `test_llm_ollama.py`, `test_fabrique.py`, `test_journal.py`, `test_client_catalog.py`, `test_main.py` | créés | 47 tests, aucun appel réseau réel (faux SDK, `MockTransport`) ; `conftest.py` : backend anyio |
| `services/ai/Dockerfile`, `requirements.txt` | créé / modifié | Image Python 3.11, port 8008 ; fastapi, uvicorn, slowapi, `anthropic==2.3.0` |
| `requirements-dev.txt` | modifié | `anthropic==2.3.0` |
| `gateway/app/main.py`, `gateway/app/config.py` | modifié | Route `/api/ai` → ai, `ai` dans le `/health` agrégé, `AI_SERVICE_URL` ; blocage `/internal` inchangé |
| `docker-compose.yml` | modifié | Service `ai` (base `postgres-ai`) ; service `ollama` (`ollama/ollama:0.40.6`, profil `ollama`, volume `voyara_ollama`) ; gateway → ai |
| `scripts/dev.ps1`, `scripts/stop-dev.ps1` | modifié | Démarrage de ai (:8008), arrêt des ports 8000-8008 |
| `config.py` + `.env.example` de gateway, admin, auth, booking, catalog, payment, review | modifié | URL inter-services `localhost` → `127.0.0.1` (limite n° 13) ; tes `.env` locaux : mêmes lignes uniquement |
| `.env.example`, `services/ai/.env.example` | modifié | `ANTHROPIC_API_KEY` vide, `LLM_PROVIDER`, `CLAUDE_*`, `OLLAMA_*`, `CATALOG_SERVICE_URL` |
| `docs/architecture.md`, `CLAUDE.md`, `docs/mcd.md`, `RUN.md`, `docs/plan.md`, `docs/ia/journal.md` | modifié | ADR-007 appliquée, routage, variables, limite n° 13 faite, `llm_appels`, démarrage d'Ollama, étape cochée |

## 3. Choix techniques

**Image Postgres : conteneur `postgres-ai` conservé** (validé avec toi)
- *Retenu* : on ne change pas l'image du Postgres principal (le prompt demandait de le faire) ; le
  service active `CREATE EXTENSION IF NOT EXISTS vector` dans `voyara_ai` au démarrage.
- *Écarté* : passer `postgres` à `pgvector/pgvector:pg16`, déjà refusé par l'ADR-007 à l'étape 1
  (musl → glibc : collations et `REINDEX` sur 5 bases en service, pour aucun gain).

**SDK Claude : `anthropic` 2.3.0, donc version d'API `2026-10-21`**
- Vérifié dans le SDK installé : `ANTHROPIC_API_VERSION = "2026-10-21"`, et `temperature` ne fait
  plus partie de la signature de `messages.create`.
- *Conséquence* : `temperature` reste dans l'interface (`generer(..., temperature=None)`, demandé par
  le guide) mais **n'est jamais envoyée à Claude** : avec cette version, elle donne une 400 sur tous
  les modèles, et Claude Sonnet 5.5 n'accepte de toute façon que la valeur par défaut. Ollama
  l'applique.
- *Écarté* : rester sur le SDK 0.x ou 1.x et l'ancienne version d'API (dette immédiate, et
  `temperature` est de toute façon refusée par Sonnet 5.5).

**Modèle Claude par défaut : `claude-sonnet-5-5`** (demandé par le guide), configurable par
`CLAUDE_MODEL`. Points propres à ce modèle, appliqués d'après la documentation :
- `tool_choice` reste `auto` : `any` / `tool` (choix forcé) renvoient une 400. `strict: true` est
  ajouté quand le schéma de l'outil est fermé (`additionalProperties: false`) ;
- la pensée adaptative est active par défaut (on n'envoie pas `thinking`). Les blocs `thinking` sont
  ignorés pour le texte, mais conservés dans `blocs_bruts` : l'agent de l'étape 8 devra les renvoyer
  tels quels ;
- `output_config.effort = medium` par défaut (`CLAUDE_EFFORT`) : assez pour de l'extraction, à
  mesurer à l'étape 4 ;
- sortie structurée par `output_config.format` (JSON Schema), plutôt qu'un outil forcé (impossible
  ici) ou un parsing de texte libre.

**Repli côté serveur sur refus de sécurité : activé par défaut**
- `fallbacks: "default"` + bêta `server-side-fallback-2026-07-01`, comme le recommande la
  documentation pour Sonnet 5.5 : si un classifieur refuse, l'API rejoue la requête sur un autre
  modèle dans le même appel. Désactivable par `CLAUDE_FALLBACKS=false`. Le modèle réellement utilisé
  (`response.model`) est journalisé et tarifé.

**Bascule `auto` : jamais sur un refus**
- *Retenu* : Claude, puis Ollama si la clé est absente ou refusée, en cas de panne réseau, de délai,
  de 429 ou de 5xx, ou si la requête est rejetée. Un **refus de sécurité ne bascule pas** :
  contourner un classifieur avec un modèle local irait contre sa décision. Une sortie JSON invalide
  ne bascule pas non plus (c'est un défaut à corriger, pas une panne).
- *Écarté* : basculer sur toute exception (masquerait les bugs) ; aucune bascule (pas de démo
  hors-ligne).
- Sans clé, `auto` ne tente même pas Claude : une ligne `bascule` « ANTHROPIC_API_KEY absente » est
  journalisée, puis Ollama est appelé (critère du guide).

**Peu de nouvelles tentatives côté SDK** : `CLAUDE_MAX_RETRIES=1`, `CLAUDE_TIMEOUT_S=60`. Le SDK
réessaie déjà 429 / 5xx / réseau ; en mode `auto`, mieux vaut basculer vite sur Ollama qu'attendre
3 × 10 min (délai par défaut du SDK).

**Journal `llm_appels`**
- *Retenu* : une ligne par **tentative** (une bascule = 2 lignes chaînées par `appel_parent_id`),
  écrite dans un thread ; une base indisponible est logguée et n'empêche jamais la réponse.
  **Aucun prompt, aucune réponse, aucune clé** n'est stocké (RGPD, étape 12) ; l'erreur est tronquée
  à 500 caractères.
- *Écarté* : journaliser les prompts (données personnelles possibles dans les demandes de voyage) ;
  écrire de façon synchrone dans la requête (latence ajoutée).
- `cout_estime` est en **USD** (tarifs publics : Sonnet 5.5 2 $ / 10 $ par million de tokens,
  Opus 5.5 4 $ / 20 $, Haiku 5.5 0,10 $ / 0,50 $). Les tokens de pensée sont inclus dans les tokens de
  sortie. Ollama = 0. Modèle inconnu = `NULL` (pas de tarif inventé).

**Ollama : `/api/chat` en httpx, modèle `qwen2.5:3b`**
- `format` reçoit le **JSON Schema** (sortie contrainte, plus fiable que le simple `"json"`), les
  outils au format « function ».
- *Modèle* : tu avais choisi `qwen2.5:7b`. Il n'a pas pu se charger : Docker Desktop dispose de
  3,7 Go et le modèle en demande environ 4,4 Go ; le poste a 7,7 Go en tout (§4). Avec ton accord,
  le défaut est passé à **`qwen2.5:3b`** ; le 7b reste téléchargé pour une machine de 16 Go ou plus.

**Client catalog sur `ServiceClient`, avec transport injectable**
- *Retenu* : un paramètre `transport` facultatif ajouté à `voyara_common.internal.ServiceClient`
  (rétrocompatible, aucun autre service modifié), ce qui permet des tests sans réseau.
- *Écarté* : un second client httpx propre au service ai (duplication de la gestion de la clé
  interne) ; « monkeypatcher » httpx (fragile).
- Erreurs typées : `CatalogLieuInconnu` (404 : l'agent pourra poser une question),
  `CatalogRequeteInvalide` (422), `CatalogAccesRefuse` (401 / 403 : clés internes différentes),
  `CatalogIndisponible` (réseau, délai, 5xx : dégradation propre à l'étape 5, jamais d'offre
  inventée).

**URL `127.0.0.1` partout** (validé) : voir §5. *Écarté* : corriger seulement ai (le BFF admin et la
saga booking payaient aussi la pénalité à chaque appel interne).

**Préfixe public `/api/ai`** (et non `/api/v1/ai`) : celui fixé par l'ADR-007 et le guide. Le
gateway le route comme les autres préfixes ; `/internal` reste bloqué même sous `/api/ai`.

**Tests asynchrones avec `anyio`** : le plugin est déjà présent (dépendance de httpx et starlette).
*Écarté* : ajouter `pytest-asyncio`, une dépendance de plus pour le même service rendu.

**Limiteur slowapi branché, sans limite posée** : `app.state.limiter` et son gestionnaire sont en
place ; les limites par route arrivent avec les premiers endpoints coûteux (`/api/ai/comprendre`,
étape 4). Limiter `/health` n'aurait pas de sens.

## 4. Vérification

**Tests (aucun appel réseau réel : faux SDK Claude, `MockTransport` pour Ollama et catalog)** :

```text
PS services\ai>      ..\..\.venv\Scripts\python -m pytest -q -p no:warnings
111 passed in 6.67s          # 64 des étapes 1 et 2-bis + 47 nouveaux
PS services\catalog> ..\..\.venv\Scripts\python -m pytest -q -p no:warnings
88 passed in 4.33s           # non-régression (ServiceClient et URL modifiés)
PS services\auth>    ..\..\.venv\Scripts\python -m pytest -q -p no:warnings
5 passed in 0.91s
```

Les 46 premiers nouveaux tests sont passés du premier coup. Le 47ᵉ
(`test_latence_journalisee_meme_en_erreur`) a été ajouté après l'essai réel, voir plus bas.

**Docker** :

```text
PS> docker compose config -q                      # → config valide
PS> docker compose build ai                       # → Image voyara-ai Built
PS> docker run --rm -e POSTGRES_USER=x -e POSTGRES_PASSWORD=x -e JWT_SECRET_KEY=x voyara-ai `
      python -c "...from app.main import app..."
3.11.18 anthropic 2.3.0 ['/api/ai/health', '/health']
```

**Gateway et santé** (services relancés par `dev.ps1`, qui démarre maintenant ai) :

```text
GET /health : {"status": "ok", "services": {"auth": "ok", "catalog": "ok", "booking": "ok",
  "payment": "ok", "review": "ok", "notification": "ok", "admin": "ok", "ai": "ok"}}
GET /api/ai/health : 200 {"service": "ai-service", "status": "ok", "base": "ok", "pgvector": "0.8.7",
  "llm": {"provider": "auto", "claude": {"modele": "claude-sonnet-5-5", "cle_configuree": false},
          "ollama": {"modele": "qwen2.5:3b", "joignable": true}}}
GET /api/ai/internal/reindexer : 404      # /internal bloqué, même sous /api/ai
GET /internal/airports : 404
```

Incident, signalé tel quel : au premier redémarrage, le `/health` agrégé a montré
`catalog: unreachable`. Le reloader uvicorn de catalog tenait le port 8002 (état `Bound`) sans
aucun worker vivant ; la console minimisée ne montrait aucune erreur. Un redémarrage de catalog a
suffi, et le second `dev.ps1` a tout démarré correctement. Cause **non identifiée**.

**Postgres principal intact** :

```text
voyara-postgres-1    postgres:16-alpine        # image inchangée
voyara-postgres-ai-1 pgvector/pgvector:pg16
bases : postgres touribook* voyara voyara_booking voyara_catalog voyara_payment voyara_review
extension vector dans voyara_catalog : 0
voyara_ai : vector 0.8.7 ; tables llm_appels, meteo_cache, pois
```

**Client catalog en réel** (catalog lancé) :

```text
vols Tunis->Djerba 2026-11-04 : 4 offres, 1re = UG103 372.0 DT (382 ms)
séjours exportés : 27
transferts DJE->Midoun 4 pax : 3
lieu inconnu -> CatalogLieuInconnu : Lieu inconnu : Atlantide
```

**Essais LLM réels** (`scripts/essai_llm.py`) :

1. Claude sans clé, en mode strict :

```text
PS> python scripts\essai_llm.py --provider claude
✗ LLMCleAbsente (claude) : ANTHROPIC_API_KEY absente de la configuration      # code 1
```

2. Ollama `qwen2.5:7b` (ton premier choix) : **échec**. Les trois modes ont donné un délai dépassé
   puis des erreurs 500. Journal d'Ollama :

```text
load_tensors: CPU model buffer size = 1483.70 MiB ; CPU_REPACK model buffer size = 2976.75 MiB
msg="Load failed" ... error="llama-server process no longer running: unknown"
[GIN] | 500 | 1m49s | POST "/api/chat"
RAM Docker : 3,7 Go · RAM physique : 7,7 Go (0,6 Go libres)
```

   Le modèle demande environ 4,4 Go et Docker n'en a que 3,7 : le processus est tué au chargement.
   Avec ton accord, je suis passé à `qwen2.5:3b`.

3. Ollama `qwen2.5:3b`, services de dev lancés : seul le mode texte a abouti, en **167 744 ms** pour
   51 tokens. Les modes json et outil ont dépassé le délai de 180 s. Journal :
   `eval time = 160195 ms / 51 tokens (0.31 tokens per second)`, la machine étant saturée en mémoire.

4. Après arrêt temporaire des 9 services de dev (seul `postgres-ai` reste) :

```text
PS> python scripts\essai_llm.py --provider ollama --mode json
✓ Servi par ollama (qwen2.5:3b)
  latence 58635 ms · tokens 93 -> 60 · coût estimé 0.0 USD · arrêt : stop
  données : {"destination": "Jerba", "duree_jours": 3, "budget_total_dt": 300, "nb_adultes": 2,
             "nb_enfants": 2, "preferences": ["culture", "plage"]}

PS> python scripts\essai_llm.py --provider auto --mode texte          # sans clé Claude
✓ Servi par ollama (qwen2.5:3b), après bascule depuis claude
  latence 58206 ms · tokens 71 -> 51 · coût estimé 0.0 USD · arrêt : stop

PS> python scripts\essai_llm.py --provider ollama --mode outil         # délai de 180 s
✗ LLMIndisponible (ollama) : délai dépassé
PS> $env:OLLAMA_TIMEOUT_S = "600"; python scripts\essai_llm.py --provider ollama --mode outil
✓ Servi par ollama (qwen2.5:3b)
  latence 237091 ms · tokens 224 -> 55 · coût estimé 0.0 USD · arrêt : tool_use
  appel d'outil : meteo({"ville": "Djerba", "date": "2026-11-07"})
```

**Journal `llm_appels`** (SQL réel, extrait) :

```text
 id | provider | modele            | statut  | t_in | t_out | latence_ms | parent | erreur
  5 | claude   | claude-sonnet-5-5 | erreur  |    0 |     0 |          0 |        | LLMCleAbsente: ANTHROPIC_API_KEY absente…
  6 | ollama   | qwen2.5:7b        | erreur  |    0 |     0 |          0 |        | LLMIndisponible: délai dépassé
  7 | ollama   | qwen2.5:7b        | erreur  |    0 |     0 |          0 |        | LLMIndisponible: erreur serveur (500)
 16 | ollama   | qwen2.5:3b        | succes  |   93 |    60 |      58635 |        |
 18 | claude   | claude-sonnet-5-5 | bascule |    0 |     0 |          0 |        | ANTHROPIC_API_KEY absente
 19 | ollama   | qwen2.5:3b        | succes  |   71 |    51 |      58206 |     18 |
 20 | ollama   | qwen2.5:3b        | succes  |  224 |    55 |     237091 |        |
```

Défaut trouvé grâce à cet essai : les tentatives en erreur étaient journalisées avec
`latence_ms = 0`, alors qu'un délai dépassé coûtait 180 s. **Corrigé** : la fabrique mesure
maintenant le temps aussi en cas d'erreur ou de refus, et un test le vérifie (111 tests verts). Les
lignes 5 à 17 ci-dessus datent d'avant la correction. Les numéros manquants viennent des tests,
dont les transactions sont annulées.

## 5. Métriques

Jeu d'essai : les 3 requêtes fixes de `essai_llm.py` (texte : une question sur Sidi Bou Saïd ;
json : « Je vais à Jerba 3 jours avec ma femme et nos deux enfants, 300 dinars, culture et plage » ;
outil : la météo à Djerba le 07/11) ; machine : 12 cœurs, 7,7 Go de RAM, Docker 3,7 Go, sans GPU.

| Mesure | Valeur |
|---|---|
| Tests | ai **111** (47 nouveaux), catalog 88, auth 5, tous verts |
| `qwen2.5:7b` | ne se charge pas (≈ 4,4 Go nécessaires contre 3,7 Go disponibles) |
| `qwen2.5:3b`, services de dev arrêtés | json **58,6 s** (93 → 60 tokens) · texte 58,2 s · outil 237 s (224 → 55 tokens) |
| `qwen2.5:3b`, services de dev lancés | texte 167,7 s (0,31 token/s) ; json et outil > 180 s |
| Débit de génération Ollama | 0,3 à 1,2 token/s (journal `print_timing`), limité par la mémoire |
| Extraction json (1 cas) | 6/6 champs corrects ; destination « Jerba » non normalisée (normalisation prévue à l'étape 4) |
| Appel d'outil (1 cas) | outil et arguments corrects, `stop_reason = tool_use` |
| Coût | 0 USD (Ollama) ; Claude non mesuré (pas de clé) |
| `ServiceClient` → catalog, p50 sur 10 appels | `localhost` **282 ms** → `127.0.0.1` **29 ms** |
| Gateway → catalog, p50 sur 10 appels | 10 ms → 9 ms (connexion persistante, peu touchée) |

Ces chiffres ne mesurent pas la qualité : un seul cas par mode. La qualité d'extraction (F1 par
champ, Claude contre Ollama) est l'objet de l'étape 4.

## 6. Limites, dette technique, risques

- **Claude jamais appelé en réel** : aucune clé disponible. Le contrat (paramètres envoyés, réponses,
  erreurs) est testé avec un faux client construit sur les types du SDK 2.3.0 et sur la
  documentation ; un premier appel réel peut encore révéler un écart, par exemple sur
  `fallbacks="default"` ou sur `output_config` côté bêta.
- **Ollama trop lent sur ce poste** pour une démo interactive : 1 à 4 minutes par appel avec
  `qwen2.5:3b`. Un délai de 180 s ne suffit pas aux appels d'outils (237 s mesurés). Pistes, par
  ordre d'effet : une clé Claude pour la démo ; une machine de 16 Go ou plus, ou un GPU ; plus de
  RAM pour Docker (`.wslconfig`) ; fermer les services inutiles pendant la démo ;
  `OLLAMA_TIMEOUT_S=600` en attendant.
- **`qwen2.5:3b` plus faible que le 7b**, surtout en arabe et en darija : à mesurer à l'étape 4. Le
  7b reste téléchargé dans le volume `voyara_ollama` (4,7 Go de disque) ; `ollama rm qwen2.5:7b`
  libère la place si besoin.
- **Pas de streaming** : `generer` renvoie la réponse complète. Le SSE de l'agent (étape 8) demandera
  une méthode `diffuser` ; `max_tokens = 16000` sans streaming reste sous les délais HTTP.
- **Messages en texte seul** : `Message(role, contenu)` ne porte ni image ni résultat d'outil.
  L'agent de l'étape 8 devra renvoyer `blocs_bruts` et des `tool_result` : l'interface sera étendue,
  sans casser la signature actuelle.
- **Mode `auto` : bascule sur `LLMRequeteInvalide`** (400) : pratique en démo, mais cela peut masquer
  un bug de requête. Le journal garde la trace (statut `bascule`, message d'erreur).
- **`cout_estime` en USD** avec des tarifs codés en dur, à mettre à jour si les prix changent.
  Haiku 5.5 est plus cher au-delà de 100 000 tokens de prompt, ce que le calcul ignore.
- **Incident catalog non expliqué** au premier redémarrage (worker disparu, port gardé par le
  reloader). Si cela revient, lancer catalog seul pour lire ses logs.
- **Aucune limite slowapi posée** pour l'instant (pas encore d'endpoint coûteux).
- Le `docker compose up` complet n'a pas été lancé (seuls `build ai` et le service `ollama` l'ont
  été) : la pile de dev tourne en processus locaux.

## 7. À vérifier par moi

1. `git checkout ia/etape-03` ; `.venv\Scripts\pip install -r requirements-dev.txt` (installe
   `anthropic==2.3.0`).
2. `cd services\ai ; ..\..\.venv\Scripts\python -m pytest -q` → `111 passed` ; `cd ..\catalog ;
   ..\..\.venv\Scripts\python -m pytest -q` → `88 passed`.
3. `.\scripts\stop-dev.ps1 ; .\scripts\dev.ps1` : la liste affiche `ai http://localhost:8008`.
4. Ouvre `http://127.0.0.1:8000/health` : 8 services `ok`, dont `ai`. Puis
   `http://127.0.0.1:8000/api/ai/health` : `pgvector: "0.8.7"`, `cle_configuree: false`.
5. `docker compose --profile ollama up -d ollama`, puis `docker compose exec ollama ollama list` :
   `qwen2.5:3b` doit apparaître.
6. `cd services\ai ; $env:OLLAMA_TIMEOUT_S = "600" ; ..\..\.venv\Scripts\python scripts\essai_llm.py
   --provider auto --mode json` → « Servi par ollama (qwen2.5:3b), après bascule depuis claude ». Sois
   patient : environ 1 minute si tu as fermé le reste, plus sinon.
7. (Avec une clé) place **toi-même** `ANTHROPIC_API_KEY=...` dans `services/ai/.env`, puis lance
   `essai_llm.py --provider claude --mode json`, puis `--mode outil`. C'est le seul point que je n'ai
   pas pu vérifier.
8. Vérifie le journal : `docker exec voyara-postgres-ai-1 psql -U <utilisateur> -d voyara_ai -c
   "select id, provider, modele, statut, tokens_entree, tokens_sortie, latence_ms, cout_estime,
   appel_parent_id from llm_appels order by id desc limit 5"`.
9. Vérifie `git diff -- services/*/.env.example gateway/.env.example` : seules les URL ont changé.
   Tes `.env` locaux, non versionnés, ont reçu le même remplacement sur les lignes `*_SERVICE_URL`.

## 8. Étape suivante recommandée

**Étape 4 — Module 1 : comprendre le voyageur (NLU)**, sur `ia/etape-04` : `DemandeVoyage` avec
le bloc transport, `POST /api/ai/comprendre` (première route limitée par slowapi), 100 demandes
annotées (au moins 20 en arabe ou darija, au moins 25 avec transport), F1 par champ.

Prérequis et recommandations :
- décider du fournisseur de l'évaluation. Avec Ollama sur ce poste, compter environ 1 minute par
  demande, soit 100 demandes ≈ 1 h 40 par passe, services fermés. Une clé Claude rendrait
  l'évaluation et la comparaison Claude / Ollama bien plus réalistes ;
- prévoir `OLLAMA_TIMEOUT_S` à 600 pour l'évaluation hors-ligne ;
- la normalisation post-LLM (« Jerba » → « Djerba », « 300 dinars » → 300) est déjà justifiée par
  l'essai de cette étape ;
- toujours ouverte depuis l'étape 2 : la validation humaine des tags (0 / 117).
