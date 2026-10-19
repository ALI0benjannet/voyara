# Moteur IA de Voyara

> Projet IA & Cognition — 5DS Data Science (ESPRIM) · équipe TravelMinds.
> Sources : [présentation](../../AgentIA_Voyara/PresProjCom.pdf) ·
> [guide de réalisation](../../AgentIA_Voyara/Guide_Moteur_IA_Voyara.html) ·
> décision d'architecture : [ADR-007](../architecture.md#adr-007--microservice-ai-dédié-pgvector-et-llm-hybride) ·
> avancement : [plan.md — Phase Moteur IA](../plan.md#-phase-moteur-ia--projet-ia--cognition-5ds) ·
> historique : [journal.md](journal.md)

## 1. Vision

**Problématique** : comment utiliser l'IA pour transformer une demande touristique exprimée
naturellement en un itinéraire **personnalisé, cohérent et adaptable** ?

> « Je vais à Djerba pendant 3 jours. J'ai 300 DT. Je voyage avec ma famille.
> Je veux découvrir la culture et profiter de la plage. »

Aujourd'hui le voyageur cherche les activités, compare les prix, vérifie les distances, organise
les horaires et construit lui-même son itinéraire. Le moteur IA ajoute **une couche d'intelligence**
au-dessus de la plateforme de réservation existante : il ne la remplace pas, il transforme une
intention de voyage en plan d'action réservable.

**Principe directeur — éviter les hallucinations par construction :**

| Rôle | Qui le tient |
|---|---|
| Comprendre la demande, expliquer les choix | **LLM** (Claude API, Ollama en secours) |
| Faits (prix, horaires, places, coordonnées) | **Bases de données** (catalog, review, booking, `voyara_ai`) |
| Classement des expériences | **Score mesurable** et explicable (module 3) |
| Planning jour par jour, budget | **Solveur d'optimisation** (OR-Tools CP-SAT, glouton en secours) |

L'agent **propose** ; il ne réserve et ne paie jamais seul (le bouton « Réserver » renvoie vers le
tunnel existant booking + Stripe).

## 2. Les 6 modules

```text
                     « 3 jours à Djerba, 300 DT, famille, culture + plage »
                                            │
                                            ▼
 ┌────────────────────────────────────────────────────────────────────────────────┐
 │ MODULE 6 — AGENT INTELLIGENT (étape 8)                                         │
 │ boucle LLM à outils · état de conversation persistant · planifier / modifier / │
 │ justifier · garde-fous (max itérations, budget tokens, aucune action payante)  │
 │                                                                                │
 │  ┌──────────────┐  ┌──────────────────┐  ┌──────────────┐  ┌────────────────┐  │
 │  │ MODULE 1     │  │ MODULE 2         │  │ MODULE 3     │  │ MODULES 4 & 5  │  │
 │  │ Compréhension│─▶│ Recherche &      │─▶│ Recommandation─▶│ Itinéraire +   │  │
 │  │ (NLU)        │  │ collecte (RAG)   │  │ Top-5        │  │ budget/optim.  │  │
 │  │ étape 4      │  │ étapes 1, 2, 5   │  │ étape 6      │  │ étape 7        │  │
 │  │ texte →      │  │ BM25 + embeddings│  │ score pondéré│  │ CP-SAT sous    │  │
 │  │ DemandeVoyage│  │ fusion RRF,      │  │ explicable + │  │ contraintes :  │  │
 │  │ + question si│  │ filtres durs     │  │ diversité MMR│  │ budget, temps, │  │
 │  │ info manquante│ │ (ville, rayon,   │  │ + raisons    │  │ distances,     │  │
 │  └──────────────┘  │ prix)            │  └──────────────┘  │ horaires, météo│  │
 │                    └────────┬─────────┘                    └────────────────┘  │
 └─────────────────────────────┼──────────────────────────────────────────────────┘
                               │ lit (jamais de jointure SQL)
        ┌──────────────────────┼─────────────────────────────┬─────────────────────┐
        ▼                      ▼                             ▼                     ▼
  catalog /internal/*    review /internal/*          booking /internal/*    collecte web
  activités, tags IA,    notes, favoris              historique,            automatisée :
  hébergements, créneaux                             popularité             OSM (POI) +
                                                                            Open-Meteo
                                            │
                                            ▼
          Itinéraire jour par jour (matin · midi · après-midi · soir) + ventilation du budget
          (hébergement / restaurants / activités / déplacements) + carte + bouton Réserver
```

