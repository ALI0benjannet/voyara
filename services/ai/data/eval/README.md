# Jeu d'évaluation NLU — module 1 (étape 4)

Demandes de voyage annotées à la main pour mesurer l'extraction de `DemandeVoyage`
(`POST /api/ai/comprendre`). **Aucune donnée personnelle réelle** : textes inventés.

| Fichier | Contenu |
|---|---|
| `nlu_dev.jsonl` | demandes générées du jeu dev (≈ 40 %) : sert à ajuster les prompts, les exemples few-shot et les règles |
| `nlu_test.jsonl` | demandes générées du jeu test (≈ 60 %) : **regardé seulement pour l'évaluation finale** (aucun exemple few-shot n'en provient, un test le vérifie) |
| `demandes_humaines_a_annoter.jsonl` | 130 demandes écrites par l'équipe (`source = humain`), **pré-annotées** depuis la v2 selon ce README (`statut = a_relire`) ; `annotation_equipe` garde l'annotation d'origine (dont les codes `activites` de l'équipe) pour comparaison |
| `brut/demandes_equipe.json` | export de l'équipe, **v2** (130 objets, JSON valide) : demandes 1 à 100 aux textes inchangés + 30 nouvelles (101 à 130) centrées sur des activités ; champ `activites` (codes normalisés) ajouté, `notes` retiré. La v1 (100 objets) avait d'abord été un module TypeScript (`export const INITIAL_DATA: VoyaraItem[] = [...]`), converti en JSON le 09/11/2026 ; elle reste dans l'historique Git (commit `37c6d6b`) |
| `nlu_demandes.jsonl` | généré par `scripts/evaluer_nlu.py` (toutes les demandes retenues, avec leur jeu) : ne pas éditer |

**Composition** (09/11/2026, demandes équipe v2) : **192 demandes** = 130 `humain` + 62 `genere` ;
≥ 20 en arabe ou darija ; ≥ 25 avec transport ; dans le test, ≥ 70 % hors Djerba. Les scores sont
publiés séparément pour `humain` et `genere`.

**Relecture (toutes les demandes, humaines et générées)** : en équipe, avec un fichier Excel par
relecteur (`docs/ia/relecture/relecture_<nom>.xlsx`, 40 demandes chacun, stratifié par langue) :

```powershell
cd services\ai
..\..\.venv\Scripts\python scripts\generer_relecture.py               # crée les 4 fichiers (refuse d'écraser)
..\..\.venv\Scripts\python scripts\importer_relecture.py              # simulation : incohérences, lignes non relues
..\..\.venv\Scripts\python scripts\importer_relecture.py --appliquer  # écrit statuts et corrections dans les JSONL
..\..\.venv\Scripts\python scripts\accord_annotateurs.py              # accord équipe / jeu → docs/ia/resultats/
```

`statut` passe de `a_relire` à `valide` (tout est juste) ou `corrige` (au moins un champ modifié) ;
`relu_par` et `commentaire_relecture` sont ajoutés à l'import. **Seules les lignes `valide` ou
`corrige` entrent dans l'évaluation.** Les champs dérivés (`budget_total_dt`, `champs_manquants`)
sont recalculés à l'import, jamais saisis. Le champ `a_trancher` signale un cas que la règle ne
tranche pas (ex. « je » sans « seul ») ; il disparaît quand la ligne est relue.

**Répartition des demandes humaines** : laisser `"jeu": null`. Le script les répartit de façon
déterministe (graine fixe, stratifiée par langue) : 40 % dev, 60 % test. Pour forcer un jeu,
mettre `"dev"` ou `"test"`.

## 1. Format (une demande JSON par ligne, UTF-8)

```json
{"id": "H-001", "source": "humain", "jeu": null, "date_reference": "2026-11-09", "statut": "a_relire",
 "tags": ["transport"], "texte": "…",
 "attendu": {
   "destination": "Monastir", "autres_villes": [], "date_debut": "2026-12-18",
   "duree_jours": 3, "nb_nuits": 3,
   "budget_montant": 1400, "budget_devise": "TND", "budget_base": "total", "budget_illimite": false,
   "budget_total_dt": 1400,
   "nb_voyageurs": 4, "nb_adultes": 2, "nb_enfants": 2, "type_voyage": "famille",
   "preferences": [], "activites_souhaitees": [],
   "contraintes": {"niveau_marche_max": null, "mobilite_reduite": null, "horaires": null},
   "langue": "fr", "ville_depart": "Tunis",
   "besoins_transport": {"vol": "oui", "voiture": "indifferent", "transfert": "indifferent"},
   "preferences_transport": {"vol_direct": null, "boite_auto": null, "priorite": null},
   "budget_inclut_transport": true, "hors_sujet": false, "champs_manquants": []}}
```

