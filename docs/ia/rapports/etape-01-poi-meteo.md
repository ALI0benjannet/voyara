# Étape 01 — Données : points d'intérêt OpenStreetMap, météo et analyse exploratoire

> Date : 2026-10-13 · Branche : ia/etape-01 · Module(s) : 2 (recherche & collecte)
> Clôt l'étape 1, avec les sous-tâches déjà livrées : [seed du catalogue](etape-01-seed-catalogue.md)
> et [photos du catalogue](etape-01-photos-catalogue.md).

## 1. Objectif

Donner au moteur IA ce que le catalogue n'a pas : des **points d'intérêt** (restaurants, cafés,
plages, musées, monuments, souks, parcs) pour remplir un itinéraire autour des activités
réservables, et la **météo**. Les données viennent de sources ouvertes (OpenStreetMap / Overpass,
Open-Meteo), pas d'un scraping de sites commerciaux. Il fallait ensuite les analyser dans un notebook.

Critère de « fini » du guide : **≥ 300 POI sur au moins 5 villes, météo disponible pour Djerba,
notebook exécuté sans erreur.** → **atteint** : 1 030 POI sur 8 villes, 7 jours de météo à Djerba
(56 jours sur les 8 villes), notebook exécuté avec 0 erreur.

## 2. Réalisé

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `docker-compose.yml` | modifié | Service `postgres-ai` (`pgvector/pgvector:pg16`, base `voyara_ai`, port 5435, volume `voyara_pgdata_ai`, healthcheck) |
| `scripts/dev.ps1` | modifié | Étape « 1b » : démarre `postgres-ai` et attend `healthy` ; non bloquant sans Docker |
| `scripts/stop-dev.ps1` | modifié | Arrête aussi `postgres-ai` (données conservées) ; le Postgres principal n'est pas touché |
| `.env.example` | modifié | Note sur `postgres-ai` (mêmes identifiants, port 5435) |
| `services/ai/.env.example` | créé | Modèle de configuration du service `ai` (port 5435, URL Overpass / Open-Meteo, cache 6 h) |
| `services/ai/app/config.py` | créé | `Settings(CommonSettings)` calqué sur catalog, `DATABASE_URL` via `build_postgres_url` |
| `services/ai/app/database.py` | créé | `create_session_factory`, `Base`, `get_db` (identique à catalog) |
| `services/ai/app/models.py` | créé | Tables `pois` (unique `source_id`, index `(ville, type)`) et `meteo_cache` (unique `(ville, date)`) |
| `services/ai/app/villes.py` | créé | Référentiel des 8 villes (centre GPS, rayon de collecte) + recherche tolérante aux accents |
| `services/ai/app/osm.py` | créé | Mapping tags OSM → 7 types, noms fr/en/ar, normalisation des horaires, prix (`charge`, `fee=no`) |
| `services/ai/app/collecte.py` | créé | Requête Overpass, nouvelles tentatives, plafond par type, upsert `ON CONFLICT (source_id)` |
| `services/ai/app/meteo.py` | créé | Client Open-Meteo + cache 6 h, nouvelle tentative sur 5xx, repli sur cache périmé |
| `services/ai/scripts/collecter_pois.py` | créé | CLI : `--ville` (répétable), `--max-par-type`, `--dry-run`, bilan, code 1 si une ville échoue |
| `services/ai/scripts/rafraichir_meteo.py` | créé | CLI : remplit le cache météo (`--ville`, `--jours`) |
| `services/ai/tests/` (4 fichiers) | créé | 55 tests pytest, réseau simulé (`httpx.MockTransport`), base annulée par transaction |
| `services/ai/requirements.txt`, `pytest.ini` | créé | Dépendances (pour le futur Dockerfile, étape 3) et configuration pytest |
| `notebooks/01_eda_donnees.ipynb` | créé | Analyse exploratoire POI + 86 activités du seed + météo, exécutée, sorties incluses |
| `docs/ia/figures/etape01_*.png` | créé | 7 figures pour le rapport de PFE |
| `requirements-dev.txt` | modifié | pandas, matplotlib, nbformat, nbconvert, ipykernel (versions épinglées) |
| `docs/architecture.md` | modifié | ADR-007 : décision du conteneur dédié, alternative écartée, conséquences ; tableau de déploiement, schéma |
| `docs/mcd.md` | modifié | §5 bis : diagramme ER de `voyara_ai` |
| `docs/plan.md` | modifié | Étape 1 cochée ; étape 3 : « décidé à l'étape 1 » au lieu de « à trancher » |
| `CLAUDE.md`, `RUN.md` | modifié | `postgres-ai` / 5435, `services/ai/.env`, commandes de collecte, météo, tests et notebook |
| `docs/ia/README.md`, `docs/ia/journal.md` | modifié | Index des rapports, ligne de journal |

