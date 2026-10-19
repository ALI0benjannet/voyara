# Étape 01 (sous-tâche) — Offres de voyage, nouvelles catégories et photos

> Date : 2026-10-19 · Branche : `seed/offres-voyage` · Module(s) : 2 (données), prépare le module 5 (budget)
> Complète les sous-tâches [seed du catalogue](etape-01-seed-catalogue.md) et
> [photos du catalogue](etape-01-photos-catalogue.md). L'étape 2 (enrichissement sémantique) est
> **reportée à la demande de l'étudiant** jusqu'à ce que ces données existent.

## 1. Objectif

Les tables `stays`, `flights`, `car_rentals` et `transfers` du service catalog existaient mais étaient
**vides** (0 ligne chacune). Or le module 5 du moteur IA doit chiffrer un séjour complet :
hébergement + activités + déplacements. Demandes de l'étudiant :
1. remplir séjours, vols, voitures et transferts avec des exemples réalistes ;
2. couvrir les trois profils de voyageurs : **solo, couple, famille** ;
3. ajouter les catégories d'activités jugées utiles ;
4. ajouter **les photos en même temps** ;
5. supprimer la catégorie de test « sahra » et l'activité de test « touzer ».

Critère de « fini » retenu : données validées par les schémas de l'API admin, script idempotent
(une relance ne crée rien), photos sous licence libre créditées, données visibles dans l'admin.

