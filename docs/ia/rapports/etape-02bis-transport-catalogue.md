# Étape 2-bis — Hébergements et offres de transport pour l'IA

> Date : 2026-10-20 · Branche : `ia/etape-02bis` · Module(s) : 2 (recherche & collecte) + architecture ·
> Source : [Guide_Moteur_IA_Voyara.pdf](../../../AgentIA_Voyara/Guide_Moteur_IA_Voyara.pdf) (v2, étape 2-bis)

## 1. Objectif

Rendre lisibles par le service ai les **hébergements, vols, voitures de location et transferts** du
catalogue, et mettre l'architecture et la documentation à jour pour ce périmètre (guide v2).
Principe : le transport **n'est pas indexé en vecteurs**. Prix, places et horaires changent et se
cherchent par critères exacts, donc le service ai interrogera catalog **en direct**. Seuls les
hébergements rejoignent l'index sémantique de l'étape 5.

Critère de « fini » du guide : *les 4 endpoints internes répondent et sont testés (401/403,
filtres, pagination) ; les tests de l'étape 2 restent verts ; l'architecture documentée correspond
au code.* **Atteint** : 5 routes (les 4 du guide + le référentiel des aéroports), 37 tests
nouveaux, 51 tests de l'étape 2 verts, documentation à jour.

### Inventaire de départ (modèles réels, `services/catalog/app/models.py`)

| Table (lignes) | Champs utiles | Disponibilité | Lien avec un lieu | Ce qui manquait |
|---|---|---|---|---|
| `stays` (27) | nom (+en/ar), type, description (+en/ar), localisation, latitude/longitude (27/27), etoiles, prix_nuit, capacite, equipements (texte « a,b,c »), photos | `actif` | `localisation` « Tunis, Sidi Bou Saïd » | `modifie_le` (sync incrémentale) ; **aucune note** (review ne note que les activités) |
| `flights` (632, 0 complet) | compagnie, numero_vol, aeroport_depart/arrivee (IATA), ville_depart/arrivee, depart_le/arrivee_le, classe, prix par passager, places_disponibles/totales | `places_disponibles` | IATA + ville | **fuseau** (heures locales naïves), **escales** (1 ligne = 1 tronçon direct) |
| `car_rentals` (35) | marque, modele, categorie, transmission, carburant, nb_places, agence, localisation, prix_jour, photos | booléen `disponible` | texte « Tunis, aéroport Tunis-Carthage » | **ville**, **code aéroport** ; pas de lieu de retour |
| `transfers` (32) | depart, arrivee (textes), type_vehicule, capacite, bagages, duree (min), prix par véhicule, description | `actif` | textes « Aéroport Djerba-Zarzis » → « Djerba, … » | **villes** et **codes aéroport** de départ et d'arrivée |

POI de `voyara_ai` : 1 030, **aucun aéroport** → le point 3 du prompt s'appliquait.