- `id` : `H-NNN` pour l'équipe (NNN = `id` d'origine), `G-NNN` pour les générées. Unique.
- `statut` (toutes les demandes) : `a_relire` · `valide` · `corrige`.
- `a_trancher` (facultatif) : question laissée au relecteur ; `annotation_equipe` (demandes
  humaines) : annotation d'origine, sert au calcul d'accord entre annotateurs.
- `date_reference` : la date « d'aujourd'hui » pour cette demande. Elle sert à résoudre les dates
  relatives et à valider `date_debut`, pour que l'évaluation donne le même résultat quel que soit
  le jour où on la relance.
- `tags` (libres, servent aux analyses) : `transport`, `refus`, `incomplet`, `faute`, `hors_sujet`,
  `hors_catalogue`, `date_relative`, `nuits`, `journee`, `par_personne`, `par_jour`, `devise`,
  `mobilite`, `chiffres_arabes`, `multi_villes`, `budget_illimite`, `fourchette`, `duree_longue`.
- Tous les champs de `attendu` sont **toujours présents** (valeur `null` si inconnue).

## 2. Valeurs autorisées

| Champ | Valeurs |
|---|---|
| `destination` | ville principale (**la première citée**) **du catalogue**, graphie exacte, parmi les 29 villes du moteur IA (`app/villes.py`) : les chefs-lieux des 24 gouvernorats (Tunis, Ariana, Ben Arous, La Manouba, Nabeul, Zaghouan, Bizerte, Béja, Jendouba, Le Kef, Siliana, Sousse, Monastir, Mahdia, Sfax, Kairouan, Kasserine, Sidi Bouzid, Gabès, Médenine, Tataouine, Gafsa, Tozeur, Kébili) + Sidi Bou Saïd, Hammamet, Djerba, Tabarka, Douz ; sinon `null` |
| `autres_villes` | autres villes du catalogue pour le même voyage (circuits), dans l'ordre cité ; les lieux hors catalogue (Chebika, Tamerza, La Goulette…) sont ignorés |
| `ville_depart` | toute ville, graphie canonique française (Tunis, Paris, Lyon, Genève, Londres…) ; `null` si non dite |
| `budget_devise` | code ISO : `TND`, `EUR`, `USD`, `CHF`, `CAD`, `MAD`… |
| `budget_base` | forme d'origine du budget : `total` · `par_personne` · `par_nuit` · `par_jour` ; `null` si pas de montant |
| `budget_illimite` | `true` / `false` |
| `duree_jours` / `nb_nuits` | 1 à 60 / 0 à 60 |
| `type_voyage` | `famille` · `couple` · `solo` · `amis` · `groupe` · `null` |
| `preferences` | thèmes de l'étape 2 : `plage`, `culture`, `histoire`, `nature`, `gastronomie`, `aventure`, `detente`, `shopping`, `nautique`, `desert` |
| `activites_souhaitees` | liste de textes courts (≤ 80 caractères, sans « ; »), tels que dits par le client, dans sa langue ; vocabulaire libre |
| `langue` | `fr` · `en` · `ar` · `darija` |
| `besoins_transport.*` | `oui` · `non` · `indifferent` |
| `preferences_transport.priorite` | `prix` · `confort` · `null` |
| `champs_manquants` | sous-ensemble de `destination`, `duree`, `budget`, `voyageurs`, `ville_depart`, `date_debut` |

## 3. Règles d'annotation

**Principe : on n'annote que ce qui est dit ou déductible sans ambiguïté. On n'invente jamais
un budget, une date ni une ville de départ.**

### Durée : `duree_jours` et `nb_nuits` (règle unique)

