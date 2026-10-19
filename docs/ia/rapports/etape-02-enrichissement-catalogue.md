# Étape 02 — Enrichissement sémantique du catalogue

> Date : 2026-10-19 · Branche : `ia/etape-02` · Module(s) : 2 (recherche & collecte), 3 (recommandation)
> Source : [Guide_Moteur_IA_Voyara.html](../../../AgentIA_Voyara/Guide_Moteur_IA_Voyara.html) (étape 2)

## 1. Objectif

Donner à chaque activité des attributs que le moteur IA peut exploiter : thèmes, public visé,
effort de marche, intérieur ou extérieur, moment idéal de la journée. Sans `niveau_marche`, le
scénario « je préfère moins marcher » est impossible. La démarche est le *weak labelling + human
in the loop* : une machine propose (rapide), un humain valide dans l'admin (fiable). Les tags
vivent dans **catalog**, propriétaire des activités, et non dans `ai`.

**Critère de « fini » du guide** : 100 % des activités actives ont des tags validés ; l'export
interne est testé. → L'export est testé. **La validation humaine reste à faire : 0 / 117**
(voir §6 et §7). Les 117 activités ont une proposition prête à relire.

**Décision de l'étudiant (19/10/2026)** : pas de clé Anthropic pour rester gratuit. Le
pré-étiquetage passe par des **règles hors-ligne**, et le code reste prêt pour un LLM (Claude ou
Ollama local). Correction 422 → 401 de `require_internal_key` validée pour tous les services.

**Contrôle préalable des étapes 0 et 1** (demandé par l'étudiant après ses changements de
catégories) : conteneurs `postgres` (5434) et `postgres-ai` (5435) *healthy*, `55 passed` côté IA,
1 030 POI sur 8 villes, 56 lignes météo, `seed_catalogue_demo.py --verifier` → « Données valides :
107 activités », `seed_offres_voyage_demo.py --verifier` → « Données valides ». En base : 117
activités publiées sur 8 catégories (Culture 36, Mer 19, Désert 9, Aventure 17, Gastronomie 15,
Bien-être 9, Famille & loisirs 7, Golf 5). Rien à corriger.

## 2. Réalisé

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `services/catalog/app/tags_ia.py` | créé | Vocabulaire unique (`Literal` : 10 thèmes, 5 publics, 4 moments, niveaux 1-3), schémas `TagsIA` / `TagsIAValidation` (valeurs contrôlées, dédoublonnage, champs en trop refusés) |
| `services/catalog/app/models.py` | modifié | 8 colonnes IA sur `Activity`, 5 contraintes `CHECK` nommées, trigger `modifie_le` créé aussi par `create_all` (base neuve) |
| `services/catalog/scripts/add_tags_ia_columns.py` | créé | Migration idempotente d'une base existante, en une transaction : colonnes, contraintes lues dans le modèle, trigger |
| `services/catalog/app/routers.py` | modifié | `GET /internal/activities/export` : paginé (≤ 500), tri `(modifie_le, id)`, `modifie_depuis`, `statut`, `tags_valides` |
| `services/catalog/app/etiquetage_routes.py` | créé | Routes admin `/etiquetage` : liste filtrable, `PUT` (enregistrer / valider), statistiques (avancement, part des propositions corrigées) |
| `services/catalog/app/main.py` | modifié | Enregistre `etiquetage_router` |
| `gateway/app/main.py` | modifié | Préfixe `/api/v1/etiquetage` → catalog |
| `libs/common/voyara_common/internal.py` | modifié | Clé interne absente → **401** (au lieu de 422), clé fausse → 403 ; vaut pour tous les services |
| `services/catalog/scripts/pre_etiqueter.py` | créé | Pré-étiquetage → CSV, base ouverte en `READ ONLY` ; fournisseurs `regles` (défaut), `claude` (SDK `anthropic`), `ollama` (REST) |
| `services/catalog/scripts/importer_propositions.py` | créé | Charge le CSV dans les colonnes IA **sans valider**, garde la proposition dans `tags_proposes`, ne touche jamais une activité validée ; `--simulation` |
| `services/catalog/data/etiquetage/propositions_regles.csv` | créé | 117 propositions avec confiance et raisons (versionné pour la traçabilité) |
| `services/catalog/pytest.ini`, `tests/conftest.py` | créés | Première suite pytest de catalog : base réelle, une transaction annulée par test |
| `services/catalog/tests/test_export_interne.py` | créé | 401 / 403, champs, pagination sans doublon, `modifie_depuis`, trigger, filtres |
| `services/catalog/tests/test_tags_ia.py` | créé | Vocabulaire, 422 sur chaque valeur interdite, 401 sans jeton, statistiques, contraintes `CHECK` en base |
| `services/catalog/tests/test_pre_etiquetage.py` | créé | Règles (toponymes, marche, moment, public), Ollama simulé (valide / hors vocabulaire), lecture du CSV |
| `frontend/apps/admin/src/features/tags-ia/{api,hooks}.ts` | créés | Types, vocabulaire miroir, appels `/api/v1/etiquetage`, mutations avec messages traduits |
| `frontend/apps/admin/src/pages/TagsIaPage.tsx` | créé | Page « Tags IA » : avancement, filtres, cartes avec puces modifiables, marque « modifié », raisons, Valider / Enregistrer / Repasser à valider |
| `frontend/apps/admin/src/app/router.tsx`, `components/AdminLayout.tsx` | modifiés | Route `/tags-ia` et entrée de menu |
| `frontend/packages/i18n/src/locales/{fr,en,ar}/common.json` | modifiés | `admin.nav.tagsIa` + bloc `admin.tagsIa` (libellés de chaque valeur), aller-retour JSON vérifié identique avant écriture |
| `docs/mcd.md`, `docs/architecture.md`, `RUN.md`, `CLAUDE.md` | modifiés | Colonnes IA, routes et endpoint interne, commandes de migration / pré-étiquetage, commande de test catalog |
| `docs/plan.md`, `docs/ia/journal.md`, `docs/ia/README.md` | modifiés | Étape cochée (+ 2 sous-tâches ouvertes), ligne de journal, index des rapports |