## 2. Réalisé

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `services/catalog/app/lieux.py` | créé | Référentiel des 14 aéroports, `normaliser`, `deduire_lieu` (texte → ville + IATA), `completer_lieux`, `resoudre_lieu` (IATA / ville / texte) |
| `services/catalog/app/recherche_transport.py` | créé | Calculs purs : fuseaux (`zoneinfo`), fenêtre ± N jours, composition des correspondances, prix, tri, jours de location |
| `services/catalog/app/internal_offres_routes.py` | créé | 5 routes internes : `/internal/airports`, `/stays/export`, `/flights/search`, `/car-rentals/search`, `/transfers/search` |
| `services/catalog/app/models.py` | modifié | Table `Aeroport` (+ remplissage à la création), `stays.modifie_le` + trigger, colonnes de lieu sur `car_rentals` et `transfers`, DDL du trigger factorisée (`ddl_trigger_modifie_le`) |
| `services/catalog/app/main.py` | modifié | Inclusion de `internal_offres_router` |
| `services/catalog/app/travel_routes.py` | modifié | Champs de lieu **optionnels** dans `CarRentalIn` / `TransferIn`, déduits du libellé à chaque écriture s'ils sont omis |
| `services/catalog/scripts/add_transport_ia.py` | créé | Migration idempotente en une transaction : table + référentiel, 7 colonnes, index, trigger, remplissage des lieux vides, bilan |
| `services/catalog/scripts/seed_offres_voyage_demo.py` | modifié | Complète ville / aéroport des voitures et transferts créés par le seed |
| `services/catalog/requirements.txt` | modifié | `tzdata==2026.5` (base des fuseaux, absente de Windows) |
| `services/catalog/tests/test_lieux.py` | créé | 12 tests purs : référentiel = codes des vols, déduction sur **toutes** les localisations réelles du seed, résolution, jours facturés |
| `services/catalog/tests/test_transport_interne.py` | créé | 25 tests d'intégration (vraie base, transaction annulée) sur aéroports fictifs ZZA/ZZB/ZZC |
| `services/ai/app/models.py` | modifié | `aeroport` ajouté à `TYPES_POI` |
| `services/ai/app/osm.py` | modifié | Règle `aeroway=aerodrome` **avec** `iata` → `aeroport` |
| `services/ai/app/collecte.py` | modifié | Requête nationale des aéroports, `distance_km` (haversine), `ville_la_plus_proche`, `selectionner_aeroports`, `collecter_aeroports` |
| `services/ai/scripts/collecter_pois.py` | modifié | Option `--aeroports` ; message d'échec adapté (miroir via `OVERPASS_URL`) |
| `services/ai/tests/test_osm.py`, `tests/test_aeroports.py` | modifié / créé | 3 + 6 tests : règle aéroport, requête, ville la plus proche, dédoublonnage nœud/contour, upsert, option du script |
| `docs/architecture.md` | modifié | Avenant v2 à l'ADR-007, schéma « Flux du moteur IA (v2) », ligne `ai` et catalog dans §3, endpoints internes, §4.3, limite n° 13 (`localhost`) |
| `CLAUDE.md` | modifié | Périmètre du moteur IA, tableau des endpoints internes, migrations, guide v2 comme source |
| `docs/ia/README.md` | modifié | Schéma des 6 modules avec le transport, tableau « place du transport », 4ᵉ scénario, index des rapports |
| `docs/plan.md` | modifié | Tâche 2-bis cochée (+ 2 sous-tâches ouvertes), étapes 3 à 13 réécrites selon le guide v2 |
| `docs/mcd.md` | modifié | Table `AEROPORTS`, nouvelles colonnes, type POI `aeroport` |
| `docs/ia/rapports/etape-00-…`, `etape-01-poi-meteo.md`, `etape-02-…` | modifié | Courte section « Avenant v2 » en fin de rapport (rien d'autre réécrit) |
| `docs/ia/journal.md` | modifié | Ligne de l'étape 2-bis |

## 3. Choix techniques

**Référentiel des aéroports dans catalog** (choix validé avec toi en plan mode)
- *Retenu* : table `aeroports` (code IATA, nom, ville, pays, fuseau IANA), 14 lignes = les codes
  déjà utilisés par `flights`, sans clé étrangère depuis `flights`.
- *Écarté* : constantes dans le code des routes (référentiel invisible et non corrigeable) ; aucune
  table (durées fausses d'une heure vers l'Europe en été, « Paris » impossible à relier à ORY + CDG).
- *Pourquoi pas de FK* : l'admin peut saisir un code non référencé ; la recherche l'accepte et
  renvoie alors une durée `null` au lieu de refuser l'enregistrement.
- *Pourquoi pas de coordonnées* : la géographie vient d'OSM (POI `aeroport` côté ai), comme pour tous
  les POI. Les deux sont rapprochés par code IATA, sans jointure.

**Colonnes de lieu sur voitures et transferts** (validé)
- *Retenu* : `car_rentals.ville / aeroport`, `transfers.ville_depart / ville_arrivee /
  aeroport_depart / aeroport_arrivee`, nullables, remplies depuis le libellé par `deduire_lieu` à la
  migration, à chaque écriture admin et dans le seed, **sans jamais écraser** une valeur saisie.
- *Écarté* : déduire à chaque lecture (fragile, filtrage en Python, rien à corriger côté admin) ;
  colonnes `NOT NULL` (un libellé inattendu ferait échouer la migration).
- Front admin inchangé : les champs sont optionnels dans l'API ; les exposer dans les formulaires
  est une sous-tâche `should` du plan.

**`ville` des séjours dérivée, pas stockée**
- *Retenu* : préfixe de `localisation`, calculé à l'export (même convention que les filtres publics
  `/offres`). *Écarté* : une colonne de plus pour une information déjà présente et non ambiguë.

