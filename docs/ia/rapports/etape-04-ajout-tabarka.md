# Étape 04 — Ajout de la ville Tabarka (sous-tâche)

> Date : 2026-11-09 · Branche : ia/etape-04 · Module(s) : 1 (NLU, jeu d'évaluation) et 2 (POI, météo)

## 1. Objectif

Faire de **Tabarka** une destination reconnue par le moteur IA. Jusqu'ici, c'était l'exemple type
de destination « hors catalogue » (README du jeu d'évaluation, test de validation, demande G-023).
Une fois l'ajout fait : Tabarka figure dans le référentiel des villes du moteur IA (collecte des POI
et météo), dans le vocabulaire du jeu NLU, et les demandes qui la citent sont réannotées.

## 2. Réalisé

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `services/ai/app/villes.py` | modifié | `Ville("Tabarka", 36.9544, 8.7580, 6000)` : centre OSM, le rayon couvre le port, le fort génois et l'aéroport TBJ |
| `services/ai/app/collecte.py` | modifié | Docstring : Tabarka retirée des exemples d'aéroports ignorés (remplacée par Gabès) |
| `services/ai/scripts/collecter_pois.py`, `rafraichir_meteo.py`, `RUN.md` | modifiés | « 8 villes » → « 9 villes » |
| `services/ai/scripts/jeu_nlu.py` | modifié | `VILLES_CATALOGUE` + « Tabarka » (validation, génération et import des relectures) |
| `services/ai/data/eval/README.md` | modifié | §2 : Tabarka ajoutée aux villes du catalogue ; §3 : exemple hors catalogue « Tabarka » → « Bizerte » |
| `services/ai/tests/test_relecture_jeu_nlu.py` | modifié | Exemple de destination invalide : « Tabarka » → « Bizerte » |
| `services/ai/data/eval/nlu_dev.jsonl` | modifié | G-023 : `destination` null → « Tabarka », `champs_manquants` [] (était `["destination"]`), tag `hors_catalogue` retiré ; statut inchangé (`a_relire`) |

## 3. Choix techniques

- **Rayon de 6 km** : retenu pour couvrir la ville, le port de plaisance et l'aéroport
  Tabarka–Aïn Draham (TBJ, à environ 5 km à l'est). Avec 3 ou 4 km, on raterait l'aéroport. Au-delà,
  on ramasserait les POI d'Aïn Draham, qui ne fait pas partie du catalogue. Comme TBJ est à moins
  de 60 km d'une ville couverte, `selectionner_aeroports` le rattache désormais à Tabarka au lieu
  de l'ignorer.
- **Aéroport TBJ absent du référentiel catalog** (`app/lieux.py`) : je l'avais ajouté, puis retiré.
  Le test `test_referentiel_couvre_tous_les_aeroports_des_vols` impose que le référentiel soit
  exactement l'ensemble des aéroports utilisés par les vols du seed, et aucun vol ne dessert TBJ.
  Il faudra l'ajouter en même temps que des vols, des voitures ou des transferts à Tabarka.
- **Site client inchangé** : la carte Tabarka de l'accueil avait été retirée le 19/10/2026 parce
  qu'elle menait à une page vide. Le catalogue n'a toujours qu'**une** activité à Tabarka
  (« Plongée aux récifs de Tabarka », seed) et aucun séjour. Je n'ai donc pas remis la carte. La
  clé i18n `home.destTags.tabarka` existe encore en fr / en / ar.
- **G-023 réannotée, pas réécrite** : on garde le texte de la demande générée, seule l'annotation
  suit le nouveau catalogue. Bizerte prend la place de Tabarka comme exemple de destination hors
  catalogue (README et test).

## 4. Vérification

```text
# Jeu d'évaluation : validation des 190 demandes (jeu_nlu.valider + recalcul des champs dérivés)
G-023: Tabarka []
190 demandes, en erreur : 0

# services\catalog : ..\..\.venv\Scripts\python -m pytest -q tests/test_lieux.py
12 passed, 2 warnings in 0.02s

# services\ai : ..\..\.venv\Scripts\python -m pytest -q
FAILED tests/test_main.py::test_health_et_health_detaillee - sqlalchemy.exc.O...
1 failed, 132 passed, 14 errors in 17.31s
```

Les 15 échecs (1 failed + 14 errors : `test_aeroports`, `test_collecte::test_upsert_idempotent`,
`test_journal`, `test_meteo`, `test_main`) ont tous la même cause :
`connection to server at "localhost" (127.0.0.1), port 5435 failed: Connection refused`.
Docker Desktop ne tournait pas, donc `postgres-ai` n'était pas démarré. On obtenait déjà le même
résultat (1 failed, 132 passed, 14 errors) avant l'ajout de Tabarka. **Ces 15 tests restent à
relancer avec la base démarrée.**

La collecte réelle des POI et de la météo de Tabarka n'a **pas** été lancée : elle demande la base
et le réseau.

## 5. Métriques

- Villes couvertes par le moteur IA : 8 → **9**.
- Jeu d'évaluation : 190 demandes, 0 erreur de validation ; demandes `hors_catalogue` : 2 → **1**
  (G-131, Douz, jeu test). **Le jeu dev n'a plus aucun cas hors catalogue.**
- POI et météo de Tabarka : non mesurés (collecte non lancée).

## 6. Limites, dette technique, risques

- **Contenu du catalogue** : 1 activité, 0 séjour, 0 vol, 0 voiture, 0 transfert à Tabarka. Le
  moteur pourra comprendre « Tabarka », mais il n'aura presque rien à proposer.
- **Jeu dev sans cas hors catalogue** : il faut ajouter une demande générée (par exemple
  « 3 jours à Bizerte… ») pour garder ce cas dans les exemples few-shot.
- **Relecture d'Ali** : sa ligne G-023 dans `relecture_ali.xlsx` doit indiquer
  `destination = Tabarka`. Sinon, l'import (`importer_relecture.py --appliquer`) remettra null.
  Le fichier était ouvert dans Excel au moment de ce rapport.
- La base existante n'a ni les POI ni la météo de Tabarka tant que les deux scripts de collecte
  n'ont pas tourné.

## 7. À vérifier par moi

```powershell
.\scripts\dev.ps1                                   # démarre postgres-ai (:5435)
cd services\ai
..\..\.venv\Scripts\python -m pytest -q              # attendu : 147 passed
..\..\.venv\Scripts\python scripts\collecter_pois.py --ville Tabarka
..\..\.venv\Scripts\python scripts\rafraichir_meteo.py --ville Tabarka
..\..\.venv\Scripts\python scripts\importer_relecture.py   # G-023 ne doit pas être signalée
```

Vérifier aussi que la collecte rattache bien l'aéroport TBJ à Tabarka (POI de type `aeroport`).

## 8. Étape suivante recommandée

Ajouter du contenu à Tabarka dans le catalogue (séjours, activités ; puis TBJ dans
`AEROPORTS_REFERENCE` si on ajoute du transport), remettre ensuite la carte d'accueil, et ajouter
un cas hors catalogue (Bizerte) au jeu dev. Ensuite, reprendre l'étape 4 (NLU).