- Si les deux sont donnés (« 4 jours / 3 nuits »), on garde les deux.
- **Si un seul est donné, l'autre lui est égal** : « 3 jours » → 3 jours, 3 nuits ;
  « 3 nuits » → 3 jours, 3 nuits.
- Seule exception : une excursion dans la journée (« une journée », « nhar wa7ed », « aller-retour
  dans la journée ») → 1 jour, 0 nuit.
- « une semaine » = 7, « deux semaines » = 14, « week-end » = 2, « un mois » = 30.
- Fourchette (« nhar wala zouz », « 2 ou 3 jours ») → **borne haute**.
- Plus de 14 jours (« un mois ») : annoté tel quel (30). Le schéma accepte **jusqu'à 60 jours** ;
  au-delà de 14, la compréhension ajoute l'avertissement « planning limité à 14 jours », sans
  rejeter la demande (la limite est gérée à l'étape 7).
- Justification : `duree_jours` = journées exploitables par le planning (étape 7), `nb_nuits` =
  nuits facturées par l'hébergement. Dans « 3 nuits », le voyageur arrive le jour 1 et repart le
  matin du jour 4 : 3 nuits payées, 3 journées utiles, le départ n'en est pas une. Dans « 3 jours »,
  compter 3 nuits surestime l'hébergement d'une nuit au pire, ce qui reste prudent : on ne dépasse
  jamais le budget réel. Le sous-estimer ferait dépasser le budget.

### Dates (relatives à `date_reference`)

- Date sans année (« le 15 mars ») → **prochaine occurrence ≥ `date_reference`**.
- « demain » = référence + 1 ; « ce week-end » = samedi de la semaine en cours (la référence
  elle-même si c'est un samedi) ; « vendredi prochain / next Friday » et un jour de la semaine seul
  (« samedi », « نهار الأحد ») = première occurrence **strictement après** la référence ; « la
  semaine prochaine » = lundi de la semaine suivante ; « le mois prochain » = 1er du mois suivant.
- Mois ou saison sans jour (« début juillet », « en décembre », « fi sif ») → `null` : on ne
  choisit pas un jour à la place du voyageur. Si un vol est demandé, la question portera dessus.
- Une heure (« à 18 h ») n'est pas un champ : elle va dans `contraintes.horaires` si elle exprime
  une préférence, sinon elle est ignorée.

### Budget : `budget_montant`, `budget_devise`, `budget_total_dt`

- `budget_montant` = **total pour tout le groupe**, dans la devise dite : « 300 dinars », « 300dt »,
  « 300 DT », « 300 TND », « ٣٠٠ دينار », « 1,5k DT » → 300 / 1 500, devise `TND`.
- Montant sans devise dans un contexte tunisien (« budget 500 ») → `TND`.
- Par personne (« 120 dinars each », « 200 dt l wa7ed », « 60 dt/élève ») × le nombre de
  personnes **concernées** (seulement les élèves si c'est « par élève ») ; par nuit × `nb_nuits` ;
  par jour × `duree_jours` ; « par mois » pour un séjour d'un mois = le montant. Si le
  multiplicateur est inconnu → `null`.
- `budget_base` garde la forme d'origine (`total`, `par_personne`, `par_nuit`, `par_jour`), pour
  vérifier la multiplication. « Par personne et par nuit » → `par_nuit` (choix de l'équipe en v2,
  H-018 : 80 × 8 personnes × 3 nuits = 1 920 DT).
- `budget_total_dt` = `budget_montant` **seulement si la devise est TND**, sinon `null`. Le LLM ne
  convertit jamais ; une conversion éventuelle viendra plus tard d'un taux configuré et affiché.
- « Pas de limite », « budget sans problème » → `budget_illimite = true`, `budget_montant = null`,
  et **pas** de `budget` dans `champs_manquants` (aucune question).
- « Budget confortable », « mid budget », « tout petit budget » sans montant → `null`, et `budget`
  manquant.

### Voyageurs

- `type_voyage` seulement s'il est explicite ou sans ambiguïté :
  - enfant ou membre de la famille (mère, sœur, frère, cousins, grand-mère, parents…) → `famille` ;
  - conjoint, mari, femme, copain, copine, « sa7bti » → `couple` ;
  - « seul(e) », « wa7di » → `solo` ;
  - amis, copains, « s7abi », « 2 couples » → `amis` ;
  - collègues, élèves, étudiants, équipe, seniors en groupe organisé → `groupe` ;
  - « à deux », « 2 personnes », « 4 adultes », « des invités » → `null`.
- « Pour mes parents » : ce sont eux les voyageurs (`couple`, 2 adultes).
- `nb_voyageurs` = **total** du groupe (« famille de 4 » = 4, « ena w s7abi 5 » = 6) ; `null` si
  inconnu (« en famille », « avec mes amis »). Un « je » ne suffit pas à conclure à 1 voyageur si
  rien ne dit « seul(e) ».
- `nb_adultes` / `nb_enfants` : seulement si la répartition est connue (« 2 adultes 1 enfant »,
  « ma femme et nos deux enfants », « couple » = 2 / 0) ; sinon `null` tous les deux.
  `nb_enfants` = 0 quand le groupe est décrit sans enfant. Un bébé ou un ado compte comme un
  enfant ; une « fille » ou un « frère » d'âge inconnu → répartition `null`.

### Préférences et contraintes

| Le texte dit | Thème |
|---|---|
| plage, mer, b7ar, البحر, beach | `plage` |
| culture, musées, médina, traditions, mosquée, fête religieuse | `culture` |
| histoire, ruines, romain, patrimoine, ribat | `histoire` |
| oasis, nature, randonnée, paysages | `nature` |
| gastronomie, cuisine, street food, restaurants, dîner | `gastronomie` |
| sensations, quad, parachute | `aventure` |
| détente, repos, spa, hammam, thalasso, massage | `detente` |
| souks, shopping, artisanat, tapis | `shopping` |
| plongée, jet-ski, kitesurf, sports nautiques, parc aquatique | `nautique` |
| désert, Sahara, dunes, sahra, nuit sous tente | `desert` |

- « musées » seul → `culture` ; « histoire et musées » → `culture` + `histoire`.

### Activités souhaitées `activites_souhaitees`

Elles servent à la recherche de l'étape 5 ; les **thèmes** (`preferences`) restent remplis en parallèle.

- Une activité = **une chose concrète à faire ou un lieu précis à visiter**, telle que le client
  la dit : « quad dans les dunes », « musée du Bardo », « hammam », « جامع عقبة », « jet ski ».
- **Textes du client, dans sa langue** (pas de traduction, pas de code) ; on retire le verbe
  d'introduction et l'article de tête (« visiter la grande mosquée » → « grande mosquée »), on garde
  le complément qui précise l'activité (« dîner avec vue sur le golfe »).
- **Une entrée par activité** ; les alternatives comptent séparément (« plongée ou snorkeling »,
  « kitesurf wala windsurf » → deux entrées). Ordre du texte.
- **Exclus** : les mots qui ne sont qu'un thème (plage, mer, désert, sahra, culture, histoire, nature,
  détente, gastronomie, shopping, sports nautiques, visites culturelles) → seulement dans
  `preferences` ; les villes du catalogue (→ `destination` / `autres_villes`) ; les critères
  d'hébergement (piscine, wifi, 5 étoiles) ; le transport (4x4 de location, chauffeur) ; les
  horaires (« au coucher du soleil » → `contraintes.horaires`). Un lieu précis hors catalogue
  (Chebika, Carthage, Friguia park) **est** une activité.
- Les codes `activites` de l'équipe (`nuit_desert`, `visite_monument`…) restent dans
  `annotation_equipe` : seul leur nombre est comparé dans l'accord entre annotateurs.
- **Évaluation (F1)** : après normalisation (minuscules, sans accents, ponctuation, mots vides ni
  article arabe « ال »), une activité prédite correspond à une attendue si elles sont égales, si
  l'une contient l'autre, ou si leurs mots se recouvrent à 50 % ou plus (indice de Jaccard) ;
  appariement un à un. F1 = 2·VP / (nb prédites + nb attendues). Implémentation :
  `scripts/jeu_nlu.py` (`activites_correspondent`, `apparier_activites`).
- Ce qui n'a pas de thème (photo, cafés, soirées, piscine, wifi, hôtel 5 étoiles) → rien.
- `niveau_marche_max` : 1 = marche très difficile, fauteuil roulant, mobilité réduite ; 2 = « pas
  trop fatigant », « on marche peu », « éviter les longues marches », « pas d'escaliers » ;
  3 = rarement dit, sinon `null`.
- `mobilite_reduite` : `true` pour fauteuil roulant, « PMR » ou « marche mal », sinon `null`.
- `horaires` : texte libre court (« matin », « soir », « pas avant 10 h »), **non noté** à
  l'évaluation.

### Transport

- `vol = oui` si le voyageur demande un vol ou dit venir **en avion** (« bel tayara », « flying
  from », « vol depuis ») ; `non` s'il dit avoir déjà ses billets, venir en train, en louage, en
  voiture (la sienne)… Arriver en avion sans demander de vol (« on atterrit samedi ») →
  `indifferent`.
- « Venir de Lyon » sans dire le moyen → `ville_depart = Lyon`, `vol = indifferent` (on ne
  devine pas).
- `voiture` concerne la **location** : « on loue une voiture », « nekri karhba », « un van », « 4x4 »
  → `oui` ; « sans voiture », « pas de voiture », « on ne veut pas conduire », « en taxi »,
  « avec notre propre voiture » → `non`. « On n'a pas de voiture » (constat, pas un refus) →
  `indifferent`.
- `transfert = oui` s'il demande un transfert, une navette aéroport ↔ hôtel, un chauffeur privé, un
  minibus ou un bus avec chauffeur (le catalogue n'a pas d'autre offre avec chauffeur).
- `vol_direct` : `true` (« vol direct », « directe ») ; `false` (« escale acceptée », « sinon via
  Tunis ») ; sinon `null`.
- `boite_auto` : `true` (automatique) ; `false` (manuelle) ; sinon `null`.
- `priorite` (transport) : `prix` (« le moins cher », « priorité au prix ») ; `confort` (« luxe »,
  « priorité au confort ») ; sinon `null`.
- `budget_inclut_transport` : **`true` si au moins un besoin de transport vaut `oui`** (le budget
  couvre tout ce qui est proposé sur Voyara), sauf si le texte dit le contraire ; `false` sinon.

### Langue

- Alphabet arabe → `ar` (arabe standard ou darija écrite en arabe : on répondra en arabe).
- Darija en lettres latines (« f », « m3a », « n7eb », « s7abi », « nemchi »…) → `darija`.
- Sinon `fr` ou `en` selon la langue dominante.

### Hors sujet et hors catalogue

- Demande sans rapport avec un voyage en Tunisie (recette, lettre de motivation, culture générale,
  tentative de détournement du prompt) → `hors_sujet = true`, autres champs `null` ou par défaut,
  `champs_manquants = []`.
- Destination hors catalogue (Matmata, Ksar Ghilane, Kélibia, ou une ville étrangère : Alger,
  Paris…) → `destination = null` et `destination` manquant : le système doit proposer les villes
  connues, jamais en inventer une. Les cas de référence sont G-137 (dev) et G-138 (test).
  Une destination hors catalogue **n'est pas recopiée** dans `activites_souhaitees` (« 2 jours à
  Ksar Ghilane » → `activites_souhaitees = []`) : la règle « un lieu précis hors catalogue est une
  activité » vaut pour un site visité depuis une ville du catalogue (« Chebika » depuis Tozeur), pas
  pour le lieu de séjour lui-même.
- **Nom de gouvernorat** : il désigne toujours la ville chef-lieu du même nom (« Nabeul » → Nabeul,
  « Médenine » → Médenine, « Kébili » → Kébili). Hammamet, Djerba, Tabarka et Douz restent des villes à
  part : on ne les remplace jamais par leur chef-lieu. « Kef » et « El Kef » s'annotent « Le Kef », et
  « Manouba », « La Manouba ».

### Champs manquants (règle des champs essentiels)

`destination`, `duree`, `budget` (= `budget_montant` inconnu, quelle que soit la devise, sauf si
`budget_illimite`) et
`voyageurs` (= `nb_voyageurs` inconnu) sont toujours essentiels ; si `vol = oui`, `ville_depart` et
`date_debut` le deviennent aussi. Une demande hors sujet n'a pas de champ manquant.