**Note des hébergements**
- *Retenu* : exporter `etoiles` seulement. *Écarté* : un champ `note` inventé. Le service review
  ne note que les activités. Ajouter des avis sur les séjours est une évolution de review, pas de
  cette étape.

**Escales : correspondances composées à la volée** (validé)
- *Retenu* : directs + **1 correspondance** (même aéroport, attente 60 min–8 h, même classe, pas de
  retour à l'origine), places restantes = minimum des tronçons, prix = somme.
- *Écarté* : directs seuls (Lyon, Bruxelles, Genève → Djerba : 0 résultat, voir §5) ; colonne
  `escales` (fausse dès qu'un vol est saisi tronçon par tronçon) ; 2 escales et plus (explosion
  combinatoire pour un gain nul sur ce réseau).

**Durées par fuseau**
- *Retenu* : `zoneinfo` + `tzdata`, dates ISO 8601 **avec décalage**
  (`2026-10-24T11:00:00+02:00`). Vérifié : Paris → Djerba = 175 min, la durée du seed, malgré
  l'écart Paris (UTC+2) / Tunis (UTC+1).
- *Écarté* : différence d'heures locales (fausse de ± 1 h) ; stocker l'UTC (changerait le sens
  d'une colonne utilisée par le site et l'admin).

**Lieu inconnu → 404 pour les vols**
- *Retenu* : `404 « Lieu inconnu : X »`, distinct d'une liste vide : l'agent pourra demander une
  précision au lieu de conclure « aucun vol ». *Écarté* : 200 vide (ambigu). Pour voitures et
  transferts, un texte inconnu est un filtre « contient » (« Midoun », « centre »), donc une liste
  vide est une réponse légitime.

**Voitures : pas d'aller simple, pas de stock par date**
- *Retenu* : retour obligatoire dans la ville de prise (sinon 0 résultat), `disponible = true`,
  prix total = prix/jour × ⌈durée / 24 h⌉. *Écarté* : inventer un tarif d'abandon ou un stock. Le
  catalogue n'a ni réservation de voiture ni lieu de retour : je n'invente rien.

**Transferts : sens enregistré uniquement, prix par véhicule**
- *Retenu* : on ne renvoie que les trajets dans le sens demandé, avec capacité ≥ passagers et
  bagages ≥ demandés, `prix_total` = prix du véhicule, `prix_par_passager` indicatif et
  `arrivee_estimee` = prise en charge + durée. *Écarté* : réutiliser l'aller pour le retour (prix
  non connu) ; appliquer la majoration de nuit citée dans les descriptions (texte libre, pas une
  règle tarifaire).

**Pagination en Python pour les recherches**
- Les itinéraires composés n'existent pas en SQL ; les candidats sont filtrés en SQL (dates,
  places, lieux), puis composés, triés et paginés avec `voyara_common.pagination.paginate`.
  Volume : quelques dizaines de lignes, p95 = 40 ms (§5).

**Nommage des routes**
- Même convention que `/internal/activities/export` : ressource anglaise des routes admin
  (`stays`, `flights`, `car-rentals`, `transfers`, `airports`), paramètres et champs en français.

**Aéroports dans le collecteur POI**
- *Retenu* : une **requête nationale** (`aeroway=aerodrome` + `iata`, zone ISO TN) ; ville = ville
  couverte la plus proche à ≤ 60 km ; code IATA gardé dans `tags`. Un aéroport présent deux fois
  (nœud + contour) donne un seul POI, le contour.
- *Écarté* : la collecte par rayon autour des villes (Enfidha à ~35 km de Sousse, Tunis-Carthage à
  ~8 km du centre : hors rayon) ; tous les `aerodrome` sans IATA (aéroclubs, pistes).
- Effet de bord assumé : NBE (Enfidha-Hammamet) est rattaché à **Sousse**, la ville couverte la
  plus proche (33 km contre 39 km pour Hammamet). Côté catalog, sa ville est « Enfidha », comme dans
  les vols. La jointure se fait par code IATA, pas par ville.
- *Ports et gares* : aucune offre du catalogue ne les référence, donc ils ne sont pas collectés (§6).