## 2. Réalisé

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `services/catalog/scripts/seed_offres_voyage_demo.py` | créé | Seed idempotent : 27 séjours, 632 vols générés à partir de 18 lignes, 35 voitures, 32 transferts, 40 photos ; modes `--verifier` et `--telecharger` |
| `services/catalog/scripts/seed_catalogue_demo.py` | modifié | 3 catégories créées automatiquement avec leurs traductions (Bien-être, Famille & loisirs, Golf) + 21 activités (107 au total) ; tableau de répartition élargi |
| `services/catalog/scripts/seed_photos_demo.py` | modifié | 21 photos de plus (107) ; largeur de repli 640 px pour les images trop lourdes |
| `services/catalog/static/offres/demo/*.jpg` | créé | 40 photos (27 séjours, 13 modèles de voiture), 11,7 Mo, versionnées |
| `services/catalog/static/activities/demo/*.jpg` | créé | 21 photos des nouvelles activités, 5,3 Mo |
| `services/catalog/static/activities/1-b330….png` | supprimé | Photo de l'activité de test « touzer » |
| `frontend/apps/client/src/app/credits/photo-credits.json` | modifié | Crédits (auteur, licence, source) des 61 nouvelles photos ; 153 entrées au total |
| `frontend/apps/client/src/app/credits/page.tsx` | modifié | Le texte d'introduction couvre « activités, séjours et voitures » |
| `gateway/app/main.py` | modifié | Route `/static/offres` → catalog (avant la route `/static` d'auth) |
| `frontend/apps/admin/src/features/travel/config.ts` | modifié | Format de colonne `image` ; colonne photo pour séjours et voitures |
| `frontend/apps/admin/src/pages/TravelOffersPage.tsx` | modifié | Rendu d'une vignette pour le format `image` |
| `frontend/packages/i18n/src/locales/{fr,en,ar}/common.json` | modifié | Libellé « Photo » des deux tableaux + noms des 3 nouvelles catégories, en fr / en / ar |
| `RUN.md` | modifié | Commande du nouveau seed dans l'installation d'un poste |
| `docs/architecture.md` | modifié | Table de routage : `/static/offres/*` → catalog |
| `docs/plan.md`, `docs/ia/journal.md`, `docs/ia/README.md` | modifié | Sous-tâche cochée, ligne de journal, index des rapports |

**Données modifiées hors du code** (bases locales, après sauvegarde, voir §4) : suppression de la
chaîne de test « touzer » dans 4 bases, puis écriture des seeds dans `voyara_catalog`.

## 3. Choix techniques

| Décision | Option retenue | Alternatives envisagées | Pourquoi écartées |
|---|---|---|---|
| Noms des séjours et agences | **Noms fictifs** (« Houch Yasmina », « Voyara Location — Aéroport Djerba-Zarzis ») posés sur de **vraies zones** (coordonnées OSM) | Vrais hôtels tirés d'OSM | Prix, équipements et disponibilités inventés attribués à une entreprise réelle = fausse information, présentée devant un jury. Le seed des activités suit déjà la règle « aucun nom d'entreprise inventé ni détourné ». |
| Vols | **Vraies compagnies (Tunisair, Tunisair Express, Nouvelair, Transavia) et vrais aéroports**, numéros, horaires, prix et remplissage inventés | Compagnie fictive | Les lignes aériennes sont des faits publics ; une « Air Fictif » sonnerait faux. Les numéros restent signalés comme démo dans le script. |
| Volume des vols | **Génération** à partir de 18 lignes × jours de la semaine sur 28 jours (632 vols, dont 136 en business) | Liste écrite à la main | Même horizon que les créneaux d'activités ; relancer le script prolonge l'horizon sans doublon. |
| Heure d'arrivée | Calcul du **décalage horaire** (Tunisie UTC+1 ; Europe UTC+2 jusqu'au dernier dimanche d'octobre) | Ignorer les fuseaux | Sans ce calcul, un Paris → Tunis du 20/10 arriverait 1 h trop tard sur le papier. Le changement d'heure du 25/10/2026 tombe dans l'horizon. |
| Prix et places des vols | **Bruit déterministe** (CRC32 du numéro et de la date) : +15 % le week-end, ±6 %, 20 à 70 % des places vendues | Aléatoire | Reproductible d'un poste à l'autre, donc mêmes chiffres pour les tests et l'évaluation. |
| Profils solo / couple / famille | Champ `profils` dans le seed et **contrôle par zone** dans `--verifier` ; la capacité, les équipements et la description suivent le profil | Nouvelle colonne `public` dans `stays` | Il faudrait une migration et l'étape 2 doit justement décider du stockage des attributs de public (pour les activités). Le contrôle garantit la couverture dès maintenant. |
| Validation | Chaque ligne passe par **`StayIn` / `FlightIn` / `CarRentalIn` / `TransferIn`** de l'API admin | Contrôles maison | Ce que le seed écrit reste modifiable depuis l'admin sans erreur 422 (vérifié par un PUT, §4). |
| Nouvelles catégories | **Bien-être, Famille & loisirs, Golf** | Nature, Shopping, Vie nocturne, parcs aquatiques | Nature et Shopping recoupent Aventure et Culture ; trop peu de lieux vérifiables dans les 5 zones. Parcs aquatiques **fermés** sur l'horizon des créneaux (octobre-novembre). Bien-être : la Tunisie est une grande destination de thalasso, absente du catalogue. Famille : utile au scénario 1 de la démo (« famille »). Golf : parcours réels dans 4 zones sur 5. |
| Lieux des nouvelles activités | **Géocodés par Nominatim** (OSM, 19/10/2026), uniquement les lieux trouvés | Coordonnées approximatives | Overpass était saturé (502, 504, délai dépassé sur les 5 zones, voir §4). Nominatim a confirmé Hannibal Park, zoo du Belvédère, Cité des sciences, Friguia Park, Chak Wak, Eden Palm, zoo du désert de Tozeur et 4 golfs. |
| Thalasso et hammams | Point de rendez-vous = **zone touristique**, sans nom d'hôtel | Nommer le centre | Les centres de thalasso sont dans des hôtels réels : même règle que pour les séjours. |
| Photos | **Wikimedia Commons**, licence lue par l'API (CC0 / domaine public / CC BY / CC BY-SA), **chaque image vérifiée à l'œil** sur planche contact | Photos d'hôtels identifiés, banques d'images | Écartées : une photo des Berges du Lac avec une enseigne de marque, un fourgon Trafic sans vitres, des photos d'hôtels nommés (El Mouradi, RIU) pour des séjours fictifs. Certaines photos d'activités sont des **illustrations** (thalasso, massage, yoga, golf de Djerba) : commentaire `# illustration` dans le script, comme pour le seed précédent. |
| Stockage des photos | `static/offres/demo/` + route gateway `/static/offres` | Les ranger dans `static/activities/` | Le chemin aurait menti sur le contenu. Le catalog sert déjà tout `static/` : une ligne de gateway suffit. |
| Une photo par modèle de voiture | 13 photos pour 35 voitures | Une par voiture | Même modèle = même photo : c'est ce que montrent les vrais loueurs. |
| Suppression de « touzer » | **Toute la chaîne** : paiement simulé, réservation, favori, créneau, activité, photo, puis catégorie « sahra », après `pg_dump` des 4 bases | Supprimer seulement l'activité et la catégorie | « touzer » avait 1 réservation confirmée (compte 20, paiement `simulation` `mock_…`) et 1 favori. L'activité seule aurait laissé une réservation orpheline, et la page Réservations de l'admin aurait affiché une activité introuvable. La route admin de suppression refuse d'ailleurs une activité réservée. |

## 4. Vérification

**Sauvegarde avant suppression** (`pg_dump -Fc`, dossier temporaire de la session) :

```text
voyara_catalog 66156 octets · voyara_booking 7317 · voyara_review 6236 · voyara_payment 7062
```

**Chaîne « touzer » avant suppression** :

```text
activities : 1|touzer|2|/static/activities/1-b330….png|touzer|1 créneau
bookings   : id 1, user_id 20, activity_id 1, statut confirmed, montant_total 700, nb_places 2
payments   : id 1, booking_id 1, montant 700, succeeded, methode simulation, intent mock_64e…
favorites  : id 2, user_id 20, activity_id 1      reviews : 0
```

Après suppression : `OK`, catégories `3 Culture · 4 Mer · 5 Désert · 6 Aventure · 7 Gastronomie`, 96 activités.

**Recherche de lieux** : Overpass a échoué sur les 5 zones (5 essais chacune, `HTTP 502`, `504`,
`read operation timed out`, `WinError 10054`), puis `runtime error: Query timed out` sur la requête
pays entier. Nominatim a répondu ; les lieux introuvables (Aqualand Djerba, Flipper Monastir,
Carthage Land Kantaoui…) ont été écartés.

**Contrôles hors base** (`cd services\catalog`) :

```text
PS> ..\..\.venv\Scripts\python scripts\seed_catalogue_demo.py --verifier
Données valides : 107 activités.
(tableau de répartition reproduit avec des colonnes resserrées)
Zone                     Culture  Mer  Désert  Aventure  Gastronomie  Bien-être  Famille & loisirs  Golf  Total
Djerba                        11    8       2         6            5          3                  0     1     36
Tunis / Sidi Bou Saïd          9    2       0         2            3          2                  2     0     20
Sousse / Monastir              6    4       0         2            2          2                  1     3     20
Hammamet                       5    3       0         2            2          1                  1     1     15
Tozeur                         3    0       5         2            2          1                  3     0     16
Total                         34   17       7        14           14          9                  7     5    107
PS> ..\..\.venv\Scripts\python scripts\seed_photos_demo.py --verifier
Photos valides : 107 fichiers dans …\static\activities\demo.
PS> ..\..\.venv\Scripts\python scripts\seed_offres_voyage_demo.py --verifier
Données valides.
Séjours : 27 · Djerba 6, Tunis / Sidi Bou Saïd 7, Sousse / Monastir 6, Hammamet 4, Tozeur 4
  types : maison_hotes 11, hotel 10, appartement 6
  prix/nuit (DT) : min 95 · médiane 210 · max 560
Vols : 632 sur 28 jours (18 lignes, 136 en business)
Voitures : 35 dans 9 agences, 13 modèles
Transferts : 32
Photos prévues : 40
```

**Téléchargement des photos** : 1er passage 36/40, avec 3 `HTTP Error 429` (quota Commons) et
1 « vignette trop lourde même en 800 px ». La relance a récupéré les 3, puis la photo trop lourde
a été remplacée par la façade d'Ouled El Hadef. Côté activités : 1 × 429 (Chak Wak, récupéré à la
relance) et 1 image trop lourde même en 640 px (piscine de thalasso de Limassol), remplacée par une
piscine de spa générique. Bilan : `0 licence(s) refusée(s), 0 échec(s)` au dernier passage. Les
61 fichiers enregistrés ont été relus à l'œil sur 4 planches contact.

