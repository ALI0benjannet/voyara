# Étape 01 (sous-tâche) — Seed réaliste du catalogue de démonstration

> Date : 2026-10-11 · Branche : `ia/etape-01` · Module(s) : 2 (données) — prépare les modules 2, 3, 4 et 5 ·
> Source : addendum de l'[étape 0](etape-00-cadrage.md#addendum-du-2026-10-11-après-validation-du-rapport)

## 1. Objectif

Donner au moteur IA un catalogue assez riche pour être évalué. Avec 8 activités, on ne peut mesurer
ni Recall@k / nDCG (étape 5), ni précision@5 et diversité (étape 6), ni donner de vrais arbitrages
au solveur (étape 7 : budget, distance, créneaux).

**Critère de « fini »** (addendum de l'étape 0) :
- script `services/catalog/scripts/seed_catalogue_demo.py` idempotent ;
- au moins 30 activités à Djerba et 60 à 100 au total sur 5 villes ;
- titres et descriptions en fr / en / ar ;
- catégories existantes, coordonnées GPS réelles, prix en DT, durées ;
- créneaux sur les 4 prochaines semaines ;
- lieux et types d'activités réels, aucune entreprise inventée ;
- rien d'écrasé dans le catalogue existant.

La collecte des POI (Overpass) et de la météo (Open-Meteo) reste à faire : l'étape 1 n'est **pas** cochée.

## 2. Réalisé

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `services/catalog/scripts/seed_catalogue_demo.py` | créé | 86 activités en fr/en/ar et leurs créneaux sur 28 jours. Idempotent. Option `--verifier` pour contrôler les données sans base. |
| `docs/architecture.md` | modifié | §7 « Seeds » : ajout du script. |
| `RUN.md` | modifié | §5.4 : commande du seed ajoutée après `seed_photos.py`. |
| `docs/plan.md` | modifié | Sous-tâche « Seed réaliste » cochée, avec le lien vers ce rapport (étape 1 laissée ouverte). |
| `docs/ia/journal.md` | modifié | Ligne de la sous-tâche. |
| `docs/ia/README.md` | modifié | Index des rapports. |
| `docs/ia/rapports/etape-01-seed-catalogue.md` | créé | Ce rapport. |

Aucun modèle, aucune route ni aucun autre service n'a été modifié : le script n'utilise que les
colonnes existantes de `activities` et `availabilities`.

### Répartition du seed (86 activités)

| Zone | Culture | Mer | Désert | Aventure | Gastronomie | **Total** |
|---|---:|---:|---:|---:|---:|---:|
| Djerba | 11 | 8 | 2 | 6 | 5 | **32** |
| Tunis / Sidi Bou Saïd | 9 | 2 | 0 | 2 | 3 | **16** |
| Sousse / Monastir | 6 | 4 | 0 | 2 | 2 | **14** |
| Hammamet | 5 | 3 | 0 | 2 | 2 | **12** |
| Tozeur | 3 | 0 | 5 | 2 | 2 | **12** |
| **Total** | **34** | **17** | **7** | **14** | **14** | **86** |

Sousse / Monastir se répartit en 9 activités à Sousse et 5 à Monastir.

### Répartition du catalogue complet en base (96 activités)

Elle compte les 86 activités du seed et les 10 activités qui existaient déjà :
- les 8 de `seed_catalog.py` ;
- 2 activités de test saisies dans l'admin (« touzer », « claude »).

| Zone | Culture | Mer | Désert | Aventure | Gastronomie | *sahra* (test) | **Total** |
|---|---:|---:|---:|---:|---:|---:|---:|
| Djerba | 11 | 9 | 2 | 6 | 5 | 0 | **33** |
| Tunis / Sidi Bou Saïd | 10 | 2 | 0 | 2 | 4 | 0 | **18** |
| Sousse / Monastir | 6 | 4 | 0 | 3 | 2 | 0 | **15** |
| Hammamet | 5 | 3 | 0 | 2 | 2 | 0 | **12** |
| Tozeur | 3 | 0 | 6 | 2 | 2 | 0 | **13** |
| Hors zones (Bizerte, Douz, Korbous, Tabarka, « touzer ») | 0 | 1 | 1 | 2 | 0 | 1 | **5** |
| **Total** | **35** | **19** | **9** | **15** | **13** | **1** | **96** |

« Sousse / Monastir » compte ici 15 activités : les 14 du seed et l'activité de test « claude »
(Monastir, Aventure).

### Contenu par zone (titres français)

- **Djerba (32)** :
  - **Culture** : Ghriba et Erriadh, Djerbahood, poterie et musée de Guellala, Houmt Souk et Borj El Kebir, musée du patrimoine traditionnel, mosquées ibadites (Fadhloun), musée Lalla Hadria / Djerba Explore, marché de Midoun (vendredi), Star Wars à Ajim, Meninx et El Kantara.
  - **Mer** : bateau pirate vers Ras Rmel, kitesurf à Bin El Ouedian, baptême de plongée, jet-ski, parachute ascensionnel, pêche à la charfia à Ajim, kayak à Aghir, paddle à la Seguia.
  - **Aventure** : vélo entre menzels et huileries, randonnée à Mahboubine, dromadaire, cheval, quad, ornithologie.
  - **Désert** : Ksar Ghilane (2 jours), Matmata et Tataouine.
  - **Gastronomie** : cours de cuisine, huile d'olive, criée de Houmt Souk, tabouna et brik, dîner dans un menzel.
- **Tunis / Sidi Bou Saïd (16)** : Bardo, médina, Carthage punique, Carthage romaine, Byrsa, Ennejma Ezzahra, calligraphie, souk des Chaouachia, Dougga (excursion), voilier, paddle à La Marsa, Carthage à vélo, Boukornine, cours de cuisine, bambalouni, marché central.
- **Sousse / Monastir (14)** : médina et Ribat de Sousse, musée archéologique, catacombes, El Jem (excursion), ribat de Monastir, mausolée Bourguiba, bateau pirate, plongée et jet-ski à Port El Kantaoui, îles Kuriat, cheval à Chott Meriem, vélo Skanes–Monastir, cuisine du Sahel, huile d'olive.
- **Hammamet (12)** : médina et Kasbah, Dar Sebastian, Pupput, Nabeul (vendredi), Kerkouane et Kélibia (excursion), bateau pirate, parachute ascensionnel, plongée, Carthage Land, cheval, cuisine du Cap Bon, harissa à Nabeul.
- **Tozeur (12)** : Ouled El Hadef, Dar Cherait, Nefta, calèche, oasis de montagne en 4x4, Chott el-Jérid, Ong Jemel / Mos Espa, dromadaire, quad, gorges de Mides, dattes Deglet Nour, khobz mella.

## 3. Choix techniques

| Décision | Option retenue | Alternatives envisagées | Pourquoi écartées |
|---|---|---|---|
| Source des coordonnées | **Géocodage OpenStreetMap (Nominatim)**, 102 requêtes au total, environ 1 par seconde, le 11/10/2026, puis valeurs **figées dans le script** | Coordonnées écrites de mémoire · géocodage à chaque exécution | De mémoire : invérifiable et souvent faux. À chaque exécution : dépendance réseau, résultat non reproductible, et charge inutile sur un service gratuit. |
| Contrôle des coordonnées | Rejet si l'activité est à **plus de 70 km du centre de sa zone** (haversine) | Aucun contrôle · bounding box de la Tunisie | Nominatim s'est trompé plusieurs fois : « Chebika » renvoyé dans le gouvernorat de Kairouan, « Kerkouane » à Manouba, « Erriadh » au centre de Djerba. Une bounding box nationale n'aurait rien vu. |
| Sens de `latitude`/`longitude` | **Point de rendez-vous.** Pour une excursion avec transport inclus (Ksar Ghilane, Matmata, Dougga, El Jem, Kerkouane, oasis de montagne, Chott el-Jérid, quad à Tozeur), c'est le point de départ | Coordonnées de la destination | Le solveur (étape 7) raisonne sur les trajets *depuis la ville de séjour*. Avec la destination (Ksar Ghilane est à 150 km de Djerba), une excursion compterait comme « loin » alors que le transport est inclus. La destination reste dans le titre et la description. |
| Clé d'idempotence | **Titre français** (comme `seed_catalog.py`) ; créneau = (activité, date, heure) | Colonne `source` / identifiant externe | Une colonne de plus imposerait une migration (pas d'Alembic dans catalog) pour un simple seed. Les titres sont uniques : c'est contrôlé par `--verifier`, qui a détecté un vrai doublon (« Balade à dromadaire au coucher du soleil » à Djerba et à Tozeur). |
| Activité déjà présente | **Rien n'est écrasé.** Seules les traductions vides sont complétées et les créneaux manquants ajoutés | Mise à jour complète des champs | Une correction faite dans l'admin serait perdue à chaque relance. |
| Horizon des créneaux | **28 jours à partir du lendemain de l'exécution**, avec des jours d'ouverture par activité (marché le vendredi, musées fermés le lundi, Ghriba fermée le samedi, Carthage Land le week-end…) | Un créneau tous les 2 jours à 9 h (comme `seed_catalog.py`) | Un créneau unique à 9 h ne donne aucun arbitrage au solveur. Des horaires réalistes (lever du soleil 05:45, coucher du soleil 16:30–17:00, dîner 19:00) créent de vraies contraintes. Relancer le script plus tard prolonge l'horizon sans doublon. |
| Capacités | **Par type d'activité** : 2 (parachute), 4–6 (jet-ski, 4x4, plongée), 8–15 (visites, ateliers), 40–50 (bateaux pirates, parc) ; `places_totales = places_disponibles` | Valeur unique (8) | Les capacités variées sont nécessaires pour tester les cas « complet » et les groupes (famille de 4 vs parachute à 2 places). |
| Prix | **Ordres de grandeur du marché en DT** (15 à 320 DT, médiane 45) | Tarifs officiels des sites | Les tarifs officiels changent et ne sont pas publiés pour la plupart des prestations. Le script indique en en-tête qu'il ne s'agit pas de tarifs officiels. |
| Noms propres | **Seulement des lieux réels** (sites, musées, plages, ports, parcs existants : Djerba Explore, Carthage Land, Dar Cherait…). **Aucun nom de prestataire** : « avec un moniteur certifié », « chez l'habitant » | Inventer des agences pour faire vrai | C'est la contrainte demandée : une entreprise fictive présentée comme réelle tromperait l'utilisateur, et le LLM la citerait comme un fait. |
| `localisation` | **« Ville, lieu »** (ex. `Djerba, Guellala`, `Tunis, Sidi Bou Saïd`) | Ville seule (format des 8 activités existantes) · colonne `ville` | La recherche actuelle fait un `LIKE` sur `localisation` : ce format garde la ville trouvable *et* donne le lieu précis. Une colonne `ville` relève de l'étape 2 (attributs IA dans catalog). |
| Catégories | **Les 5 existantes uniquement.** Le script s'arrête si l'une manque. La catégorie de test « sahra » est ignorée | Créer « Plage », « Famille »… | C'est la consigne. Les nuances (famille, intérieur, niveau de marche) sont prévues comme attributs à l'étape 2, pas comme catégories. |
| Validation | **`--verifier` intégré** : titres uniques, catégories connues, distance au centre de la zone, prix/durées/places > 0, 3 langues non vides, présence de caractères arabes, heures valides | Fichier pytest séparé | Le service catalog n'a pas encore de dossier de tests. La vérification est lancée automatiquement avant chaque écriture, ce qui empêche d'écrire des données invalides. Un test pytest pourra l'appeler plus tard. |

