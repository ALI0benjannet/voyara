# Captures d'écran à réaliser

Enregistrer les fichiers **dans ce dossier**, avec exactement ces noms
(le rapport les référence via `\includegraphics{screenshots/<nom>.png}`).

Format conseillé : PNG, largeur 1400–1600 px, navigateur en **plein écran**,
**langue française**, et **connecté** avec un compte de test.

| Fichier | Écran | Cadrage attendu |
|---|---|---|
| `accueil.png` | `http://localhost:5173/` | Haut de page : navbar, hero avec la barre de recherche, début des destinations |
| `catalogue.png` | `http://localhost:5173/activities` | Filtres (recherche, ville, catégories) **et** au moins 6 cartes d'activité |
| `detail-activite.png` | `http://localhost:5173/activities/9` | Photo, titre, description **et** carte de réservation à droite |
| `paiement-confirme.png` | Après un paiement test | Écran « Réservation confirmée » avec le **QR code** visible |
| `admin-dashboard.png` | `http://localhost:5174/dashboard` | Barre latérale, les 4 indicateurs **et** le tableau des dernières réservations |

## Conseils

- Masquer les données personnelles réelles si nécessaire (adresse e-mail).
- Éviter les fenêtres de développement (console, DevTools) dans le cadrage.
- Pour `paiement-confirme.png` : utiliser la carte de test Stripe
  `4242 4242 4242 4242` (16 chiffres), onglet **Carte** — pas Link.

## Si une capture manque

Le rapport compile quand même, mais LaTeX affichera un cadre vide à la place.
Pour compiler sans les captures, commenter les blocs `figure` correspondants
dans `rapport.tex` (chapitre « Fonctionnalités détaillées »).