**Écriture en base** :

```text
Catégorie créée : Bien-être / Famille & loisirs / Golf
Horizon des créneaux : 2026-10-20 -> 2026-11-16
Terminé : 21 activité(s) créée(s), 0 traduction(s) complétée(s), 2190 créneau(x) ajouté(s).
Catalogue complet : 117 activité(s) en base.
Terminé : 21 photo(s) reliée(s), 86 activité(s) déjà illustrée(s), 0 absente(s) de la base.
Séjours : 27 créé(s) · Vols : 632 ajouté(s) (2026-10-20 -> 2026-11-16) · Voitures : 35 · Transferts : 32
En base : 27 séjours, 632 vols, 35 voitures, 32 transferts.
```

Les 2 190 créneaux comprennent 1 156 créneaux pour les 21 nouvelles activités (compté en SQL) et
1 034 qui prolongent l'horizon des 86 activités du 11/10 jusqu'au 16/11.

**Idempotence (relance des trois scripts)** :

```text
Terminé : 0 activité(s) créée(s), 0 traduction(s) complétée(s), 0 créneau(x) ajouté(s).
Terminé : 0 photo(s) reliée(s), 107 activité(s) déjà illustrée(s), 0 absente(s) de la base.
Séjours : 0 créé(s), 0 complété(s). · Vols : 0 ajouté(s). · Voitures : 0 créée(s). · Transferts : 0 créé(s).
```

