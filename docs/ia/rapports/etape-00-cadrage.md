# Étape 00 — Cadrage, conventions et architecture cible

> Date : 2026-10-11 · Branche : `ia/etape-00` · Module(s) : transverse ·
> Source : [Guide_Moteur_IA_Voyara.html](../../../AgentIA_Voyara/Guide_Moteur_IA_Voyara.html) (étape 0) +
> [PresProjCom.pdf](../../../AgentIA_Voyara/PresProjCom.pdf)

## 1. Objectif

Fixer les règles avant d'écrire la moindre ligne d'IA :
- où vit le moteur IA ;
- comment Claude Code doit travailler sur le dépôt ;
- comment chaque étape est tracée.

**Critère de « fini » (guide)** : CLAUDE.md existe, l'ADR est rédigé, et `docs/plan.md` liste les étapes avec leur effort et leur priorité. Aucun code applicatif à cette étape.

## 2. Réalisé

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `CLAUDE.md` | créé | Règles permanentes pour chaque session : architecture en bref (ports, bases, service `ai` prévu), conventions, commandes PowerShell, méthode IA, source des étapes, renvoi vers `frontend/apps/client/CLAUDE.md`, règle « rapport obligatoire ». |
| `docs/ia/README.md` | créé | Vision du moteur, principe anti-hallucination, schéma des 6 modules ↔ étapes, 3 scénarios de démo, collecte web OSM + Open-Meteo, perspectives, modèle de rapport en 8 sections, index des rapports. |
| `docs/ia/journal.md` | créé | Historique : une ligne par étape (date, étape, résumé), avec la ligne de l'étape 0. |
| `docs/ia/rapports/etape-00-cadrage.md` | créé | Ce rapport (crée aussi le dossier `rapports/`). |
| `docs/architecture.md` | modifié | **ADR-007** (service `ai`, `voyara_ai` + pgvector, `/internal/*`, `/api/ai`, LLM hybride) avec le statut « acceptée, non appliquée ». Intro du §13 précisée, lien dans le sommaire, point 5 « Phase Moteur IA » dans la feuille de route §14, et « recommandations ML » retiré des perspectives. |
| `docs/plan.md` | modifié | Nouvelle **phase « Moteur IA »** : étapes 0 à 13 avec effort et priorité, étape 0 cochée, en-tête « date à confirmer » et rappel que J1–J4 ne concernent pas cette phase. La Phase 10 est marquée remplacée. Les lignes IA/ML sont retirées des reports (avec la raison) et les perspectives Prestataires / mobile / vocal ajoutées. Ligne IA de la stack et livrable « recommandations par règles » mis à jour. |

Aucun fichier de code (`services/`, `gateway/`, `libs/`, `frontend/`, `scripts/`, `infra/`, `docker-compose.yml`) n'a été modifié (voir §4).

## 3. Choix techniques

| Décision | Option retenue | Alternatives envisagées | Pourquoi écartées |
|---|---|---|---|
| Où vit le moteur IA | **Nouveau microservice `ai`** (:8008) | IA dans catalog (ancienne Phase 10) | Couplerait un domaine critique (places, saga) à un composant lent, coûteux et expérimental. Catalog devrait aussi lire review et booking et stocker des conversations, ce qui brise le découpage par domaine. |
| Stockage des vecteurs | **pgvector dans `voyara_ai`** | Qdrant / Weaviate / Pinecone | Une technologie et une synchronisation de plus pour quelques milliers de documents. pgvector combine filtres SQL (ville, prix, rayon) et similarité dans une seule requête. |
| Fournisseur LLM | **Hybride : Claude API par défaut, Ollama en secours** (`auto` = bascule) | Claude seul · Ollama seul | Claude seul : pas de démo hors-ligne, coût à l'usage. Ollama seul : qualité plus faible (arabe, darija, tool use). Dans les deux cas, aucune comparaison scientifique entre modèles. |
| Accès aux données métier | **HTTP synchrone `/internal/*` + `ServiceClient`**, endpoints manquants ajoutés dans le service propriétaire | Lecture directe des autres bases · réplication par événements (broker) | Lecture directe : viole ADR-002 (database-per-service). Broker : infrastructure en plus, injustifiée à cette échelle (ADR-005 a déjà écarté ce choix). |
| Statut de l'ADR | **« Acceptée, non encore appliquée »** + intro du §13 corrigée | Écrire l'ADR comme les autres (« déjà appliquée ») | Le §13 affirmait que toutes les décisions sont dans le code, ce qui aurait été faux pour ADR-007. |
| Sort de la Phase 10 | **Gardée pour l'historique**, marquée « remplacée par la phase Moteur IA (ADR-007) » | La supprimer · la réécrire | Supprimer fait perdre la trace du recadrage, utile pour le rapport. Réécrire mélangerait deux cadrages contradictoires. *(Décision validée par l'étudiant.)* |
| Lignes IA/ML de « Reporté après la soutenance » | **Retirées**, avec une phrase d'explication | Les laisser | Elles contredisaient la nouvelle phase : le projet est désormais aussi un projet IA & Cognition 5DS. |
| Calendrier de la phase | **Pas de dates**, « Date de présentation IA : à confirmer », J1–J4 réservés à la plateforme | Caler sur les jalons J1–J4 | Les jalons visaient le 21/09/2026, date déjà passée. La date de la présentation IA est inconnue, et une date inventée induirait en erreur. *(Décision validée.)* |
| Échelle d'effort | **Celle de plan.md** (S ≤ ½ j · M 1–2 j · L ≥ 3 j), avec les durées du guide | Reprendre les durées du guide en jours | Garder une seule échelle dans plan.md. Pour une étape à « 2–3 j », j'ai retenu L par prudence (étapes 4, 6). |
| Priorités | **must 0–9 et 13**, **should 10 et 12** ; **11 scindée** : version réduite (NLU, recherche, itinéraire chiffrés) en must, le reste en should | 11 entièrement en should (guide) | Sans chiffres, il n'y a pas de démarche data science : c'est l'avertissement du guide. *(Ajustement validé.)* |
| Web scraper de la présentation | **« Collecte automatisée de données web » OSM/Overpass + Open-Meteo** | Scraping TripAdvisor / Google | Le scraping viole les CGU et les licences, et casse à chaque changement de page. Les API ouvertes (ODbL, sans clé) sont légales et reproductibles. Le module 2 reste couvert. *(Décision validée.)* |
| Interface Prestataires, mobile, vocal | **Perspectives** (README IA + plan.md) | Les planifier | Absentes des 13 étapes du guide, et hors du MVP de la présentation (diapo 15). |
| Emplacement des règles de travail | **CLAUDE.md racine** qui **renvoie** vers `frontend/apps/client/CLAUDE.md` | Fusionner les deux | Le fichier du client est géré par `next dev` (bloc régénéré automatiquement). Le fusionner créerait des conflits. |
| Traçabilité Git | **Branche `ia/etape-00`** créée avant toute écriture | Travailler sur `main` | Recommandation du guide : une branche par étape, facile à relire et à annuler. *(Décision validée.)* |