`infra/postgres/init.sql` et `scripts/create_databases.py` **n'ont pas été modifiés** (voir §3).

## 3. Choix techniques

**Stockage : un conteneur Postgres dédié `postgres-ai` (décision de l'étudiant, 13/10/2026).**
- *Retenu* : `pgvector/pgvector:pg16`, base `voyara_ai` créée par `POSTGRES_DB`, port hôte 5435 et
  volume propre. Le conteneur `postgres` et ses 5 bases ne bougent pas (vérifié par `psql -l`, §4).
- *Écarté* : changer l'image du Postgres principal. `postgres:16-alpine` repose sur musl, l'image
  pgvector sur Debian/glibc : l'ordre des collations peut changer, ce qui impose un `REINDEX` des
  5 bases en service. Le risque est réel et le gain nul, car aucun service existant n'utilise pgvector.
- *Écarté* : PostgreSQL local hors Docker, ou une base vectorielle externe (déjà écartée par ADR-007).
- *Effets* : isolation des pannes, de la charge et des sauvegardes du moteur IA (objectif d'ADR-007) ;
  en contrepartie, un conteneur de plus, démarré et arrêté par `dev.ps1` et `stop-dev.ps1`.

**Écarts volontaires au prompt du guide**
- Le prompt demandait d'ajouter `voyara_ai` à `infra/init.sql` et à `create_databases.py`. Ces deux
  fichiers ciblent le conteneur **principal** : y ajouter `voyara_ai` créerait une base fantôme au
  mauvais endroit. La base est créée par `POSTGRES_DB` dans son propre conteneur.
- `voyara_common.exceptions` ne contient que des handlers FastAPI, sans classe d'erreur métier.
  `meteo.py` définit donc `MeteoIndisponible`, que l'étape 3 traduira en HTTP 503.
- La logique de collecte vit dans `app/collecte.py`, et `scripts/collecter_pois.py` n'est qu'une
  interface de ligne de commande. Les tests importent ainsi la logique sans passer par un script.

**Collecte Overpass**
- *Requête par cercle* (`around:rayon,lat,lon`) plutôt que par zone administrative OSM : les limites
  administratives tunisiennes sont incomplètes dans OSM (Djerba est répartie entre plusieurs
  délégations), alors qu'un cercle est explicite et reproductible.
- *Uniquement les objets nommés* (`["name"]` dans la requête) : un POI sans nom est inutilisable
  dans un itinéraire.
- *Plafond de 60 par couple (ville, type)*, sélection déterministe par identifiant OSM. Sans
  plafond, Tunis ramène plusieurs centaines de restaurants et domine tout le jeu.
  - Alternative écartée : un échantillon aléatoire (non reproductible).
  - Alternative écartée : préférer les POI les mieux renseignés, ce qui fausserait les taux de
    valeurs manquantes mesurés par l'EDA.
- *Idempotence* : `INSERT … ON CONFLICT (source_id) DO UPDATE … RETURNING (xmax = 0)`. Une relance
  met à jour au lieu de dupliquer, et compte séparément les insertions et les mises à jour.
- *Respect du serveur public*, avec un User-Agent sans donnée personnelle :
  - 5 s de pause entre deux villes ;
  - 1 essai + 3 nouvelles tentatives (attentes de 10, 30 puis 60 s) sur 429, 502, 503, 504, les
    erreurs réseau et la remarque `runtime error` qu'Overpass renvoie avec un code 200 ;
  - une ville en échec n'arrête pas les autres et le code de sortie vaut 1.
- *Mapping* : priorité musée > monument > souk > plage > parc > restaurant > café (un musée installé
  dans un fort reste un musée). `tourism=attraction` sans `historic` est ignoré, car trop hétérogène.
- *Horaires* : le texte OSM brut est toujours conservé, et une version par jour
  (`{"lundi": [["09:00","18:00"]], …}`) est ajoutée quand la syntaxe est reconnue. Un analyseur
  partiel est assumé : une règle non reconnue donne `null` plutôt qu'une contrainte fausse.

**Météo**
- Cache valide **6 h**, et seulement si **toutes** les dates demandées sont présentes. Sinon, un seul
  appel couvre toute la plage (au plus 16 jours, la limite d'Open-Meteo), suivi d'un upsert sur
  `(ville, date)`.
- *Ajout pendant l'implémentation* : une nouvelle tentative après 2 s sur un 5xx ou une erreur
  réseau. Open-Meteo a renvoyé des 503 passagers pendant la vérification (§4).
- *Dégradation* : si Open-Meteo est injoignable, le cache périmé est renvoyé avec `perime=True`.
  Sans cache, `MeteoIndisponible` est levée. Un itinéraire reste ainsi constructible hors-ligne
  (plan B de la démo).

**Notebook**
- Les activités sont lues depuis la constante `ACTIVITES` du script de seed (via `importlib`, sans
  base). Le notebook ne lit **jamais** `voyara_catalog` (database-per-service), et l'analyse est
  reproductible sans les services.
- Les cartes sont faites avec matplotlib seul (pas de geopandas ni de fond de carte) : rien à
  télécharger, rien qui puisse casser à l'exécution.

**Tests**
- Base `voyara_ai` réelle, chaque test étant annulé par transaction
  (`join_transaction_mode="create_savepoint"`), comme `services/auth/tests`. Réseau toujours simulé.
- Les tests ne comptent que leurs propres lignes (`node/101`, `node/102`, météo en 2099) : ils
  passent même avec les vraies données en base. Cette correction a été faite après un premier
  échec, voir §4.

## 4. Vérification

Conteneurs et bases (le Postgres principal est intact) :

```text
> docker compose ps
voyara-postgres-1    postgres:16-alpine       Up 11 seconds (healthy)  0.0.0.0:5434->5432/tcp
voyara-postgres-ai-1 pgvector/pgvector:pg16   Up 10 seconds (healthy)  0.0.0.0:5435->5432/tcp

> docker compose exec -T postgres-ai psql -U voyara_user -d voyara_ai -c "select name, default_version from pg_available_extensions where name='vector'"
 vector | 0.8.7

> docker compose exec -T postgres psql -U voyara_user -d voyara -c "select datname from pg_database order by 1"
 voyara / voyara_booking / voyara_catalog / voyara_payment / voyara_review   (+ postgres, template*, anciennes touribook*)
```

Tests (`cd services\ai; ..\..\.venv\Scripts\python -m pytest -v`) :

```text
collected 55 items
tests/test_collecte.py::test_reessaie_apres_429_puis_reussit PASSED
tests/test_collecte.py::test_abandon_apres_tous_les_essais PASSED
tests/test_collecte.py::test_upsert_idempotent PASSED
tests/test_meteo.py::test_second_appel_avant_6h_sert_le_cache PASSED
tests/test_meteo.py::test_hors_ligne_avec_cache_perime_renvoie_le_cache_marque PASSED
tests/test_meteo.py::test_503_passager_puis_succes PASSED
tests/test_osm.py::test_horaires_plusieurs_regles PASSED
…
55 passed in 1.10s
```

Échecs rencontrés pendant l'étape, tels quels :
- `test_noeud_complet` : mon assertion supposait un arrondi décimal exact
  (`33.8751234 != 33.8751235`). Le test a été corrigé avec des coordonnées à 4 décimales.
- `test_upsert_idempotent` : `assert 1032 == 2`, parce que le test comptait toute la table après la
  vraie collecte. Il a été restreint à ses propres identifiants. 1 032 = 1 030 réels + 2 du test,
  donc rien n'a été perdu.

Collecte réelle (`python scripts\collecter_pois.py`) :
- **Premier passage** : Tunis et Sousse ont échoué après 4 réponses 504, comme prévu.

  ```text
  → Djerba (rayon 16 km)...      187 POI : 187 insérés, 0 mis à jour
  ✗ Tunis : échec après 4 essais : HTTP 504
  → Sidi Bou Saïd                134 POI : 134 insérés
  ✗ Sousse : échec après 4 essais : HTTP 504
  → Hammamet 137 · Monastir 97 · Tozeur 43 · Kairouan 35 (insérés)
  Base voyara_ai : 633 POI sur 6 villes.
  Villes en échec : Tunis, Sousse — relancer avec --ville.        (code 1)
  ```

- **Relance ciblée** (`--ville Tunis --ville Sousse`) :

  ```text
  → Tunis   236 POI : 236 insérés, 0 mis à jour
  → Sousse  161 POI : 161 insérés, 0 mis à jour
  Base voyara_ai : 1030 POI sur 8 villes.                          (code 0)
  ```

- **Relance complète, test d'idempotence** : aucune nouvelle ligne. Monastir a de nouveau échoué
  sur des 504, le total est inchangé.

  ```text
  → Djerba 187 POI : 0 insérés, 187 mis à jour
  → Tunis 236 : 0 insérés, 236 mis à jour · Sidi Bou Saïd 134 : 0 / 134 · Sousse 161 : 0 / 161
  → Hammamet 137 : 0 / 137 · Tozeur 43 : 0 / 43 · Kairouan 35 : 0 / 35
  Base voyara_ai : 1030 POI sur 8 villes.
  Villes en échec : Monastir — relancer avec --ville.              (code 1)
  ```

Météo (`python scripts\rafraichir_meteo.py --ville Djerba`) :
- **Premier essai** : Open-Meteo a renvoyé un 503 et il n'y avait pas encore de cache, d'où
  « ✗ Météo indisponible pour Djerba et aucun cache », avec le code 1. Un appel direct à l'API a
  répondu 200 quelques secondes plus tard : panne passagère. La nouvelle tentative de 2 s a été
  ajoutée à ce moment-là.
- **Après correction** :

  ```text
  Djerba
    2026-10-13   23.2 /  26.8 °C  pluie   0.4 mm  code WMO 80
    2026-10-14   20.7 /  25.6 °C  pluie   0.0 mm  code WMO 2
    …
    2026-10-19   24.5 /  27.6 °C  pluie   0.0 mm  code WMO 3
  ```

- **Second appel**, avec les logs `httpx` au niveau INFO : aucune requête HTTP n'est journalisée
  (le cache sert) et l'appel affiche `7 jours, perime = False`.
- **Toutes les villes** : Sidi Bou Saïd a reçu deux 503 de suite (code 1) ; une relance avec
  `--ville "Sidi Bou Said"` a réussi. Le cache contient 56 jours, soit 8 villes × 7 jours.

Notebook :

```text
> .venv\Scripts\jupyter nbconvert --to notebook --execute --inplace notebooks\01_eda_donnees.ipynb
[NbConvertApp] Writing … bytes to notebooks\01_eda_donnees.ipynb      (exit 0)
cellule « Critère » : OK : 1030 POI, 8 villes, 7 jours de météo à Djerba
erreurs dans les sorties : 0 ; 7 figures écrites dans docs/ia/figures/
```

Scripts de démarrage :

```text
> .\scripts\dev.ps1
1b) Base du moteur IA (conteneur postgres-ai, port 5435)...
   postgres-ai pret (voyara_ai sur localhost:5435)
> .\scripts\stop-dev.ps1
24 processus arretes.
postgres-ai arrete (donnees conservees).
> docker compose ps -a     → voyara-postgres-1 Up 32 minutes (healthy) · voyara-postgres-ai-1 Exited (0)
> (redémarrage) select count(*) from pois → 1030 ; meteo_cache → 56
```

Le mot de passe Postgres a été recherché dans `notebooks/`, `services/ai/` (hors `.env`) et `docs/`
avec 0 occurrence. `services/ai/.env` est bien ignoré par Git.

## 5. Métriques

**Jeu de données**
- Source : OpenStreetMap via `overpass-api.de`, extraction du 13/10/2026, licence ODbL.
- Paramètres : 8 villes, rayons de 2 à 16 km, plafond de 60 par (ville, type).
- Les 86 activités viennent de `seed_catalogue_demo.py`.

**Volumes de POI par ville et par type**

| Ville | restaurant | café | plage | musée | monument | souk | parc | **total** |
|---|---|---|---|---|---|---|---|---|
| Djerba | 51 | 60 | 10 | 7 | 51 | 0 | 8 | **187** |
| Tunis | 60 | 60 | 0 | 12 | 60 | 25 | 19 | **236** |
| Sidi Bou Saïd | 55 | 42 | 3 | 4 | 24 | 2 | 4 | **134** |
| Sousse | 60 | 60 | 12 | 5 | 10 | 6 | 8 | **161** |
| Hammamet | 60 | 60 | 4 | 0 | 2 | 3 | 8 | **137** |
| Monastir | 22 | 49 | 1 | 4 | 10 | 4 | 7 | **97** |
| Tozeur | 9 | 19 | 0 | 4 | 0 | 2 | 9 | **43** |
| Kairouan | 5 | 17 | 0 | 3 | 6 | 3 | 1 | **35** |
| **Total** | 322 | 367 | 30 | 39 | 163 | 45 | 64 | **1 030** |

**Valeurs manquantes (toutes villes)**

| Champ | % manquant |
|---|---|
| horaires (brut OSM) | 93,2 % |
| horaires normalisés | 93,8 % |
| nom_en | 85,4 % |
| nom_ar | 71,3 % |
| prix_moyen | 99,7 % |

Sur les 70 POI qui ont des horaires, 64 sont analysés (91 %).

**Doublons probables** (même nom normalisé, même ville, moins de 50 m) : 21 paires, soit 2,0 % des
POI. Ce sont surtout des lieux cartographiés deux fois (un nœud et un contour, par exemple le
mausolée Bourguiba).

**Couverture croisée avec les 86 activités**
- Distance médiane au POI le plus proche : 0,20 km.
- 13 activités sans POI à moins de 2 km. Ce sont des excursions : gorges de Mides (55,7 km),
  Nefta, Ong Jemel, Boukornine, lagune de Bin El Ouedian…
- Kairouan : 35 POI mais **0 activité** dans son rayon.

**Météo** : 56 jours en cache (8 villes × 7 jours).

**Tests** : 55 tests, tous verts.

Figures : `etape01_poi_par_ville_type.png`, `etape01_valeurs_manquantes.png`,
`etape01_carte_poi_activites.png`, `etape01_carte_tunisie.png`, `etape01_activites_seed.png`,
`etape01_distance_activite_poi.png`, `etape01_meteo.png`.

## 6. Limites, dette technique, risques

**Données**
- **Prix presque absents** (99,7 %). OSM ne porte pas de prix : le budget repas du module 5 devra
  partir d'un forfait par type de repas et par ville, présenté comme une hypothèse.
- **Horaires rares** (93 % manquants). Le solveur (étape 7) devra traiter « horaires inconnus » sans
  inventer de contrainte : par défaut une plage raisonnable, avec un drapeau « à vérifier ».
- **Arabe** : 71 % de `nom_ar` manquant ; l'affichage arabe se replie sur `nom` (convention i18n).
- **Biais de cartographie** : les villes touristiques du nord sont mieux couvertes que Tozeur et
  Kairouan, et restaurants et cafés font 67 % du jeu. Le plafond limite l'effet sans l'annuler.
- **Doublons** (21 paires) non fusionnés à cette étape. La fusion est à faire à l'indexation
  (étape 5), sinon la recherche montrera deux fois le même lieu.

**Analyseur d'horaires** : il ne reconnaît pas `12:00 - 23:00` (espaces autour du tiret), les
saisons, `sunrise-sunset` ni les jours sans heures. Le texte brut reste disponible.

**Services externes**
- **Overpass est instable** (504 fréquents le 13/10). Une collecte complète prend environ 10 min, et
  une ville peut échouer : il faut relancer avec `--ville`.
- **Données figées** : les POI datent du 13/10/2026 et la météo expire après 6 h. Pour la démo, le
  repli sur le cache périmé fonctionne.

**Exploitation**
- **Les tests demandent `postgres-ai` démarré.** Ils échouent avec une erreur de connexion sinon,
  sans faux succès.
- `dev.ps1` démarre `postgres-ai` mais **pas encore** de processus `ai` (pas d'`app.main` avant
  l'étape 3).
- Le volume `voyara_pgdata_ai` n'est couvert par aucune sauvegarde, comme `pgdata` (dette existante).

## 7. À vérifier par moi

1. Démarrer Docker Desktop, puis lancer `docker compose up -d postgres postgres-ai` et
   `docker compose ps`. Les deux conteneurs doivent être `healthy`, sur les ports 5434 et 5435.
2. Créer `services/ai/.env` à partir de `services/ai/.env.example`, avec les mêmes
   `POSTGRES_USER/PASSWORD`, `JWT_SECRET_KEY` et `INTERNAL_API_KEY` que `services/catalog/.env`.
   Garder `POSTGRES_PORT=5435` et `POSTGRES_DB=voyara_ai`.
3. Lancer `.venv\Scripts\pip install -r requirements-dev.txt` (pour pandas, matplotlib et nbconvert).
4. Lancer `cd services\ai; ..\..\.venv\Scripts\python -m pytest`, qui doit afficher `55 passed`.
5. Lancer `..\..\.venv\Scripts\python scripts\collecter_pois.py`. Cela prend environ 10 min ; si une
   ville échoue, la relancer avec `--ville <nom>`. Le résumé doit finir par
   `Base voyara_ai : 1030 POI sur 8 villes` (le chiffre peut bouger si OSM a changé).
6. Relancer la même commande : chaque ville doit afficher `0 insérés`.
7. Lancer `..\..\.venv\Scripts\python scripts\rafraichir_meteo.py --ville Djerba` deux fois. Le
   second appel doit être instantané.
8. Depuis la racine, lancer
   `.venv\Scripts\jupyter nbconvert --to notebook --execute --inplace notebooks\01_eda_donnees.ipynb`.
   Ensuite, ouvrir le notebook dans VS Code et regarder les figures dans `docs/ia/figures/`.
9. Lancer `.\scripts\dev.ps1`, qui doit afficher « postgres-ai pret », puis `.\scripts\stop-dev.ps1`,
   qui doit afficher « postgres-ai arrete ». Le site doit continuer de fonctionner comme avant.

## 8. Étape suivante recommandée

**Étape 2 — Enrichissement sémantique du catalogue** (modules 2 et 3), sur une branche
`ia/etape-02` :
- attributs IA **dans catalog** : thèmes, public, `niveau_marche`, intérieur, moment idéal ;
- endpoint `/internal/activities/export` ;
- pré-étiquetage par LLM, puis validation par l'admin.

Prérequis :
- trancher le fournisseur LLM du pré-étiquetage : Claude API (clé dans `.env`) ou Ollama local,
  puisque la couche `LLMProvider` n'arrive qu'à l'étape 3 ;
- reprendre les constats de cette EDA : faire de « distance au restaurant le plus proche » un
  attribut utile, et faire de Kairouan, sans activité, une zone à enrichir ou à exclure de la démo.