**À travers le gateway** (services démarrés, `/health` 200) :

```text
GET /api/v1/categories → (6 Aventure) (8 Bien-être, Wellness) (3 Culture) (5 Désert)
                         (9 Famille & loisirs, Family & leisure) (7 Gastronomie, Food) (10 Golf) (4 Mer, Sea)
GET /api/v1/activities?category_id=8  → 9 activités, 9 avec photo
GET /api/v1/activities?category_id=9  → 7 activités, 7 avec photo
GET /api/v1/activities?category_id=10 → 5 activités, 5 avec photo
GET /static/offres/demo/houch-yasmina.jpg     → 200 image/jpeg 397771o
GET /static/offres/demo/voiture-duster.jpg    → 200 image/jpeg 287139o
GET /static/activities/demo/initiation-au-golf-a-el-kantaoui.jpg → 200 image/jpeg 308899o
SQL : stays 27 / photos 27 · cars 35 / photos 35 · vols 632 du 2026-10-20 au 2026-11-16 · transferts 32
```

Une recherche texte `search=Bien-être` envoyée depuis Git Bash a renvoyé 0 résultat : le terminal
a mal encodé l'accent (le libellé affiché était `Bien-�tre`). Le filtre par `category_id` ci-dessus
confirme les 9 activités.

**Routes admin des offres** : un jeton fabriqué localement a été refusé par le gateway
(`Identifiants invalides ou token expiré`). Les routes ont donc été appelées en interne avec
`TestClient`, sur la vraie base, en ne remplaçant que la dépendance `require_admin` :

```text
stays 200 27 · flights 200 632 · car-rentals 200 35 · transfers 200 32
PUT d'un séjour (prix + 1), puis PUT de retour au prix initial → « restauré True »
```

Le code HTTP du premier PUT n'apparaît pas dans l'extrait (la ligne a été avalée par un filtre de
logs) ; le second PUT a bien renvoyé le prix d'origine.

**Front** :

```text
PS> cd frontend; npm run typecheck
> @voyara/client@0.0.0 typecheck > tsc --noEmit      (aucune erreur)
> @voyara/admin@0.0.0 typecheck  > tsc --noEmit      (aucune erreur)
```

Non vérifié : l'affichage réel de la colonne photo dans le navigateur (voir §7) et les tests vitest
(aucun test ne couvre ces pages).

## 5. Métriques

**Jeu de données** : seeds versionnés dans `services/catalog/scripts/`, horizon du 20/10 au
16/11/2026, coordonnées OSM / Nominatim du 19/10/2026, photos Wikimedia Commons.

| Offre | Volume | Répartition |
|---|---|---|
| Séjours | 27 | Djerba 6 · Tunis/SBS 7 · Sousse/Monastir 6 · Hammamet 4 · Tozeur 4 ; 10 hôtels (3★ à 5★), 11 maisons d'hôtes, 6 appartements ; 95 à 560 DT la nuit (médiane 210) ; chaque zone couvre solo, couple et famille |
| Vols | 632 | 18 lignes : 4 intérieures (Tunis ↔ Djerba ×3 par jour, Tunis ↔ Tozeur 3 par semaine) et 14 internationales (Paris ×6, Lyon, Marseille, Nice, Rome, Francfort ×2, Bruxelles, Genève) vers TUN, DJE, MIR, NBE, TOE ; 136 en business |
| Voitures | 35 | 9 agences (5 aéroports, 4 en ville), 13 modèles : économique 85-100 DT/j, compacte 120-240, SUV 180-390, van 210-350 |
| Transferts | 32 | 28 au départ d'un aéroport (5 aéroports), 4 entre villes ; taxi, berline, van, minibus ; 15 à 650 DT par véhicule |
| Activités | 107 dans le seed (117 en base) | +9 Bien-être, +7 Famille & loisirs, +5 Golf |
| Photos | 61 nouvelles | 17 Mo au total ; 153 crédits sur `/credits` |