## 4. Vérification

Commandes lancées depuis `services\catalog` (PowerShell).

**1. Premier contrôle** : il a trouvé une vraie erreur (titre en double), que j'ai corrigée.

```text
PS> ..\..\.venv\Scripts\python scripts\seed_catalogue_demo.py --verifier
Données invalides :
  - titre en double : Balade à dromadaire au coucher du soleil
```

**2. Le garde-fou géographique détecte une erreur de géocodage** : on injecte la coordonnée fausse renvoyée par Nominatim pour Chebika.

```text
PS> ..\..\.venv\Scripts\python -c "...a['latitude'],a['longitude']=35.6589,9.9276; print(s.verifier())"
['Oasis de montagne en 4x4 : Chebika, Tamerza et Mides : à 254 km du centre de Tozeur']
```

**3. Écriture, puis deuxième passage pour vérifier l'idempotence**

```text
PS> ..\..\.venv\Scripts\python scripts\seed_catalogue_demo.py
Données valides : 86 activités.
[tableau de répartition du §2]
Prix (DT) : min 15 · médiane 45 · max 320
Durée (min) : min 20 · médiane 150 · max 2880

Horizon des créneaux : 2026-10-12 -> 2026-11-08
Terminé : 86 activité(s) créée(s), 0 traduction(s) complétée(s), 3664 créneau(x) ajouté(s).
Catalogue complet : 96 activité(s) en base.
----- 2e passage (idempotence) -----
Horizon des créneaux : 2026-10-12 -> 2026-11-08
Terminé : 0 activité(s) créée(s), 0 traduction(s) complétée(s), 0 créneau(x) ajouté(s).
Catalogue complet : 96 activité(s) en base.
```