## 4. Vérification

Il n'y a pas de tests automatisés à lancer : l'étape ne produit que de la documentation. Voici les contrôles réellement exécutés (PowerShell, depuis la racine).

**Branche créée avant écriture**

```text
PS> git switch -c ia/etape-00; git status --short; git branch --show-current
Switched to a new branch 'ia/etape-00'
?? AgentIA_Voyara/Guide_Moteur_IA_Voyara.html
?? AgentIA_Voyara/Guide_Moteur_IA_Voyara.pdf
?? RUN.md
ia/etape-00
```

**Livrables, ADR et phase** (avant création de ce rapport, d'où `rapports False`)

```text
== Livrables
CLAUDE.md              True
docs\ia\README.md      True
docs\ia\journal.md     True
docs\ia\rapports       False
== ADR-007
L526: ### ADR-007 — Microservice `ai` dédié, pgvector et LLM hybride
== Phase Moteur IA
L302: ## 🤖 Phase 10 — Fonctionnalités intelligentes — ~~recadrée `nice`~~ → **remplacée par la phase Moteur IA (ADR-007)**
L391: ## 🧠 Phase Moteur IA — projet IA & Cognition 5DS
== Etapes (lignes '**N — ')
total: 14
x 0
  1 … 13          (étapes 1 à 13 non cochées)
== ML retiré des perspectives
L316: - [ ]  ~~ML scikit-learn (filtrage collaboratif)~~ → **reporté** …   ← ligne historique de la Phase 10, conservée volontairement
L455: > *Retiré le 11/10/2026* : les lignes IA/ML (« ML scikit-learn — filtrage collaboratif ») ne sont plus
```

**Aucun fichier de code modifié**

```text
== git status
 M docs/architecture.md
 M docs/plan.md
?? AgentIA_Voyara/Guide_Moteur_IA_Voyara.html
?? AgentIA_Voyara/Guide_Moteur_IA_Voyara.pdf
?? CLAUDE.md
?? RUN.md
?? docs/ia/
== diff stat
 docs/architecture.md | 68 ++++++++++++++++++++++++++++++++++++++++++++++++----
 docs/plan.md         | 54 +++++++++++++++++++++++++++++++++++++----
 2 files changed, 113 insertions(+), 9 deletions(-)
```

`RUN.md` (guide d'installation écrit avant cette étape) et les deux fichiers du guide IA étaient déjà non suivis au départ. Ils ne font pas partie des livrables de l'étape 0 (voir §7 pour le commit).

**Liens et ancres Markdown** : un script de contrôle (hors dépôt) résout chaque lien relatif et calcule le slug des ancres à la façon de GitHub.

1er passage, avant ce rapport :

```text
KO  CLAUDE.md -> docs/ia/README.md#modèle-de-rapport-détape (ancre introuvable)
KO  docs/ia/README.md -> rapports/etape-00-cadrage.md (fichier introuvable)
KO  docs/ia/journal.md -> rapports/ (fichier introuvable)
KO  docs/plan.md -> ia/rapports/etape-00-cadrage.md (fichier introuvable)
66 liens relatifs vérifiés, 4 en erreur
```

- La 1re erreur était réelle : le titre est numéroté (« 6. Modèle de rapport d'étape »). Je l'ai corrigée en `#6-modèle-de-rapport-détape`.
- Les 3 autres pointaient vers ce rapport, qui n'existait pas encore.

Résultat du 2e passage après création du rapport : voir la section *Contrôle final* en fin de document.

## 5. Métriques

Non applicable : aucune donnée ni aucun modèle à cette étape. À titre indicatif : 14 étapes listées dans plan.md (0 à 13), dont 11 en must (0–9, 13), 1 scindée en must/should (11) et 2 en should (10, 12).

## 6. Limites, dette technique, risques

- **ADR-007 n'est pas appliquée** : le service `ai`, la base `voyara_ai`, la route `/api/ai` et l'image pgvector n'existent pas encore. `CLAUDE.md` et `architecture.md` le disent explicitement.
- **Changement d'image Postgres (étape 3)** : passer de `postgres:16-alpine` à `pgvector/pgvector:pg16` (image Debian) avec le volume `pgdata` existant est à tester. Même version majeure, donc les fichiers de données doivent être compatibles. Une différence de collation (libc musl vs glibc) peut toutefois exiger un `REINDEX` des index texte. Faire un `pg_dump` avant.
- **Sections non mises à jour** : `architecture.md` §1 à §11 (« 7 microservices », diagramme, table de routage) et `mcd.md` ne mentionnent pas encore `ai`. C'est voulu : elles décrivent l'architecture *en place* et seront mises à jour quand le service existera (étapes 1 et 3).
- **Efforts estimés** à partir des durées indicatives du guide, sans historique de vélocité sur ce type de tâches. Les étapes L (4 à 9) cumulent au moins 18 jours : le MVP est ambitieux tant que la date de présentation n'est pas connue.
- **Dépendance aux données** : le catalogue actuel ne compte que 8 activités. Recherche, recommandation et évaluation dépendront fortement des POI collectés à l'étape 1 et des tags de l'étape 2.
- **Coûts et secrets** : `ANTHROPIC_API_KEY` sera un nouveau secret. Il doit rester dans `.env` (déjà ignoré par Git) et ne jamais apparaître dans un rapport.

## 7. À vérifier par moi

1. `git branch --show-current` → doit afficher `ia/etape-00`.
2. Ouvre `CLAUDE.md` : vérifie le tableau des ports, la ligne « `services/ai` *(prévu — ADR-007)* », le renvoi vers `frontend/apps/client/CLAUDE.md` et la section 5 « Règle de clôture ».
3. Ouvre `docs/architecture.md`, cherche « ADR-007 ». Relis le contexte, la décision, les 3 alternatives et les conséquences, et vérifie le statut « non encore appliquée ».
4. Ouvre `docs/plan.md`, cherche « Phase Moteur IA ». Contrôle :
   - l'en-tête « Date de présentation IA : à confirmer » ;
   - les 14 lignes (0 cochée) ;
   - l'étape 11 scindée en must/should ;
   - la Phase 10 marquée « remplacée » ;
   - la note « Retiré le 11/10/2026 » en bas.
5. Ouvre `docs/ia/README.md` dans l'aperçu Markdown de VS Code (Ctrl+Shift+V) : le schéma ASCII doit rester aligné, et les liens vers le guide, le PDF et l'ADR doivent s'ouvrir.
6. Décide quoi faire de `RUN.md` et des deux fichiers du guide (`Guide_Moteur_IA_Voyara.html/.pdf`) non suivis. Je recommande de committer le guide avec cette étape, puisque CLAUDE.md le cite comme source. `RUN.md` peut partir dans un commit séparé.
7. Commit (voir le message proposé dans le chat), puis ouvre une **nouvelle session** pour l'étape 1.

## 8. Étape suivante recommandée

**Étape 1 — Données : points d'intérêt et météo** (module 2), sur la branche `ia/etape-01` :
- table `pois` ;
- script `collecter_pois.py` (Overpass, 8 villes, idempotent) ;
- client Open-Meteo avec cache 6 h ;
- notebook d'EDA ;
- tests du mapping OSM et du cache.

Prérequis :
- Docker démarré (base `voyara_ai` à ajouter à `infra/postgres/init.sql` et à `scripts/create_databases.py`) ;
- accès Internet pour Overpass et Open-Meteo ;
- Jupyter dans le venv pour le notebook.

---

### Contrôle final (après création de ce rapport)

```text
PS> python -I verifier_liens.py . CLAUDE.md docs/ia/README.md docs/ia/journal.md docs/ia/rapports/etape-00-cadrage.md docs/architecture.md docs/plan.md
68 liens relatifs vérifiés, 0 en erreur
PS> Test-Path docs\ia\rapports
True
PS> git status --short
 M docs/architecture.md
 M docs/plan.md
?? AgentIA_Voyara/Guide_Moteur_IA_Voyara.html
?? AgentIA_Voyara/Guide_Moteur_IA_Voyara.pdf
?? CLAUDE.md
?? RUN.md
?? docs/ia/
```
