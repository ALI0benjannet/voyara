# Validation DL — Interface « DL test » (résultats + tests en direct, sans LLM)

> Date : 2026-11-16 · Branche : `main` (choix de l'étudiante) · Ons · Modules : validation DL (recherche d'Ons, classification de Boutheina)

## 1. Objectif

Visualiser dans Voyara les résultats des deux validations Deep Learning et les tester en direct, **sans appeler de LLM** : un bouton temporaire « DL test » dans l'en-tête du site client ouvre une page dédiée (à retirer après la soutenance).

## 2. Réalisé

| Fichier | Créé / modifié | Rôle (une ligne) |
|---|---|---|
| `services/ai/app/dl/chemins.py` | créé | Emplacements des données, résultats (`docs/ia/resultats`) et modèles (`modeles/`) |
| `services/ai/app/dl/resultats.py` | créé | Lecture des CSV `dl_recherche*` et `dl_classif*` |
| `services/ai/app/dl/recherche.py` | créé | Recherche en direct : TF-IDF, e5 gelé, e5 fine-tuné (si présent) ; chargement en arrière-plan, un verrou par modèle |
| `services/ai/app/dl/classification.py` | créé | Classification en direct : règles de l'étape 4, TF-IDF + régression logistique, XLM-R fine-tuné (si présent) |
| `services/ai/app/dl/routes.py` | créé | 6 routes publiques `/api/ai/dl/*` (`resultats`, `etat`, `exemples`, `prechauffer`, `rechercher`, `classifier`) |
| `services/ai/app/main.py` | modifié | Inclusion du routeur DL |
| `services/ai/scripts/dl_convertir_e5_bf16.py` | créé | Copie bfloat16 d'e5-base (556 Mo) lue par tranches, pour les postes à peu de mémoire |
| `services/ai/tests/test_dl_routes.py` | créé | 8 tests (faux encodeur, aucun téléchargement ni base) |
| `services/ai/tests/test_main.py` | modifié | Liste des routes exposées complétée par les 6 routes DL |
| `frontend/apps/client/src/app/dl-test/page.tsx` | créé | Page `/dl-test` (non indexée) |
| `frontend/apps/client/src/components/dl-test/DlTest.tsx` | créé | Interface : 2 onglets (Ons / Boutheina), tableaux à barres, tests en direct |
| `frontend/apps/client/src/features/dl-test/api.ts` | créé | Types + hooks TanStack Query |
| `frontend/apps/client/src/components/layout/Navbar.tsx`, `routes/paths.ts` | modifiés | Bouton temporaire « DL test » |
| `frontend/packages/api/src/endpoints.ts` | modifié | Endpoints `ai.dl.*` |
| `frontend/packages/i18n/src/locales/{fr,en,ar}/common.json` | modifiés | Bloc `dlTest` + `nav.dlTest` en fr / en / ar |

## 3. Choix techniques

- **Backend dans le service `ai`** (propriétaire du moteur IA), routes publiques limitées à 30 appels/min ; aucun appel au LLM (règles de l'étape 4 en méthode `regles`).
- **Mêmes données que les notebooks** (`activites.json`, préfixes `query:`/`passage:`, mêmes vectoriseurs) : les classements affichés sont ceux qui ont été mesurés. Alternative écartée : interroger le catalogue en direct (textes et thèmes différents de ceux évalués).
- **Chargement des modèles en arrière-plan** : le premier encodage d'e5 dépasse le délai de 30 s du gateway et du proxy Next sur CPU. `POST /dl/prechauffer` est appelé à l'ouverture de la page ; tant qu'e5 n'est pas prêt, la recherche répond tout de suite avec TF-IDF et `en_chargement` pour e5, et la page relance la recherche toutes les 5 s.
- **Copie bfloat16 d'e5** utilisée si elle existe (moitié moins de mémoire) : rangs identiques au notebook pour 67/70 requêtes (écart d'une place pour les 3 autres).
- **Modèles absents → « non disponible »** au lieu d'une erreur : e5 fine-tuné (Kaggle) et XLM-R de Boutheina (Drive) apparaissent dès qu'ils sont copiés dans `modeles/` (`e5-voyara-ft`, `xlmr-voyara-{type_voyage,vol,voiture}`).
- **Bouton isolé et marqué TEMPORAIRE** dans `Navbar.tsx` : le retirer = supprimer le lien, `paths.dlTest`, les 3 dossiers `dl-test` et le bloc i18n.

## 4. Vérification

- `pytest` (services/ai) : `285 passed` (dont 8 nouveaux tests DL ; `test_routes_exposees` mis à jour).
- `npm run typecheck` : aucune erreur (client et admin) ; `npm run test` : `12 passed`.
- Projet lancé (`docker compose up -d postgres postgres-ai`, `scripts/dev.ps1`, `npm run dev`) : `/health` → 8 services `ok` ; `/dl-test` → 200.
- Comparaison des 70 requêtes du jeu de test, en direct via le gateway, avec `docs/ia/resultats/dl_recherche_rangs.csv` :
  ```
  TF-IDF : rang identique au notebook 70/70
  e5 gelé : rang identique 67/70 ; 1re bonne activité dans le top 5 : 62/70 (notebook : 62/70)
  latence e5 médiane : 151.8 ms
  ```
- Navigateur : bouton « DL test » → page ; R-067 (darija) : TF-IDF rang 15, e5 gelé rang 4 (surligné) ; G-104 (arabe) : règles et TF-IDF + LogReg justes sur les 3 champs ; arabe affiché en `dir="rtl"`.

## 5. Métriques

Non applicable (interface) ; les chiffres affichés sont ceux de `etape-dl-recherche.md` et `etape-dl-classif.md`.

## 6. Limites, dette technique, risques

- **Mémoire** : e5 demande ≈ 600 Mo libres. Sur ce poste (5,9 Go), le chargement échouait (erreur Windows 1455) tant que le projet Caseforge (≈ 10 Go) tournait ; arrêté à la demande de l'étudiante. Le serveur Next s'était aussi arrêté faute de mémoire.
- e5 fine-tuné et XLM-R de Boutheina non testables en direct sur ce poste (modèles sur Kaggle / Drive).
- Routes publiques sans authentification (démonstration) : à retirer avec la page.
- Travail sur `main` sans branche dédiée (choix de l'étudiante) ; pas encore commité.

## 7. À vérifier par moi

1. Ouvrir http://localhost:5173, cliquer « DL test ».
2. Onglet Recherche : choisir une requête du jeu de test → attendre ≈ 1 min la première fois → vérifier les surlignages verts.
3. Onglet Classification : choisir une demande du jeu de test → vérifier les ✅ / ❌ par rapport à « Attendu ».
4. Changer la langue (FR / EN / عربي) en haut à droite.

## 8. Étape suivante recommandée

Copier le modèle e5 fine-tuné (Kaggle) et les XLM-R de Boutheina (Drive) dans `modeles/` pour compléter les colonnes ; retirer le bouton et les routes après la soutenance.