**Ordres de grandeur utilisés** (relevés le 19/10/2026 ; taux de conversion ≈ 3,37 DT pour 1 €,
déduit des deux colonnes de combien-coute.net) :
- hôtel 4★ : environ 350 DT la nuit à Djerba (fourchette 153-805), environ 394 DT à Tozeur —
  [combien-coute.net Midoun](https://www.combien-coute.net/hotel4/djerba/midoun/),
  [Tozeur](https://www.combien-coute.net/hotel4/tunisie/tozeur/) ;
- Tunis ↔ Djerba : environ 1 h de vol, jusqu'à 7 vols par jour en saison en Tunisair Express —
  [African Manager](https://africanmanager.com/tunisair-express-programme-7-vols-quotidiens-entre-tunis-et-djerba/),
  [Trip.com](https://fr.trip.com/flights/airport-tun-dje/) ; aller-retour à partir d'environ 80 €
  ([Liligo](https://www.liligo.fr/vol-tunis-djerba_tun-dje.html)) ;
- taxi depuis l'aéroport de Djerba : environ 30 DT vers Houmt Souk, 50-70 DT vers la zone
  touristique, majoration de nuit — [Airmundo](https://airmundo.com/en/djerba-airport/taxi/),
  [cestee.fr](https://www.cestee.fr/aeroport/djerba-dje/acces) ;
- location d'une citadine : 65 à 140 DT par jour selon la saison, Kia Picanto environ 35 à 53 €
  par jour — [Expat.com](https://www.expat.com/fr/forum/afrique/tunisie/tunis/1024027-location-voiture.html),
  [VIP Cars](https://www.vipcars.com/car-rental/tunisia/tunis/tunis-airport?viplang=fr),
  [Carigami](https://www.carigami.fr/louer-tunisie.html).

Ce ne sont pas des tarifs officiels. Les prix du seed se placent volontairement dans le bas ou le
milieu de ces fourchettes (octobre-novembre = moyenne saison).

## 6. Limites, dette technique, risques

- **Données de démonstration** : noms d'hôtels et d'agences fictifs ; numéros, horaires et prix des
  vols inventés. À présenter comme tels au jury.
- **Deux photos d'hébergement montrent un vrai hôtel non identifié** : la piscine de « Hôtel Les
  Dunes de Midoun » et les bâtiments de « Hôtel Jardins de Yasmine » (médina de Yasmine). Aucune ne
  porte de nom d'hôtel. Les remplacer si l'on veut zéro ambiguïté.
- **Illustrations** : 9 photos d'activités nouvelles montrent le même type d'activité ailleurs
  (thalasso en France, en Pologne ou en Algérie ; massage ; yoga ; golf de Monastir pour Djerba).
- **Le site client n'affiche pas encore les offres** : les 4 pages restent « Bientôt disponible »
  et les routes `/stays`, `/flights`… sont réservées aux admins. Les données ne sont visibles que
  dans l'admin. Une route publique (ou interne pour le service `ai`) sera nécessaire au module 5.
- **Pas de colonne de profil** (solo / couple / famille) dans `stays` : l'information n'existe que
  dans le seed et dans le texte. L'étape 2 tranchera le stockage des attributs de public.
- **Transferts et voitures sans traduction** : les tables n'ont pas de colonnes `_en` / `_ar` ;
  les descriptions de transferts sont en français seulement.
- **L'admin charge tous les vols d'un coup** (632 lignes, pas de pagination côté API) : acceptable
  aujourd'hui, à paginer si l'horizon grandit.
- **La page `/credits` est en français en dur** (dette existante, non i18n).
- **Poids du dépôt** : +17 Mo de photos versionnées (choix assumé depuis la sous-tâche photos :
  aucun téléchargement nécessaire sur un autre poste).
- **Sauvegardes dans un dossier temporaire** : les `pg_dump` d'avant suppression sont dans le
  dossier temporaire de la session Claude ; ils ne sont pas garantis dans le temps.
- **Vols et créneaux expirent** : relancer les deux seeds avant une démo pour prolonger l'horizon.

## 7. À vérifier par moi

1. `git switch seed/offres-voyage`, puis démarrer : `docker compose up -d postgres`,
   `.\scripts\dev.ps1`, `cd frontend; npm run dev`.
2. **Redémarrer le gateway** s'il tournait déjà sans rechargement automatique, pour qu'il prenne la
   route `/static/offres`. Ouvrir <http://localhost:8000/static/offres/demo/houch-yasmina.jpg>,
   l'image doit s'afficher.
3. Admin <http://localhost:5174/admin> → **Séjours** : 27 lignes avec vignette. **Vols** : 632.
   **Voitures** : 35 avec vignette. **Transferts** : 32. Ouvrir un séjour, changer le prix,
   enregistrer : aucune erreur.
4. Site client → catalogue : les puces **Bien-être**, **Famille & loisirs** et **Golf** apparaissent ;
   passer en anglais puis en arabe, les noms doivent être traduits (Wellness, العافية والاسترخاء…).
5. Page <http://localhost:5173/credits> : les crédits « Séjour — … » et « Voiture — … » sont listés.
6. Vérifier que la page **Réservations** de l'admin ne contient plus de ligne vers une activité
   introuvable (la réservation de test n° 1 a été supprimée).
7. Idempotence : `cd services\catalog; ..\..\.venv\Scripts\python scripts\seed_offres_voyage_demo.py`
   doit afficher `0 créé(s)` partout.
8. Si une photo te gêne, remplace son fichier Commons dans le script, supprime le `.jpg` local, puis
   lance `--telecharger` puis le mode normal.

## 8. Étape suivante recommandée

**Étape 2 — Enrichissement sémantique du catalogue**, sur `ia/etape-02`, avec le plan déjà proposé
(attributs IA dans catalog, `/internal/activities/export`, pré-étiquetage LLM, validation admin).
Elle portera désormais sur 117 activités et 8 catégories. Deux ajouts à prévoir :
- décider si les attributs de public (solo / couple / famille) s'appliquent aussi aux séjours ;
- prévoir un endpoint interne d'export des offres (séjours, transferts, vols) pour le module 5.

Prérequis inchangé : une `ANTHROPIC_API_KEY` dans `services/catalog/.env` pour le pré-étiquetage réel.

---

### Addendum du 2026-10-19 — offres visibles sur le site client

**Constat de l'étudiant** : « je ne vois aucun changement sur la page client ». C'était la limite
signalée au §6 : les 4 pages affichaient `ComingSoon` et seules les routes admin pouvaient lire
les offres.

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `services/catalog/app/offres_routes.py` | créé | `GET /api/v1/offres/{sejours,vols,voitures,transferts}` publics, lecture seule : séjours actifs, voitures disponibles, transferts actifs, vols à plus de 3 h avec des places (200 au plus) ; filtres ville, type, catégorie, aéroports, date |
| `services/catalog/app/main.py` | modifié | Enregistre `offres_router` |
| `gateway/app/main.py` | modifié | Préfixe `/api/v1/offres` → catalog |
| `frontend/apps/client/src/features/offres/api.ts` | créé | Types des 4 offres + nom et description traduits des séjours (repli français) |
| `frontend/apps/client/src/lib/server-api.ts` | modifié | `fetchStays`, `fetchFlights`, `fetchCarRentals`, `fetchTransfers` (SSR, revalidation 60 s, panne = liste vide) |
| `frontend/apps/client/src/components/offres/OffresLayout.tsx` | créé | Gabarit commun, puces de filtre en liens, badge « Réservation en ligne bientôt » |
| `frontend/apps/client/src/components/offres/OffreCards.tsx` | créé | Cartes séjour, voiture, transfert et vol (heures locales, places restantes) |
| `frontend/apps/client/src/app/{stays,flights,car-rentals,transfers}/page.tsx` | modifié | Les pages « Bientôt disponible » deviennent des listes rendues côté serveur avec filtres |
| `frontend/apps/client/src/components/layout/ComingSoon.tsx` | supprimé | Plus utilisé |
| `frontend/packages/i18n/src/locales/{fr,en,ar}/common.json` | modifié | Bloc `offres` (33 clés, pluriels inclus) ; types réutilisés depuis `admin.travel.options.*` |
| `docs/architecture.md` | modifié | Table de routage : `/api/v1/offres/*` |

**Choix** : routes publiques **séparées** sous `/offres` plutôt que d'ouvrir les `GET` admin
existants. Les routes admin listent aussi les offres inactives et restent protégées. Le préfixe
séparé évite aussi le conflit avec `/stays/{item_id}`. Pas de bouton « Réserver » : les offres ne
sont pas branchées au tunnel booking + paiement, d'où un badge honnête « Réservation en ligne
bientôt ».

**Vérification** :

```text
GET /api/v1/offres/sejours → 27 · ?ville=Djerba → 6 · vols?depart=TUN&arrivee=DJE → 84
    voitures?ville=Tozeur → 3 · transferts?depart=Aéroport Djerba → 8
PS> npm run typecheck   → @voyara/client tsc --noEmit · @voyara/admin tsc --noEmit (aucune erreur)
PS> npm run test        → Test Files 1 passed (1) · Tests 4 passed (4)
Pages rendues par le serveur Next (curl sur :5173, code 200) :
/stays                         Houch Yasmina ✓  Hôtel Gammarth Horizon ✓  27 badges
/stays?ville=Djerba            6 badges
/flights?depart=TUN&arrivee=DJE  UG101 ✓  84 badges
/car-rentals?ville=Tozeur      Land Cruiser ✓  3 badges
/transfers?depart=Aéroport Djerba  8 badges
« Bientôt disponible » : 0 occurrence sur les 5 pages
```

Non vérifié : le rendu visuel dans un navigateur, en particulier le sens droite-à-gauche en arabe.

**Limites ajoutées** : sans filtre, la page Vols affiche les 200 prochains vols (sur 632) ; pas de
page de détail par offre ; descriptions des transferts et équipements des séjours en français
seulement (pas de colonnes de traduction).

### Addendum 2 — navigation toujours visible

**Constat de l'étudiant** : sur `/activities`, la rangée d'onglets (Séjours, Vols…) disparaissait.
`useCondensedHeader` condensait l'en-tête d'emblée sur le catalogue, et après 320 px sur l'accueil,
en supprimant la navigation.

**Correction** : la navigation principale est rendue sur **toutes les pages, à tout moment**.
Au défilement (> 96 px, sur toutes les pages), c'est la rangée « Espace voyageur / Espace
prestataire » qui se replie : animation `grid-template-rows`, désactivée si l'utilisateur a demandé
moins d'animations (`motion-reduce`), et rangée `inert` une fois repliée pour qu'elle ne soit plus
atteignable au clavier. L'onglet reste actif sur les sous-pages (`/activities/2` → Activités), avec
`aria-current="page"` et une `<nav aria-label>`. La recherche reste dans l'en-tête sur l'accueil et
le catalogue. Fichiers : `features/layout/use-condensed-header.ts`, `components/layout/Navbar.tsx`,
commentaire de `components/home/HeroSearch.tsx`.

**Vérification** : `npm run typecheck` sans erreur, `npm run test` 4/4. HTML rendu (curl :5173) :
`/activities`, `/stays`, `/activities/2` et `/` contiennent la `<nav aria-label="Menu">` avec le bon
onglet en `aria-current`. La recherche est présente sur `/` et `/activities` seulement. Le repli au
défilement n'a pas été vérifié dans un navigateur.

### Addendum 3 — saccade de l'en-tête au défilement

**Constat de l'étudiant** : léger à-coup de la barre en faisant défiler la page.
**Causes** : (1) le repli animait `grid-template-rows`, donc la hauteur de l'en-tête sticky. Le
navigateur recalculait la mise en page à chaque image et le contenu remontait de ~50 px.
(2) Le seuil unique de 96 px pouvait faire osciller l'état : quand l'en-tête rétrécit, la position
de défilement change.
**Correction** : la rangée 0 a une hauteur fixe (`h-14`) et l'en-tête entier glisse de
`-translate-y-14`. L'animation se fait par `transform`, prise en charge par le compositeur, sans
recalcul de mise en page ni décalage du contenu. Ajout d'une **hystérésis** : repli au-delà de
96 px, redéploiement seulement sous 32 px. Les menus (compte, langue, recherche) n'utilisent ni
`position: fixed` ni portail, donc le `transform` ne les déplace pas (vérifié par grep).
**Vérification** : typecheck sans erreur, vitest 4/4, `/activities` rendu en 200 avec les nouvelles
classes de l'en-tête et la `<nav>`. La fluidité elle-même ne se mesure que dans un navigateur : à
confirmer par l'étudiant.

### Addendum 4 — accueil, admin et recherche dans l'admin

**Demande** : améliorer l'accueil et l'admin, et ajouter une recherche (nom, ville, catégorie…) dans
les listes admin.

**Problèmes trouvés avant de coder** :
- admin Activités : seule la page 1 de 50 était demandée → **67 activités sur 117 invisibles** ;
  ni recherche ni pagination ;
- admin Séjours / Vols / Voitures / Transferts : aucune recherche, 632 vols dans une seule liste ;
- tableau de bord : textes français en dur (« Actualiser », « sur 30 jours »…, contraire à la règle
  i18n), aucune donnée sur les offres ni sur la modération ;
- accueil : la carte **Tabarka** menait à une page vide (aucune offre) ; les « activités
  populaires » étaient les 4 dernières créées, pas les mieux notées ; les nouvelles catégories et
  les offres n'apparaissaient nulle part.

| Fichier | Rôle du changement |
|---|---|
| `services/catalog/app/routers.py` | `/internal/activities` : `search` (titre fr/en/ar, ville, catégorie), `category_id`, `statut`, renvoie `photos` ; `/internal/stats/activities` : activités `en_attente`, `par_categorie`, compteurs des 4 offres |
| `services/catalog/app/offres_routes.py` | `/offres/vols` : paramètre `limite` (1-1000, 200 par défaut) |
| `services/admin/app/{main,aggregator,schemas}.py` | Le BFF fait suivre les filtres au catalog (la pagination reste juste) ; schémas étendus avec des valeurs par défaut |
| `frontend/apps/admin/src/components/ListToolbar.tsx` | Créé : recherche temporisée (300 ms), filtres, compteur « x sur y », pagination |
| `frontend/apps/admin/src/pages/AdminActivitiesPage.tsx` | Recherche + filtres catégorie et statut côté serveur, 20 par page, vignette et badge de statut |
| `frontend/apps/admin/src/pages/TravelOffersPage.tsx`, `features/travel/config.ts` | Recherche multi-mots sans accents (« djerba suv »), filtre par type, classe, catégorie ou véhicule, 25 par page (côté navigateur, listes déjà chargées) |
| `frontend/apps/admin/src/pages/DashboardPage.tsx` | Textes passés en i18n, cartes cliquables, alerte de modération, 4 cartes « Offres de voyage », barres « Activités par catégorie » |
| `frontend/apps/client/src/app/page.tsx` | Accueil : raccourcis vers les 4 offres avec chiffres réels, Hammamet remplace Tabarka, compteurs par région, « Explorer par envie » (8 catégories), populaires classées par avis (repli : une par catégorie), « Séjours coups de cœur » (un par région) |
| `frontend/apps/client/src/components/home/CategoryTiles.tsx` | Créé : tuiles de catégorie (nom traduit depuis la base) |
| `frontend/apps/client/src/lib/server-api.ts` | `fetchAllActivities` (parcourt les pages de 100), `limite` pour les vols |
| `frontend/packages/i18n/.../{fr,en,ar}/common.json` | Clés `home.*`, `admin.list.*`, `admin.activities.*`, `admin.dashboard.*` (aller-retour JSON vérifié identique avant écriture) |

**Vérification** :

```text
npm run typecheck → client et admin : tsc --noEmit sans erreur · npm run test → 4 passed (4)
GET / (Next :5173) → 200 ; présents : « Tout votre voyage », « Dès 95 DT la nuit », « 632 vols directs »,
  « Dès 90 DT par jour », « Dès 15 DT le trajet », « Explorer par envie », « Séjours coups de cœur » ;
  régions : 22 activités · 7 séjours / 37 · 6 / 17 · 4 / 15 · 4 ; « Tabarka » : 0 occurrence
BFF admin (TestClient, dépendance admin remplacée, vrais services) :
  /admin/activities → total 117, 6 pages · search=djerba → 37 · category_id=10 → 5 · page 6 → 17 lignes anciennes
  /admin/stats → offres {sejours 27, vols_a_venir 632, voitures 35, transferts 32}, par_categorie trié
```

Remarque : `search=hammam` trouve aussi « Hammamet » (19 résultats), c'est une recherche par
sous-chaîne. Non vérifié : le rendu visuel de l'admin et de l'accueil dans un navigateur. L'image
`assets/Tbarka.png` n'est plus utilisée, elle a été conservée.