**Données modifiées** : `voyara_catalog` (après `pg_dump`, §4) : 8 colonnes ajoutées, 117
propositions importées, `tags_valides` = faux partout.

## 3. Choix techniques

| Décision | Option retenue | Alternatives envisagées | Pourquoi écartées |
|---|---|---|---|
| Stockage de `themes` et `public` | **Colonnes JSONB** sur `activities` + `CHECK (themes <@ '[…]'::jsonb)` | Tables d'association `activity_themes` / `activity_publics` · `ARRAY` PostgreSQL | Catalog ne filtre jamais sur ces listes : c'est `ai` qui indexe dans sa propre base (étape 5). Une table d'association ajouterait deux jointures à l'export et deux tables à migrer, sans requête qui en profite. `ARRAY` aurait convenu aussi, mais JSONB est déjà sérialisé tel quel par l'API et l'opérateur `<@` suffit à contrôler le vocabulaire. |
| Contrôle des valeurs | **Deux niveaux** : `Literal` Pydantic (422 lisible) + 5 `CHECK` en base | API seule · enum PostgreSQL | L'API seule laisse passer un seed ou du SQL brut. Une enum PostgreSQL ne couvre pas le contenu d'un JSONB et se migre mal. Le `CHECK ck_activities_tags_complets` interdit aussi « validé mais incomplet ». |
| Source du vocabulaire | **`app/tags_ia.py`** lu par le modèle, l'API, les scripts et les tests ; miroir TypeScript dans l'admin | Listes recopiées partout | Une seule définition côté Python. Le miroir TS est inévitable (libellés i18n par valeur) et le backend refuse toute dérive (422). |
| Migration sans Alembic | **Script idempotent** `add_tags_ia_columns.py` (`ADD COLUMN IF NOT EXISTS`, contraintes lues dans le modèle, une transaction) + `pg_dump` avant | Introduire Alembic dans catalog · `DROP` + `create_all` | Alembic est reporté après la soutenance (`plan.md`) et exigerait une révision de base sur une table remplie. Recréer la table perdrait les données. Le script suit le modèle de `add_prestataire_columns.py`, déjà utilisé. Les valeurs par défaut sont neutres (listes vides, NULL, non validé). |
| Base neuve | **Trigger attaché à `after_create`** (`event.listen` + `DDL`) | Exiger le script de migration partout | Un nouveau poste obtient tout avec `create_all`. Vérifié dans un schéma temporaire (§4). |
| Date de modification | **`modifie_le` + trigger `BEFORE UPDATE`** | `onupdate` SQLAlchemy seul | `onupdate` ne voit ni les seeds en SQL, ni les scripts en SQL brut. Avec le trigger, même `UPDATE … SET modifie_le = '2000-01-01'` est corrigé (testé). |
| Export | **Pagination par décalage, tri `(modifie_le, id)`, `modifie_depuis` inclusif, tous statuts par défaut** | Pagination par curseur · seulement les publiées | `voyara_common.pagination` est le standard du projet. Le tri stable évite les doublons entre pages (testé). La borne inclusive ne perd jamais une ligne de même horodatage ; l'appelant dédoublonne par `id`. Exporter tous les statuts permet à `ai` d'apprendre les dépublications. |
| Clé interne absente | **401 dans `voyara_common`** (header facultatif côté FastAPI) | 401 seulement dans catalog | Le 422 venait de `Header(...)` dans le code partagé : le corriger là profite à tous les `/internal/*`. Non-régression : auth 5/5, IA 55/55, BFF admin en direct. |
| Pré-étiquetage | **Règles hors-ligne par défaut**, Claude et Ollama prêts derrière `--fournisseur` | Claude seul · Ollama seul | Choix de l'étudiant : gratuit. Les règles sont déterministes et chaque tag porte sa raison (« marche 3 ← randonnee »), ce que l'admin affiche. Elles servent aussi de **référence de comparaison** quand un LLM sera branché. |
| Indices des règles | **Mots-clés** sur titre + description normalisés (sans accents), **catégorie** (un thème d'office), **horaires réels des créneaux** pour le moment | Mots-clés seuls | La catégorie est une décision déjà prise par l'admin. Les créneaux sont un fait : des horaires tous après 16 h 30 indiquent le soir. Un créneau unique à 9 h ou 10 h, souvent hérité du seed, est ignoré. |
| Faux positifs des toponymes | **`\b` dans les motifs + soudure** de « Houmt Souk » et « Chott Meriem » | Les ignorer | Premier passage : « Hammamet » déclenchait *hammam* (thalasso, public adulte), « golfe » *golf*, « Houmt Souk » *shopping*. Un test en garde la trace ; il a aussi attrapé une première soudure ratée (`houmt_souk`, « _ » ne bloquant pas `\b`). |
| Appel Claude | **SDK officiel `anthropic`**, `messages.parse` + schéma Pydantic, `claude-opus-5-5`, effort `low`, refus détecté (`stop_reason == "refusal"`) | `httpx` brut | Recommandation du SDK pour Python ; sortie structurée validée deux fois (schéma imposé puis `TagsIA`). Import paresseux : rien à installer tant que ce fournisseur n'est pas utilisé. Pas de `fallbacks` serveur : appel volontairement simple, la couche hybride arrive à l'étape 3. |
| Appel Ollama | **REST `/api/chat`, `format` = schéma JSON, température 0** | Bibliothèque `ollama` | Aucune dépendance de plus ; contrainte de sortie par schéma ; testé avec une réponse simulée. |
| Aucune écriture par le pré-étiquetage | **`SET TRANSACTION READ ONLY`** + import séparé | Écrire directement en base | Consigne du guide. La lecture seule est garantie par PostgreSQL, pas par convention. L'import est explicite, idempotent, a un mode `--simulation` et ne touche jamais une validation humaine. |
| Mesure de qualité | **`tags_proposes`** (copie figée) + `GET /etiquetage/stats` : part des valeurs corrigées par champ | Pas de mesure | Sans annotation de référence, la seule mesure honnête est le taux de correction humaine, qui devient disponible au fil de la validation. |
| Route admin | **Préfixe dédié `/api/v1/etiquetage`** dans catalog | Sous `/activities/…` · dans le BFF admin | `/activities/{id}` (route publique) capterait `/activities/tags-ia`. Le BFF n'agrège rien ici : les données ont un seul propriétaire. |
| Écran | **Cartes** avec puces bascule (`aria-pressed`), marque « modifié » par champ, raisons repliables, filtre « À valider » par défaut | Tableau `DataTable` · formulaire séparé | Cinq champs multi-valeurs ne tiennent pas dans un tableau. On valide en un clic sans quitter la liste. |

## 4. Vérification

**Branche et sauvegarde** :

```text
PS> git switch -c ia/etape-02
Switched to a new branch 'ia/etape-02'
PS> docker exec voyara-postgres-1 pg_dump -U … -Fc -f /tmp/cat_avant_etape02.dump voyara_catalog ; docker cp …
pg_restore -l → 8 sections TABLE DATA · fichier 99 697 octets (dossier temporaire de la session)
```

Un premier `pg_dump > fichier` depuis PowerShell 5.1 a été jeté : cette redirection réencode les
flux binaires. La sauvegarde a été refaite dans le conteneur puis copiée avec `docker cp`.

**Migration (deux passages)** :

```text
PS> cd services\catalog; ..\..\.venv\Scripts\python scripts\add_tags_ia_columns.py
Terminé : 8 colonnes IA en place, 5 contrainte(s) ajoutée(s) sur 5, trigger modifie_le à jour. 117 activité(s) conservée(s).
PS> ..\..\.venv\Scripts\python scripts\add_tags_ia_columns.py
Terminé : 8 colonnes IA en place, 0 contrainte(s) ajoutée(s) sur 5, trigger modifie_le à jour. 117 activité(s) conservée(s).
psql → count 117 | validées 0 · ck_activities_{tags_complets,niveau_marche,moment_ideal,public,themes} · trg_activities_modifie_le
```

**Base neuve** : l'utilisateur du service n'a pas le droit `CREATEDB` (`permission denied to create
database`, rien n'a été créé). L'essai a donc été fait dans un schéma temporaire, à l'intérieur
d'une transaction annulée :

```text
contraintes : ['ck_activities_moment_ideal', 'ck_activities_niveau_marche', 'ck_activities_public', 'ck_activities_tags_complets', 'ck_activities_themes']
triggers    : ['trg_activities_modifie_le']
ligne par défaut (themes, public, tags_valides, modifie_le renseigné) : ([], [], False, True)
schéma supprimé par le rollback : True
```

**Pré-étiquetage et import** :

```text
PS> ..\..\.venv\Scripts\python scripts\pre_etiqueter.py
117 activité(s) lue(s) en lecture seule, 117 proposition(s), 0 erreur(s).
PS> ..\..\.venv\Scripts\python scripts\importer_propositions.py --simulation
SIMULATION — rien n'a été écrit. 117 ligne(s) lue(s) … : 117 importée(s), 0 inchangée(s), …
PS> ..\..\.venv\Scripts\python scripts\importer_propositions.py      (1er passage)
117 ligne(s) lue(s) dans propositions_regles.csv : 117 importée(s), 0 inchangée(s), 0 déjà validée(s) (non touchées), 0 absente(s) de la base, 0 en erreur dans le CSV, 0 invalide(s).
(après correction des toponymes et nouveau CSV) → 5 importée(s), 112 inchangée(s)
(relance)                                       → 0 importée(s), 117 inchangée(s)
```

Incident pendant le développement : un passage a produit `117 erreur(s)`
(`UnboundLocalError` sur une variable). Le `except Exception` prévu pour les erreurs réseau des LLM
masquait un bogue. Corrigé, et le fournisseur `regles` relève désormais toute exception au lieu de
l'écrire dans le CSV.

**Tests pytest** :

```text
PS> cd services\catalog; ..\..\.venv\Scripts\python -m pytest -q
FAILED tests/test_pre_etiquetage.py::test_regles_toponymes_ne_trompent_pas
  AssertionError: assert 'shopping' not in ['culture', 'histoire', 'shopping']
1 failed, 50 passed, 19 warnings in 3.52s
(correction : soudure « houmtsouk » sans « _ »)
PS> ..\..\.venv\Scripts\python -m pytest -q -p no:warnings
51 passed in 2.62s
PS> cd ..\auth; ..\..\.venv\Scripts\python -m pytest -q -p no:warnings
5 passed in 1.39s
PS> cd ..\ai; ..\..\.venv\Scripts\python -m pytest -q -p no:warnings
55 passed in 0.77s
```

Les 19 avertissements sont des dépréciations existantes (`on_event`, `httpx` dans `TestClient`,
`HTTP_422_UNPROCESSABLE_ENTITY`), pas liées à cette étape.

**Services en marche** (rechargés automatiquement par `dev.ps1`) :

```text
GET :8002/internal/activities/export?size=2   sans clé → 401 · clé fausse → 403 · bonne clé → 200 {"items":[{"id":2,…
GET :8000/internal/activities/export (gateway) → 404 (bloqué)
GET :8000/api/v1/etiquetage/stats sans jeton  → 401
JWT admin signé localement (create_access_token(1, 1)) :
  stats: total=117 publiees=117 validees=0 avec_proposition=117 sources={"regles":117}
  liste: total=117 premiers=2:culture|histoire, 3:nautique|aventure, 4:desert|aventure|culture
  PUT theme 'ski' → 422
  PUT brouillon (mêmes valeurs) → tags_valides=False themes=culture|histoire
JWT touriste (rôle 2) → 403
Non-régression BFF : /admin/activities total=117 · /admin/stats activités=117, séjours=27 · /admin/bookings total=5
```

**Front** :

```text
PS> cd frontend; npm run typecheck
> @voyara/client@0.0.0 typecheck > tsc --noEmit        (aucune erreur)
> @voyara/admin@0.0.0 typecheck  > tsc --noEmit        (aucune erreur)
PS> npm run test → Test Files 1 passed (1) · Tests 4 passed (4)
Audit des clés : 78 clés vérifiées x 3 langues, 0 manquante(s)
Vite :5174 → /admin/src/pages/TagsIaPage.tsx 200 (59 307 o) · /admin/tags-ia 200
```

**Non vérifié** : le rendu de la page dans un navigateur (mise en page, sens droite-à-gauche en
arabe, clics). Aucun test vitest ne couvre l'admin.

## 5. Métriques

**Jeu de données** : `voyara_catalog` au 19/10/2026, 117 activités publiées (107 du seed de
l'étape 1 + 8 d'origine + 2 activités de test), 8 catégories ; horaires des créneaux en base.
Fournisseur `regles-v1`. Fichier : `services/catalog/data/etiquetage/propositions_regles.csv`.

| Mesure | Valeur |
|---|---|
| Couverture | 117 / 117 propositions, 0 erreur |
| Thèmes proposés | culture 51 · aventure 32 · nature 28 · histoire 27 · nautique 21 · gastronomie 18 · plage 17 · détente 16 · désert 14 · shopping 11 |
| Public | couple 110 · solo 109 · famille 103 · groupe 25 · enfants 20 |
| Niveau de marche | 1 : 57 · 2 : 57 · 3 : 3 |
| Intérieur | oui 28 · non 89 |
| Moment idéal | indifférent 100 · soir 9 · matin 8 |
| Confiance (nombre d'indices) | haute 54 · moyenne 51 · faible 12 |
| Validées par un humain | **0 / 117** |

**Qualité : non mesurée.** Il n'existe pas d'annotation de référence. La mesure prévue est le
taux de correction humaine par champ (`GET /etiquetage/stats`), disponible au fur et à mesure de
la validation. Une relecture rapide et **non systématique** du CSV final a relevé au moins ces
erreurs, à corriger pendant la validation :
- n° 32 (dromadaire), marche 2 : « accompagnateur à pied » ;
- n° 114 et 117 (golf), marche 1 : « voiturette » ;
- n° 44 (médina de Tunis), « intérieur » : palais et musée l'emportent sur les ruelles ;
- n° 96 (pain cuit dans le sable), « intérieur » : le mot « atelier » ;
- n° 16 (musée), thème « shopping » : le mot « bijoux » ;
- n° 101 (hammam dans la médina), marche 2.

## 6. Limites, dette technique, risques

- **Critère de « fini » non atteint : 0 / 117 validées.** La validation est un travail humain, que
  je ne pouvais pas faire à la place de l'étudiant (environ 117 cartes, la plupart en un clic).
- **Deux activités de test publiées** : n° 10 « claude » (description « sxdxgkgxke ») et n° 97
  « Chien a verdure » (durée 999). Elles ont reçu des tags par défaut, avec une confiance
  « faible ». Il faut les supprimer ou les dépublier avant la démo ; je n'y ai pas touché.
- **Règles fragiles par nature** : un mot-clé peut tromper (voir §5). Le moment idéal est
  « indifférent » pour 100 activités sur 117, faute d'indice. Un LLM fera probablement mieux
  sur ce champ.
- **Monde hors vocabulaire** : 10 thèmes seulement, sans « sport » ni « bien-être ». Le golf est
  rangé en « détente » faute de mieux. Étendre le vocabulaire = `tags_ia.py` + migration des
  `CHECK` + i18n.
- **Suppressions invisibles pour `modifie_depuis`** : une activité supprimée disparaît de l'export.
  Le service `ai` devra faire une resynchronisation complète de temps en temps (étape 5).
- **Modifier une activité ne dévalide pas ses tags** : changer la description dans l'admin laisse
  `tags_valides` à vrai. Choix assumé (la plupart des modifications ne changent pas les tags), à
  revoir si les prestataires modifient beaucoup.
- **Migration à appliquer sur chaque poste** créé avant cette étape, **avant** de redémarrer
  catalog. Sinon, le service lit des colonnes absentes et renvoie des erreurs 500.
- **Services démarrés avant le changement de `libs/common`** : ils gardent l'ancien comportement
  (422) tant qu'ils ne sont pas redémarrés. `--reload` ne surveille pas le paquet installé en mode
  éditable. Catalog s'est rechargé (401 vérifié) car ses propres fichiers ont changé.
- **Vocabulaire dupliqué en TypeScript** : une dérive serait refusée par le backend (422), mais pas
  détectée à la compilation.
- **Messages « toast » existants de l'admin en français en dur** (`features/catalog/hooks.ts`) :
  dette antérieure, non traitée ; la nouvelle page passe par l'i18n.
- **Raisons du pré-étiquetage en français** dans toutes les langues (texte produit par le script).
- **Sauvegarde dans le dossier temporaire de la session** : non garantie dans le temps.
- **Fournisseurs Claude et Ollama non exercés pour de vrai** : Ollama est testé avec une réponse
  simulée, Claude n'a pas de test (pas de clé, choix de gratuité).

## 7. À vérifier par moi

1. `git branch --show-current` → `ia/etape-02`.
2. **Redémarrer le backend** pour que tous les services prennent la correction de
   `libs/common` : `.\scripts\stop-dev.ps1` puis `.\scripts\dev.ps1`. Ensuite
   `http://localhost:8003/internal/bookings/count-by-activity?ids=1` dans le navigateur doit
   renvoyer **401** (et non 422).
3. Admin <http://localhost:5174/admin> → menu **Tags IA** :
   - la barre affiche « 0 / 117 activités publiées validées » ;
   - le filtre est sur « À valider ».
4. Ouvrir « Pourquoi ces tags ? » sur une carte : la source (`regles-v1`), la confiance et les
   raisons s'affichent.
5. Cliquer **Modifier** sur la n° 32 (dromadaire) :
   - passer la marche à 1, puis **Valider** ;
   - le badge passe à « Validée », et « modifié » apparaît à côté de « Marche » ;
   - la barre affiche une ligne « Corrections humaines sur 1 activités validées ».
6. Passer l'admin en **anglais** puis en **arabe** : les libellés des thèmes, publics, niveaux et
   moments sont traduits, et la page s'affiche de droite à gauche en arabe.
7. Valider les 117 activités, en corrigeant d'abord les cas du §5. Supprimer ou dépublier les
   n° 10 et 97.
8. Contrôle final en PowerShell :
   ```powershell
   cd services\catalog
   ..\..\.venv\Scripts\python -m pytest -q
   ```
   Puis, dans l'admin connecté, ouvrir `http://localhost:8000/api/v1/etiquetage/stats` :
   `publiees_validees` doit être égal à `publiees`, et `corrections` donne les chiffres de qualité
   des règles pour le rapport.
9. (Plus tard, facultatif) Essayer un LLM local gratuit :
   ```powershell
   ollama pull qwen2.5:7b
   cd services\catalog
   ..\..\.venv\Scripts\python scripts\pre_etiqueter.py --fournisseur ollama
   ```
   Comparer ensuite `propositions_ollama.csv` à `propositions_regles.csv`. N'importer que les
   activités non validées : c'est déjà la règle de l'import.

## 8. Étape suivante recommandée

**Étape 3 — Service `ai` et couche LLM hybride**, sur `ia/etape-03` :
- scaffold FastAPI :8008 sur les modèles déjà créés ;
- route gateway `/api/ai` ;
- `LLMProvider` Claude / Ollama avec bascule ;
- table `llm_appels`.

Prérequis et recommandations :
- terminer d'abord la **validation humaine** (le critère de l'étape 2) et supprimer les 2 activités
  de test : les étapes 5 à 7 liront `tags_valides = true` ;
- sans clé Anthropic, prévoir **Ollama** comme fournisseur par défaut de l'étape 3 (gratuit,
  hors-ligne). `pre_etiqueter.py --fournisseur ollama` pourra alors servir de premier banc d'essai
  et se brancher sur `LLMProvider` ;
- à garder pour l'étape 7 : profils solo / couple / famille des séjours, et export interne des
  offres (séjours, transferts, vols) pour le budget.
