# Étape 04 — Référentiel des villes étendu à toute la Tunisie (sous-tâche)

> Date : 2026-11-09 · Branche : ia/etape-04 · Module(s) : 1 (NLU, jeu d'évaluation) et 2 (POI, météo)

## 1. Objectif

Couvrir les 24 gouvernorats. Le référentiel des villes du moteur IA passe de 9 à **29 villes** :
les 24 chefs-lieux, plus Sidi Bou Saïd, Hammamet, Djerba, Tabarka et Douz. Le travail suit le
modèle de l'ajout de Tabarka (rapport `etape-04-ajout-tabarka.md`). Les mêmes villes entrent dans le
vocabulaire du jeu NLU, et les demandes et fichiers de relecture qui les citent sont réannotés.
Hors périmètre : le service catalog, le site client et la collecte réelle des POI et de la météo.

## 2. Réalisé

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `services/ai/app/villes.py` | modifié | 20 villes ajoutées (coordonnées OSM vérifiées, rayon commenté quand il n'est pas évident), docstring « 29 villes » |
| `services/ai/app/collecte.py` | modifié | `ville_de_rattachement` (rattachement unique en zone commune), `VILLE_IMPOSEE_PAR_IATA = {"TUN": "Tunis"}`, docstring des aéroports ignorés (El Borma) |
| `services/ai/scripts/collecter_pois.py`, `rafraichir_meteo.py`, `RUN.md` | modifiés | « 9 villes » → « 29 villes » |
| `services/ai/scripts/jeu_nlu.py` | modifié | `VILLES_CATALOGUE` : 29 villes |
| `services/ai/data/eval/README.md` | modifié | Composition 190 → 192 ; §2 liste des 29 villes ; §3 exemples hors catalogue (Matmata, Ksar Ghilane…) et règle des noms de gouvernorat |
| `services/ai/data/eval/nlu_test.jsonl` | modifié | G-131 réannotée (Douz) ; G-138 ajoutée (Ksar Ghilane, hors catalogue) |
| `services/ai/data/eval/nlu_dev.jsonl` | modifié | G-137 ajoutée (Matmata, hors catalogue) |
| `docs/ia/relecture/relecture_ali.xlsx` | modifié | G-131 : 2 cellules (destination, commentaire) |
| `services/ai/tests/test_villes.py` | créé | 7 tests : 24 gouvernorats couverts, 29 noms uniques, coordonnées en Tunisie, recouvrements limités au Grand Tunis, rattachement unique |
| `services/ai/tests/test_aeroports.py` | modifié | SFA rattaché à Sfax, TUN à Tunis (exception), EBM comme exemple ignoré, 3 → 4 POI |
| `services/ai/tests/test_relecture_jeu_nlu.py` | modifié | Destination invalide « Bizerte » → « Matmata » ; 190 → 192 demandes ; 4 × 48 lignes de relecture ; 187 non distribuées |

**Les 29 villes**

Source des coordonnées : nœud `place` OpenStreetMap, interrogé avec Nominatim le 09/11/2026. Exceptions : Le Kef et
Siliana, qui n'ont pas de nœud `place`, ont le centre de leur polygone résidentiel OSM. Les 9 villes déjà présentes
n'ont pas changé.

| Ville | Gouvernorat | Latitude | Longitude | Rayon (m) | Aéroport rattaché |
|---|---|---|---|---|---|
| Djerba | Médenine | 33.8100 | 10.8800 | 16 000 | DJE (12,2 km) |
| Tunis | Tunis | 36.7990 | 10.1700 | 5 000 | TUN (7,9 km, exception explicite) |
| Sidi Bou Saïd | Tunis | 36.8687 | 10.3416 | 2 000 | — |
| Sousse | Sousse | 35.8256 | 10.6411 | 6 000 | NBE (33,6 km) |
| Hammamet | Nabeul | 36.4000 | 10.6167 | 7 000 | — |
| Monastir | Monastir | 35.7643 | 10.8113 | 5 000 | MIR (5,4 km) |
| Tozeur | Tozeur | 33.9197 | 8.1335 | 6 000 | TOE (3,8 km) |
| Kairouan | Kairouan | 35.6781 | 10.0963 | 4 000 | — |
| Tabarka | Jendouba | 36.9544 | 8.7580 | 6 000 | TBJ (11,2 km) |
| Ariana | Ariana | 36.8587 | 10.1882 | 2 500 | — (TUN imposé à Tunis) |
| Ben Arous | Ben Arous | 36.7517 | 10.2245 | 2 500 | — |
| La Manouba | La Manouba | 36.8113 | 10.0947 | 2 500 | — |
| Nabeul | Nabeul | 36.4513 | 10.7356 | 4 000 | — |
| Zaghouan | Zaghouan | 36.3995 | 10.1446 | 3 000 | — |
| Bizerte | Bizerte | 37.2721 | 9.8709 | 5 000 | — |
| Béja | Béja | 36.7237 | 9.1854 | 3 000 | — |
| Jendouba | Jendouba | 36.4967 | 8.7757 | 8 000 | — |
| Le Kef | Le Kef | 36.1784 | 8.7073 | 3 000 | — |
| Siliana | Siliana | 36.0847 | 9.3744 | 3 000 | — |
| Mahdia | Mahdia | 35.5036 | 11.0682 | 5 000 | — |
| Sfax | Sfax | 34.7394 | 10.7604 | 6 000 | SFA (7,0 km) |
| Kasserine | Kasserine | 35.1688 | 8.8366 | 4 000 | — |
| Sidi Bouzid | Sidi Bouzid | 35.0382 | 9.4865 | 3 000 | — |
| Gabès | Gabès | 33.8878 | 10.1004 | 5 000 | GAE (24,5 km) |
| Médenine | Médenine | 33.3434 | 10.4911 | 3 000 | — |
| Tataouine | Tataouine | 32.9315 | 10.4504 | 4 000 | — |
| Gafsa | Gafsa | 34.4224 | 8.7844 | 4 000 | GAF (3,4 km) |
| Kébili | Kébili | 33.7061 | 8.9698 | 4 000 | — |
| Douz | Kébili | 33.4571 | 9.0250 | 5 000 | — |

Aéroport ignoré : **EBM** (El Borma), à 177 km de Tataouine, la ville couverte la plus proche (seuil : 60 km).

**Demandes réannotées**

| Id | Fichier | Champ | Avant | Après |
|---|---|---|---|---|
| G-131 | `nlu_test.jsonl` | `destination` | `null` | `"Douz"` |
| G-131 | `nlu_test.jsonl` | `champs_manquants` | `["destination", "voyageurs"]` | `["voyageurs"]` |
| G-131 | `nlu_test.jsonl` | `tags` | `["hors_catalogue", "incomplet"]` | `["incomplet"]` |
| G-131 | `relecture_ali.xlsx` l.15 | `destination` (F15) | vide | `Douz` |
| G-131 | `relecture_ali.xlsx` l.15 | `commentaire` (AK15) | vide | `Douz ajoutée au catalogue le 09/11/2026 : destination réannotée` |

Le statut d'Ali (`valide`) reste valable. `importer_relecture.py` compare les valeurs Excel au JSONL
(`modifie = nouveau != demande["attendu"]`) : les deux disent Douz, donc il n'y a pas d'avertissement.
Le texte de la demande n'a pas changé. Le grep a aussi trouvé deux demandes sans changement à faire :

- H-032 (« men sfax ») : Sfax y est la ville de départ, déjà annotée `ville_depart = Sfax` ;
- H-086 : faux positif (« الكافيات » veut dire « les cafés », pas Le Kef).

**Nouvelles demandes hors catalogue (accord du 09/11/2026)**

- G-137 (dev) : « 3 jours à Matmata dans une maison troglodyte, 600 DT, en couple. » →
  `destination` null, `champs_manquants` `["destination"]`.
- G-138 (test) : « n7eb nemchi Ksar Ghilane 2 jours m3a s7abi, budget 400 dt » → `destination` null,
  `type_voyage` amis, `champs_manquants` `["destination", "voyageurs"]`.

## 3. Choix techniques

- **Orthographe canonique.** Seules Douz et Bizerte figurent dans les `localisation` du catalogue
  (`seed_catalog.py`). Les 18 autres villes n'y apparaissent pas. On retient la forme française
  officielle avec accents : Béja, Le Kef, La Manouba, Gabès, Médenine, Kébili. « Le Kef » a été
  préféré à « Kef » ou « El Kef », qui s'annotent « Le Kef » d'après le README.
- **Rayons.** 2,5 à 3 km pour les petits chefs-lieux et le Grand Tunis, 4 à 6 km pour les villes moyennes.
  Trois rayons sont plus larges : Jendouba (8 km, inclut Bulla Regia à 7,1 km), Gabès (5 km, inclut
  l'oasis de Chenini de Gabès) et Douz (5 km, inclut la zone touristique). Nabeul est limité à 4 km pour
  laisser 1,1 km entre son cercle et celui de Hammamet.
- **Recouvrements mesurés.** Seul le Grand Tunis se recouvre, parce que Tunis garde ses 5 km :
  - Tunis–Ariana : 1,30 km², soit 6,6 % du petit cercle ;
  - Tunis–La Manouba : 1,27 km², 6,5 % ;
  - Tunis–Ben Arous : 0,48 km², 2,5 %.

  Les autres paires ne se recouvrent pas :
  - Nabeul–Hammamet : 1,1 km d'écart entre les cercles ;
  - Sousse–Monastir : 5,8 km d'écart ;
  - Kébili–Douz : 28 km entre les centres ;
  - Médenine–Djerba : 63 km entre les centres.

  Un test fige cette liste.
- **Rattachement unique.** `source_id` est unique et l'enregistrement fait un upsert : une même ligne
  n'est jamais créée deux fois. En revanche, sans filtre, un POI de la zone commune prenait la `ville` de la
  **dernière** collecte lancée. On retient `ville_de_rattachement` : parmi la ville collectée et les villes
  dont le cercle contient le point, on prend le centre le plus proche. Une première version (« centre le
  plus proche » sans condition de cercle) a été écartée avant les tests : elle aurait perdu les POI situés
  dans le cercle de Tunis mais plus près d'Ariana, hors du cercle d'Ariana, ainsi que la bordure du cercle
  de Hammamet côté Nabeul. Les 9 villes déjà collectées ne se recouvrent pas, donc leurs POI ne changent pas.
- **TUN → Tunis par exception explicite.** Par la distance, TUN irait à Ariana (3,8 km contre 7,9 km
  pour Tunis). On garde Tunis, comme `AEROPORTS_REFERENCE` du catalogue et comme les voyageurs le
  désignent. L'alternative (Ariana, géographiquement exacte) aurait obligé à faire le lien entre deux noms
  avec le transport du catalogue.
- **Rattachements des aéroports.** SFA, GAE et GAF, ignorés jusqu'ici, sont rattachés à Sfax, Gabès et
  Gafsa. NBE reste à Sousse (33,6 km ; Hammamet à 39,3 km). EBM reste ignoré.
- **Correction de distance.** L'aéroport TBJ est à **11,2 km** du centre de Tabarka (Nominatim
  way/129798793), et non à « environ 5 km ». Le rayon de collecte de 6 km ne le couvre donc pas.
  Son rattachement à Tabarka reste juste, puisque la règle des 60 km suffit. L'ancien rapport n'a pas
  été modifié.
- **Exemples hors catalogue.** Matmata et Ksar Ghilane. Korbous a été écarté parce qu'il est une
  `localisation` du catalogue (`seed_catalog.py`, une activité). Chenini a été écarté parce que le nom
  désigne aussi l'oasis de Chenini de Gabès, dans le rayon de Gabès.
- **Excel modifié au niveau XML.** On a remplacé seulement les deux balises `<c>` de
  `xl/worksheets/sheet1.xml` (chaînes « inline »), sans réenregistrer le classeur avec openpyxl : la mise
  en forme, les validations et l'onglet « Lisez-moi » restent intacts.

## 4. Vérification

```text
# Référence AVANT modification — services\ai : ..\..\.venv\Scripts\python -m pytest -q
1 failed, 132 passed, 14 errors in 17.99s

# Validation du jeu (jeu_nlu.valider sur toutes les demandes)
192 demandes, erreurs : 0
hors_catalogue : [('G-137', 'dev'), ('G-138', 'test')]

# Simulation d'import : ..\..\.venv\Scripts\python scripts\importer_relecture.py
ERREURS (lignes non appliquées) : 4      (H-052, H-043, H-016, H-066 — identiques à la référence)
Avertissements : 10                      (identiques à la référence)
Non relues (statut vide) : 0
Absentes de tous les fichiers : 2
  - G-137
  - G-138
Appliquées : valide 176, corrige 10  (simulation : relancer avec --appliquer pour écrire)

# Excel : comparaison de toutes les cellules (valeur + style) avec les sauvegardes
ali       | 1825 cellules comparées | parties .xlsx modifiées : ['xl/worksheets/sheet1.xml'] | cellules modifiées : 2
    ('Relecture', 'F15', 'G-131', 'destination', None, 'Douz', True)
    ('Relecture', 'AK15', 'G-131', 'commentaire', None, 'Douz ajoutée au catalogue le 09/11/2026 : destination réannotée', True)
boutheina | 1825 cellules comparées | parties .xlsx modifiées : [] | cellules modifiées : 0
ghayth    | 1788 cellules comparées | parties .xlsx modifiées : [] | cellules modifiées : 0
ons       | 1788 cellules comparées | parties .xlsx modifiées : [] | cellules modifiées : 0

# APRÈS — services\ai : ..\..\.venv\Scripts\python -m pytest -q
1 failed, 139 passed, 14 errors in 15.79s
```

Les 15 échecs sont les mêmes qu'avant la modification, et tous viennent du port 5435 refusé
(`postgres-ai` non démarré) : `test_main::test_health_et_health_detaillee`,
`test_aeroports::test_collecte_et_upsert_sans_doublon`, `test_collecte::test_upsert_idempotent`,
`test_journal` (3) et `test_meteo` (9). Ils restent à relancer avec la base démarrée, en particulier
`test_collecte_et_upsert_sans_doublon`, dont l'attendu passe de 3 à 4 POI. Les 7 tests en plus sont ceux
de `test_villes.py`.

**4 erreurs et 10 avertissements d'import déjà présents.** Ils viennent du commit `2191b7e`
(« validation de 4 fechier », 18:15), qui a modifié les 4 Excel après la clôture Tabarka (16:36). Ils
n'ont pas été corrigés : la décision revient à l'équipe. Détail (valeur Excel | valeur JSONL) :

| Fichier, ligne | Id | Type | Colonne(s) : Excel → JSONL |
|---|---|---|---|
| ali l.39 | H-052 | erreur | `nb_enfants` : vide ≠ 0 (nb_adultes vidé, nb_enfants non) |
| ghayth l.22 | H-043 | erreur | `nb_voyageurs` 1 ≠ null, `nb_adultes` 1 ≠ null, `type_voyage` solo ≠ null, `voiture` non ≠ indifferent ; `nb_enfants` vide (le commentaire dit le contraire : « laissés vides ») |
| ghayth l.42 | H-016 | erreur | `nb_adultes` 4 ≠ null, `nb_enfants` vide |
| ons l.26 | H-066 | erreur | `nb_voyageurs` 5 ≠ 4, `nb_adultes` 5 ≠ null, `type_voyage` amis ≠ famille ; `nb_enfants` vide |
| ali l.3 | H-019 | avert. | `voiture` non ≠ indifferent |
| boutheina l.22 | H-041 | avert. | `nb_voyageurs` 1, `nb_adultes` 1, `nb_enfants` 0, `type_voyage` solo ≠ null |
| boutheina l.41 | H-072 | avert. | `budget_montant` 100 ≠ 400 |
| ghayth l.9 | H-030 | avert. | `budget_montant` 250 ≠ 1250, `voiture` non ≠ indifferent |
| ghayth l.33 | G-119 | avert. | `vol` oui ≠ indifferent |
| ons l.14 | G-111 | avert. | `nb_adultes` vide ≠ 2, `nb_enfants` vide ≠ 0 |
| ons l.19 | H-092 | avert. | `nb_voyageurs` 4 ≠ 3, `nb_adultes` 4 ≠ null, `nb_enfants` 0 ≠ null (le commentaire parle de 3 adultes) |
| ons l.36 | H-095 | avert. | `vol` non ≠ indifferent |
| ons l.39 | H-125 | avert. | `activites_souhaitees` : « team building » retiré |
| ons l.48 | H-060 | avert. | `budget_montant` 50 ≠ 200, `voiture` non ≠ indifferent |

Les 10 avertissements ne bloquent pas : à l'import, ces lignes passeront en `corrige`. Les 4 erreurs
empêchent l'import de ces lignes tant que `nb_adultes` et `nb_enfants` ne sont pas remplis ensemble (ou
vidés ensemble).

## 5. Métriques

- Villes couvertes par le moteur IA : 9 → **29** (24 gouvernorats sur 24).
- Aéroports rattachés : 6 → **9** (+ SFA, GAE, GAF) ; 1 ignoré (EBM).
- Jeu d'évaluation : 190 → **192 demandes** (130 `humain` + 62 `genere`), 0 erreur de validation ;
  demandes `hors_catalogue` : 1 → 0 après la réannotation de G-131, puis **2** avec G-137 (dev) et G-138 (test).
- Tests du service ai : 132 → **139 passed** ; 15 échecs dus à l'absence de base, identiques à la référence.
- POI et météo des 20 nouvelles villes : non mesurés (collecte non lancée).

## 6. Limites, dette technique, risques

- **Collecte non lancée** : la base n'a ni les POI ni la météo des 20 nouvelles villes. Il faut la lancer
  ville par ville ou avec une pause, pour ne pas saturer Overpass et Open-Meteo.
- **Catalogue presque vide hors des 9 villes historiques** : seules Douz et Bizerte y ont une activité
  (seed). Le moteur comprendra « Sfax » ou « Le Kef », mais il n'aura presque rien à proposer.
- **G-137 et G-138 ne sont dans aucun fichier de relecture.** La simulation les signale (« Absentes de
  tous les fichiers : 2 »). `generer_relecture.py` refuse d'écraser les fichiers : il faudra les ajouter à
  la main dans un des Excel, ou les faire relire séparément.
- **Activités souhaitées de G-138** : Ksar Ghilane est ici la destination demandée, donc on n'a mis aucune
  activité, comme pour G-131 (Douz). Le README dit pourtant qu'« un lieu précis hors catalogue est une
  activité ». Cette règle vise les lieux visités pendant le séjour, mais le cas mérite d'être confirmé à la
  relecture.
- Le Kef et Siliana n'ont pas de nœud `place` dans OSM : leur centre est celui du polygone résidentiel
  (à moins de 1 km du centre usuel).
- Les rayons sont estimés, pas mesurés sur les POI réels : ils seront à revoir après la première collecte
  (nombre de POI par ville).
- La sous-tâche Tabarka du plan mentionne encore « un cas hors catalogue (Bizerte) au jeu dev » : c'est
  fait avec G-137 (Matmata). Je n'ai pas réécrit la ligne existante.

## 7. À vérifier par moi

```powershell
.\scripts\dev.ps1                                   # démarre postgres-ai (:5435)
cd services\ai
..\..\.venv\Scripts\python -m pytest -q              # attendu : 154 passed
..\..\.venv\Scripts\python scripts\collecter_pois.py --aeroports --dry-run   # attendu : 9 aéroports, TUN → Tunis, SFA → Sfax
..\..\.venv\Scripts\python scripts\collecter_pois.py --ville Sfax            # une ville à la fois
..\..\.venv\Scripts\python scripts\rafraichir_meteo.py --ville Sfax
..\..\.venv\Scripts\python scripts\importer_relecture.py   # G-131 ne doit pas être signalée
```

Ouvrir `relecture_ali.xlsx` et vérifier la ligne G-131 : destination Douz et commentaire. Trancher aussi
les 4 erreurs et les 10 avertissements avec les relecteurs concernés.

## 8. Étape suivante recommandée

Relancer les tests avec `postgres-ai` démarré, puis collecter les POI et la météo des 20 villes, avec une
pause entre deux villes. Ensuite : trancher les écarts de relecture, faire relire G-137 et G-138, puis
reprendre l'étape 4 (NLU). L'ajout de contenu au catalogue dans les nouvelles villes (activités,
séjours, puis aéroports SFA/GAE/GAF/TBJ dans `AEROPORTS_REFERENCE` avec des vols) est un chantier
séparé.