**4. Contrôle direct en base** (requête SQLAlchemy hors script)

```text
Activités 1-10 inchangées : [(1, 'touzer'), (2, 'Sidi Bou Saïd & Carthage'), (3, 'Plongée aux récifs de Tabarka')] ...
Sans trad en/ar parmi id>10 : 0
Activités seed avec créneaux: 86 · créneaux/activité min 4 max 112 · dates 2026-10-12 -> 2026-11-08
Créneaux futurs total: 3664
Places incohérentes: 0
```

**5. Accès par l'API publique** : gateway sur :8000, services déjà démarrés.

```text
GET /api/v1/activities?search=<ville>  ->  total
djerba: 33 · tunis: 19 · sousse: 9 · monastir: 6 · hammamet: 12 · tozeur: 13
GET /api/v1/activities/11/availabilities
activité 11 : 40 créneaux, premier {'id': 92, 'activity_id': 11, 'date': '2026-10-12', 'heure': '09:00:00', 'places_disponibles': 12, 'places_totales': 12}
```

- « tunis » renvoie 19 résultats et non 18 : la recherche couvre aussi le texte, et « Randonnée au Cap Bon » (Korbous) mentionne « la baie de Tunis ».
- La réponse avec `lang=ar` contient bien `titre_ar` et `description_ar`, ainsi que la catégorie traduite (`مأكولات`).