| Module (présentation) | Ce qu'il fait | Étapes du guide |
|---|---|---|
| 1 · Compréhension du besoin | Extrait destination, durée, budget, type de voyage, préférences, contraintes ; pose une question au lieu d'inventer | 4 |
| 2 · Recherche & collecte | Collecte POI + météo, enrichit le catalogue, recherche hybride sémantique + lexicale | 1, 2, 5 |
| 3 · Recommandation personnalisée | Passe de ~50 candidats aux 5 meilleurs, avec raisons lisibles | 6 |
| 4 · Construction de l'itinéraire | Planning cohérent jour par jour | 7 |
| 5 · Budget & optimisation | Respect du budget total, du temps, des distances, des horaires | 7 |
| 6 · Agent intelligent / adaptation | Orchestre les modules, modifie et justifie en conversation | 8 |

**Collecte de données web.** La présentation mentionne un « web scraper » pour les données
touristiques. Il est remplacé par une **collecte automatisée de données web** à partir de sources
ouvertes : **OpenStreetMap** (API Overpass, licence ODbL — restaurants, plages, musées, monuments,
souks) et **Open-Meteo** (météo, sans clé). Raison : le scraping de sites commerciaux
(TripAdvisor, Google) viole leurs CGU et leurs licences, et casse à chaque changement de page ;
les API ouvertes sont légales, reproductibles et défendables devant un jury. Le module 2 de la
présentation reste donc entièrement couvert.

## 3. Les 3 scénarios de démonstration

| # | Le voyageur dit | Le moteur fait |
|---|---|---|
| 1 · Planifier | « 3 jours à Djerba, 300 DT, famille, culture + plage » | comprend → recherche → vérifie → construit l'itinéraire et le budget |
| 2 · Modifier | « Je préfère moins marcher » | baisse `niveau_marche_max`, remplace les activités concernées, recalcule distances et planning, liste les changements |
| 3 · Justifier | « Pourquoi le village de Guellala ? » | répond à partir des composantes réelles du score (budget respecté, distance à l'activité précédente, thème) |

## 4. Périmètre et perspectives

**MVP (présentation, diapo 15)** : saisie de la demande, recherche d'activités, recommandations,
itinéraire personnalisé, gestion du budget, modification de l'itinéraire — couverts par les
étapes 1 à 9.

**Perspectives (hors périmètre de la phase IA)** : interface Prestataires (gestion des offres par
les partenaires), application mobile, interaction vocale, extension multi-destinations, agent plus
autonome, apprentissage des préférences. La réservation et le paiement existent déjà dans la
plateforme : l'IA y renvoie sans les automatiser.

## 5. Arborescence de travail

```text
docs/ia/
├── README.md          ← ce fichier (vision, modules, modèle de rapport)
├── journal.md         ← une ligne par étape terminée
├── rapports/          ← un rapport par étape : etape-NN-<sujet>.md
├── resultats/         ← (à partir de l'étape 4) métriques générées, CSV + Markdown
└── figures/           ← (à partir de l'étape 1) figures exportées pour le rapport de PFE
```

## 6. Modèle de rapport d'étape

Chaque étape se termine par `docs/ia/rapports/etape-NN-<sujet>.md`, avec exactement ces sections :

```markdown
# Étape NN — <titre>

> Date : AAAA-MM-JJ · Branche : ia/etape-NN · Module(s) : …

## 1. Objectif
Ce que l'étape devait accomplir (et son critère de « fini » dans le guide).

## 2. Réalisé
| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|

## 3. Choix techniques
Pour CHAQUE décision : option retenue · alternatives envisagées · pourquoi elles sont écartées.

## 4. Vérification
Commandes PowerShell exécutées et **sortie réelle** (extraits). Jamais « les tests passent » sans
la sortie ; tout échec est signalé tel quel.

## 5. Métriques
Chiffres obtenus + jeu de données utilisé (taille, provenance, version). « Non applicable » sinon.

## 6. Limites, dette technique, risques
Cas non gérés, raccourcis assumés, risques pour la démo.

## 7. À vérifier par moi
Pas à pas manuel, reproductible, pour l'étudiant.

## 8. Étape suivante recommandée
Étape suivante du guide et prérequis éventuels.
```

Règles : aucune clé API dans un rapport ; les chiffres d'un rapport doivent provenir de commandes
réellement exécutées ; les rapports sont la matière première du chapitre « Moteur IA » du rapport
de PFE (étape 13).

## 7. Index des rapports

| Étape | Rapport |
|---|---|
| 0 · Cadrage | [etape-00-cadrage.md](rapports/etape-00-cadrage.md) |
| 1 · Seed du catalogue (sous-tâche) | [etape-01-seed-catalogue.md](rapports/etape-01-seed-catalogue.md) |
| 1 · Photos du catalogue (sous-tâche) | [etape-01-photos-catalogue.md](rapports/etape-01-photos-catalogue.md) |
| 1 · POI, météo et EDA (clôture de l'étape) | [etape-01-poi-meteo.md](rapports/etape-01-poi-meteo.md) |