## 4. Vérification

Sauvegarde avant migration (taille du fichier) :

```powershell
docker exec voyara-postgres-1 pg_dump -U <utilisateur> voyara_catalog > …\voyara_catalog_avant_02bis.sql
# 470 799 octets
```

Migration, lancée deux fois (idempotence) :

```text
PS> ..\..\.venv\Scripts\python scripts\add_transport_ia.py
Table aeroports déjà présente ; 0 aéroport(s) ajouté(s).
Lieux complétés : 35 voiture(s), 32 transfert(s) (23 voitures et 31 transferts liés à un aéroport).
Tous les libellés sont résolus.
Conservé(e)s : 27 séjours, 632 vols, 35 voitures, 32 transferts, 14 aéroports.
--- relance ---
Table aeroports déjà présente ; 0 aéroport(s) ajouté(s).
Lieux complétés : 0 voiture(s), 0 transfert(s) (23 voitures et 31 transferts liés à un aéroport).
Tous les libellés sont résolus.
Conservé(e)s : 27 séjours, 632 vols, 35 voitures, 32 transferts, 14 aéroports.
```

« déjà présente » dès le premier passage : les services de dev tournaient en `--reload`.
Le `create_all` de catalog a donc créé et rempli `aeroports` (listener `after_create`) dès
l'enregistrement de `models.py`, avant la migration. Les colonnes et le remplissage viennent bien
du script. Contrôle SQL : `trg_activities_modifie_le` et `trg_stays_modifie_le` présents.

Tests catalog (étape 2 + 2-bis) :

```text
PS services\catalog> ..\..\.venv\Scripts\python -m pytest -p no:warnings -q
88 passed in 1.69s
PS> ... -q tests\test_export_interne.py tests\test_pre_etiquetage.py tests\test_tags_ia.py
51 passed in 0.56s        # étape 2 inchangée
PS> ... -q tests\test_lieux.py tests\test_transport_interne.py
37 passed in 0.85s        # étape 2-bis
```