**Non vérifié** : je n'ai pas fait de rendu visuel des pages client (cartes, RTL arabe) avec les nouvelles activités. Le composant `ActivityImage` gère `photos = null` avec un placeholder (vu dans le code, pas à l'écran).

## 5. Métriques

Jeu de données : `seed_catalogue_demo.py` (version de ce commit), base `voyara_catalog` locale, exécuté le 2026-10-11.

| Mesure | Valeur |
|---|---|
| Activités créées | 86 (Djerba 32), 5 zones, 5 catégories |
| Catalogue total en base | 96 activités |
| Créneaux créés | 3 664 (min 4, max 112 par activité), du 2026-10-12 au 2026-11-08 |
| Prix | min 15 DT · médiane 45 DT · max 320 DT |
| Durée | min 20 min · médiane 150 min · max 2 880 min (2 jours) |
| Traductions | 86/86 avec titre et description en en et ar |
| Géocodage OSM | 102 requêtes Nominatim (68 au 1er passage, 34 au 2e pour les lieux introuvables ou mal placés). Réponses fausses écartées à la main, par ex. Chebika (Kairouan), Kerkouane (Manouba), Erriadh et Mahboubine (centre de Djerba), « médina de Hammamet » (un hôtel de Yasmine), « marina de Monastir » (Ksibet el-Médiouni) |

## 6. Limites, dette technique, risques

- **Données de démonstration.** Les prix, capacités et horaires sont plausibles, pas officiels. Il faudra présenter les métriques des étapes 5 à 7 comme « mesurées sur un catalogue synthétique réaliste ».
- **4 coordonnées approximées**, faute de résultat Nominatim exploitable :
  - médina de Hammamet (36.3990, 10.6130) ;
  - Ouled El Hadef à Tozeur (33.9180, 8.1300) ;
  - souk des Chaouachia (36.7985, 10.1695) ;
  - centre-ville de Tunis comme point de départ de Dougga (36.7999, 10.1868).

  Elles sont à moins de 500 m du lieu réel d'après les points voisins géocodés, mais restent à confirmer sur une carte.
- **Coordonnées partagées** : plusieurs activités ont le même point de rendez-vous (4 à Sidi Mahrez, 5 à Midoun, 3 à Port El Kantaoui). C'est réaliste (même plage, même port), mais sur une carte les marqueurs se superposent.
- **Pas de photos** pour les 86 activités : le client affiche un placeholder. On pourra étendre `seed_photos.py` (Wikimedia Commons) plus tard.
- **Anciennes activités sans créneaux futurs** : les 90 créneaux de `seed_catalog.py` datent d'août–septembre 2026. Les 8 activités d'origine ne seront donc pas planifiables par le solveur tant que personne n'en ajoute. Je ne les ai pas touchées : la consigne était de ne pas modifier l'existant.
- **Données de test en base** : les activités « touzer » (catégorie « sahra ») et « claude » (Monastir) polluent les statistiques et les futures évaluations. À supprimer depuis l'admin avant l'étape 5 (décision à prendre par toi).
- **Horizon glissant** : les créneaux ne couvrent que les 28 jours suivant l'exécution. Pour une démo plus tardive, il faut relancer le script (il complète sans doublon).
- **Saison** : les activités nautiques sont plausibles en octobre–novembre, mais pas toute l'année. Le script ne modélise pas la saisonnalité, ce qui pourra compter à l'étape 7 avec Open-Meteo.
- **Faits culturels** : les descriptions s'appuient sur des faits connus (Djerba inscrite à l'UNESCO en 2023, charfia au patrimoine immatériel, Mos Espa à Ong Jemel, 35 000 places à El Jem…), mais je ne les ai pas revérifiés source par source. À relire avant la soutenance.
- **Arabe** : traductions rédigées en arabe standard, sans relecture par un arabophone natif. Le rendu RTL n'a pas été contrôlé visuellement.

## 7. À vérifier par moi

1. `git branch --show-current` → `ia/etape-01`.
2. Depuis `services\catalog` : `..\..\.venv\Scripts\python scripts\seed_catalogue_demo.py --verifier` → « Données valides : 86 activités » et le tableau du §2.
3. Relance `..\..\.venv\Scripts\python scripts\seed_catalogue_demo.py` → « 0 activité(s) créée(s) … 0 créneau(x) ajouté(s) » (idempotence).
4. Ouvre http://localhost:8000/api/v1/activities?search=djerba&size=50 → `total` vaut 33.
5. Sur le site client (http://localhost:5173), cherche « Djerba » :
   - les cartes s'affichent avec un placeholder ;
   - la carte montre des marqueurs sur l'île ;
   - en arabe, les titres sont en arabe et la mise en page est en RTL.
6. Ouvre 2 ou 3 activités et compare leurs coordonnées sur https://www.openstreetmap.org (ex. Ghriba 33.8139, 10.8594 ; Ribat de Sousse 35.8275, 10.6390). Contrôle en priorité les 4 coordonnées approximées du §6.
7. Décide du sort des activités de test « touzer », « claude » et de la catégorie « sahra » (je propose de les supprimer depuis l'admin).
8. Commit (message proposé dans le chat).

## 8. Étape suivante recommandée

Suite de l'**étape 1** sur la même branche `ia/etape-01` :
- base `voyara_ai` (`infra/postgres/init.sql` + `scripts/create_databases.py`) ;
- table `pois` ;
- script `collecter_pois.py` (Overpass, ≥ 300 POI, ≥ 5 villes, idempotent) ;
- client Open-Meteo avec cache de 6 h ;
- notebook d'EDA (il pourra aussi décrire ce catalogue : prix, durées, répartition) ;
- tests du mapping OSM et du cache.

Prérequis : Docker démarré, accès Internet (Overpass, Open-Meteo), Jupyter dans le venv.
Les POI collectés compléteront ce catalogue (lieux sans prix ni créneau). Ils ne le remplacent pas.