Un échec au premier lancement, signalé tel quel : `test_vols_jamais_complets_ni_sous_capacite`
attendait ZZ1 avant ZZ3. Le tri par pertinence (même jour, même nombre d'escales, puis prix) place
correctement ZZ3 (80 DT) avant ZZ1 (100 DT). C'est l'attente du test qui était fausse : je l'ai
corrigée, pas le code.

Tests ai :

```text
PS services\ai> ..\..\.venv\Scripts\python -m pytest -p no:warnings -q
64 passed in 0.42s        # 55 de l'étape 1 + 9 nouveaux
```

Collecte réelle des aéroports. Premier essai **en échec** sur le serveur par défaut :

```text
→ Aéroports à code IATA (Tunisie)...
WARNING Overpass : erreur réseau (ConnectError) — nouvelle tentative dans 10 s  (… 30 s, 60 s)
  ✗ aéroports : échec après 4 essais : erreur réseau (ConnectError)
```

`overpass-api.de` refusait la négociation TLS depuis ce poste (curl code 35, PowerShell « connexion
fermée »), alors que `openstreetmap.org` et `pypi.org` répondaient. Relance sur le miroir public
`maps.mail.ru` (listé sur le wiki OSM), via `OVERPASS_URL` déjà configurable :

```text
PS> $env:OVERPASS_URL = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
PS> ..\..\.venv\Scripts\python scripts\collecter_pois.py --aeroports
  DJE  Aéroport international de Djerba-Zarzis -> Djerba
  MIR  Aéroport international de Monastir Habib-Bourguiba -> Monastir
  NBE  Aéroport international d'Enfida -> Sousse
  TOE  Aéroport International de Tozeur - Nefta -> Tozeur
  TUN  Aéroport international de Tunis–Carthage -> Tunis
  5 POI : 5 insérés, 0 mis à jour
Base voyara_ai : 1035 POI sur 8 villes.
=== relance ===
WARNING Overpass : HTTP 504 — nouvelle tentative dans 10 s
  5 POI : 0 insérés, 5 mis à jour
Base voyara_ai : 1035 POI sur 8 villes.
```

Contrôle SQL : `doublons = 0` sur `source_id`, 1 035 POI. Les 5 aéroports sont des contours
(`way/…`).

Appels réels au service catalog en cours d'exécution :

```text
stays/export total 27 | exemple : {'nom': 'Hôtel Les Dunes de Midoun', 'ville': 'Djerba', 'prix_nuit': 320.0, 'equipements': ['piscine', 'plage privée', …]}
vols Paris->DJE 2026-10-24 ±1 j, 2 pax : total 9 | directs 6 | 1 escale 3
   TU821 2026-10-24T11:00:00+02:00 -> 2026-10-24T12:55:00+01:00 175 min 1448.0 DT escales 0
   TU711 + UG105 2026-10-24T10:15:00+02:00 -> 2026-10-24T19:45:00+01:00 630 min 1556.0 DT escales 1
voitures DJE auto 4 j : 0 []          # exact : l'agence de l'aéroport n'a que des boîtes manuelles
voitures ville Djerba 4 j : 9
transferts DJE->Midoun 4 pax 4 bagages : 2 [('van', 120.0, '2026-10-24T10:00:00'), ('minibus', 220.0, …)]
airports 14
lieu inconnu -> 404 {'success': False, 'detail': 'Lieu inconnu : Atlantide'}
sans cle -> 401
via gateway -> 404                    # /internal reste bloqué par le gateway
```

Non-régression de l'étape 2 sur le service réel : `/internal/activities/export` → 117 activités,
champs IA présents ; `pre_etiqueter.py` produit ses 117 propositions (Marche `{'1': 57, '2': 57,
'3': 3}`). Routes publiques `/api/v1/offres/{voitures,transferts,sejours,vols}` : 200, avec les
nouveaux champs de lieu ; `seed_offres_voyage_demo.py --verifier` : données valides.

## 5. Métriques

Jeu de données : catalogue de démonstration (seed du 19/10/2026) : 27 séjours, 632 vols sur 28 jours
(18 lignes réelles, horaires et prix inventés), 35 voitures, 32 transferts, 14 aéroports.

| Mesure | Valeur |
|---|---|
| Lignes conservées par la migration | 27 / 632 / 35 / 32 (100 %) |
| Libellés de lieu résolus par `deduire_lieu` | **99 / 99** (35 voitures + 2 × 32 transferts) ; 23 voitures et 31 transferts liés à un aéroport |
| POI aéroport insérés / doublons à la relance | 5 / 0 (TUN, DJE, MIR, NBE, TOE ; Sfax, Gafsa… ignorés, > 60 km d'une ville couverte) |
| Tests | catalog 88 (51 + 37), ai 64 (55 + 9), tous verts |
| Latence `/internal/flights/search` (196 appels, `127.0.0.1`) | **p50 24 ms, p95 40 ms** |
| Même appel via `localhost` | **~2 100 ms** (résolution IPv6 `::1` d'abord, voir §6) |

Apport des correspondances sur l'horizon de 28 jours (classe économique, une requête par jour) :

| Trajet | Jours avec un direct | Jours avec ≥ 1 offre | Itinéraires |
|---|---:|---:|---:|
| Paris → Djerba | 27 | 27 | 58 |
| Lyon → Djerba | 0 | **12** | 12 |
| Bruxelles → Djerba | 0 | **11** | 11 |
| Genève → Tunis | 0 | **4** | 4 |
| Rome → Tozeur | 0 | 0 | 0 |
| Tunis → Djerba | 27 | 27 | 97 |
| Paris → Monastir | 8 | 8 | 8 |

Rome → Tozeur reste à 0, ce qui est correct : le seul Tunis → Tozeur part à 09:30 alors que le vol
de Rome arrive l'après-midi (attente > 8 h). Le 28ᵉ jour (17/11) est vide partout : le seed, lancé
le 19/10, a généré des vols jusqu'au 16/11 ; relancer `seed_offres_voyage_demo.py` prolonge
l'horizon.

## 6. Limites, dette technique, risques

- **Pas de stock de voitures par date** : `disponible` est un simple booléen (aucune réservation de
  voiture n'existe). Deux voyageurs peuvent se voir proposer la même voiture.
- **Pas d'aller simple en voiture** : retour dans la ville de prise uniquement.
- **Transferts directionnels** : seuls 3 trajets vers un aéroport existent dans le seed
  (Hammamet → Tunis-Carthage, Sousse → Tunis-Carthage, Tozeur → Djerba-Zarzis) ; aucun hôtel de Djerba → aéroport, donc pas de transfert retour à proposer au
  scénario Djerba.
  Sous-tâche « compléter le seed » ouverte dans le plan.
- **Pas d'horaire de transfert** : `arrivee_estimee` = prise en charge + durée ; la majoration de
  nuit écrite dans les descriptions n'est pas appliquée.
- **Correspondances limitées à 1 escale**, même classe, sans billet combiné réel (deux tronçons
  vendus séparément). L'agent devra le dire.
- **Tri `depart`** : comparaison des chaînes ISO, imprécise quand les fuseaux d'origine diffèrent
  (le tri par défaut `pertinence` n'est pas concerné).
- **Colonnes de lieu non visibles dans l'admin** : déduites du libellé ; un libellé nouveau et
  inhabituel donnerait une ville vide (la migration et les tests les listent). Sous-tâche ouverte.
- **`NBE` rattaché à Sousse côté ai, à Enfidha côté catalog** : sans conséquence (rapprochement par
  IATA), mais à connaître.
- **Overpass** : le serveur par défaut était injoignable depuis ce poste ; le miroir utilisé n'est
  pas configuré par défaut (`OVERPASS_URL` à exporter pour relancer).
- **Risque transverse découvert** : toutes les URL inter-services sont en `localhost`, ce qui coûte
  ~2 s par appel sous Windows (IPv6 tenté d'abord). Cela touche déjà le gateway, et touchera chaque
  outil de l'agent. Noté dans architecture.md §12 n° 13, à traiter à l'étape 3 (`127.0.0.1`).
- **Ports et gares** non collectés : aucune offre ne les utilise (bac de Djerba, trains : perspective).

## 7. À vérifier par moi

1. `git checkout ia/etape-02bis`, conteneurs `postgres` et `postgres-ai` démarrés.
2. `cd services\catalog ; ..\..\.venv\Scripts\python scripts\add_transport_ia.py` → « Tous les
   libellés sont résolus » et les 4 comptes inchangés (relance : « 0 voiture(s), 0 transfert(s) »).
3. `..\..\.venv\Scripts\python -m pytest -q` → `88 passed` ; dans `services\ai` → `64 passed`.
4. Swagger `http://127.0.0.1:8002/docs`, section « Offres de voyage — moteur IA (interne) » :
   essaie `/internal/flights/search` avec l'en-tête `X-Internal-Api-Key` (valeur de ton `.env`),
   `origine=Lyon`, `destination=DJE`, une date de samedi, `tolerance_jours=1`, `nb_passagers=2` :
   tu dois voir une correspondance via Tunis, avec `attente_min` entre 60 et 480.
5. Même route **sans** l'en-tête → 401 ; avec une mauvaise clé → 403 ;
   `http://localhost:8000/internal/stays/export` (gateway) → 404.
6. `/internal/car-rentals/search?lieu_prise=TUN&prise_le=…&retour_le=…` : seules les voitures de
   l'agence « Aéroport Tunis-Carthage » ; `prix_total = prix_jour × nb_jours`.
7. Admin : modifie une voiture (n'importe quel champ) puis vérifie en base que `ville` et
   `aeroport` sont toujours remplis.
8. `docker exec voyara-postgres-ai-1 psql -U <utilisateur> -d voyara_ai -c "select tags->>'iata', ville from pois where type='aeroport'"`
   → 5 lignes.
9. Relis l'avenant de l'ADR-007 (architecture.md, fin de l'ADR) et le schéma « Flux du moteur IA ».

## 8. Étape suivante recommandée

**Étape 3 — Service `ai` et couche LLM hybride** (`ia/etape-03`) : scaffold :8008, gateway
`/api/ai`, `LLMProvider` Claude / Ollama (Ollama seul suffit sans clé), `llm_appels`, et le **client
catalog** (`ServiceClient`) branché sur les 5 routes de cette étape, avec timeouts et erreurs
typées. Prérequis :
- utiliser `http://127.0.0.1:8002` (et non `localhost`) pour le client catalog ;
- garder en tête la validation humaine des tags (0 / 117), toujours ouverte depuis l'étape 2, qui
  conditionne les étapes 5 à 7.
