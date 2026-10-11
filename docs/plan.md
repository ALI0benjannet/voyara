
<aside>
🎯

Plan de réalisation complet de **Voyara**, plateforme de réservation d'activités touristiques.
Architecture : **microservices FastAPI** (backend) + **micro-frontends** (client Next.js SSR/SEO + admin Vite).
Chaque phase est découpée en tâches concrètes à cocher. Détail technique : [architecture.md](architecture.md).

</aside>

## 🧭 Comment lire ce plan

Chaque tâche **restante** porte deux étiquettes :

- **Effort** — `S` (≤ ½ journée) · `M` (1–2 jours) · `L` (3 jours et +)
- **Priorité** — `must` (indispensable pour la soutenance) · `should` (forte valeur, à faire si le rythme tient) · `nice` (bonus, uniquement si de l'avance)

Les tâches jugées **surdimensionnées pour un PFE solo** ont été déplacées en fin de document
(section « Reporté après la soutenance ») : elles restent des perspectives, pas des objectifs.

## 🗓️ Jalons (soutenance visée : semaine du 21 septembre 2026 — à confirmer)

| Jalon | Date cible | Objectif démontrable | Contenu principal |
| --- | --- | --- | --- |
| **J1 — L'admin gère son catalogue** | ven. 21/08 | Créer une activité avec photos depuis l'admin et la voir sur le site | Fin de Phase 6 (CRUD catégories/activités/créneaux) + écrans admin (Phase 11) + upload photos |
| **J2 — Réservation payée de bout en bout** | ven. 04/09 | Parcours complet : réservation → paiement Stripe test → confirmation → e-mail + QR code | Validation promo, Phase 8 (Stripe back+front), e-mail de confirmation, QR (Phase 9) |
| **J3 — Qualité démontrable** | ven. 11/09 | Suite de tests verte en CI, parcours E2E automatisé, robustesse inter-services | Phase 12 (pytest saga, E2E Playwright), CI GitHub Actions, timeouts/retry, expiration des réservations non payées |
| **J4 — Gel & dossier** | ven. 18/09 | **Gel fonctionnel.** Rapport complet, démo scriptée, jeu de données de démo | Phase 14 finalisée : rapport, diagrammes, guide d'utilisation, slides |
| **Semaine 6** | 21–25/09 | Répétitions de la soutenance, corrections mineures uniquement | Buffer — aucune nouvelle fonctionnalité |

> ⚠️ **Le rapport ne se rédige pas en semaine 6.** Réserver ~1 jour/semaine à la Phase 14
> dès maintenant : le cahier des charges et les diagrammes servent aussi à cadrer le développement.

## 🔀 Ordre des phases restantes — justification

1. **CRUD admin du catalogue d'abord (J1)** — aucune dépendance technique n'oblige à le faire avant
   Stripe, mais il débloque tout le reste de la démo : photos réelles côté client, créneaux gérables
   pour tester le tunnel, et c'est le manque le plus visible pour un jury (un admin qui ne peut pas
   créer d'activité n'est pas un admin).
2. **Validation des codes promo avant Stripe** — le `create-intent` applique le promo au montant :
   l'endpoint de validation est donc un **prérequis** du tunnel de paiement, pas une tâche annexe.
3. **Stripe ensuite (J2)**, puis e-mail de confirmation et QR code **après** Stripe : les deux sont
   déclenchés par le webhook `payment_intent.succeeded` (passage `pending → confirmed`).
4. **Tests, CI et robustesse (J3) avant le gel** — tester après Stripe évite de réécrire les tests,
   mais ne pas repousser en semaine 6 : une démo qui casse la veille de la soutenance est le pire scénario.
5. **L'IA (Phase 10) passe en dernier** — dans le plan initial elle précédait l'espace admin, alors
   qu'elle n'a aucune dépendance entrante et une valeur de démo faible comparée au paiement. Version
   « règles » uniquement, et seulement si J3 est atteint en avance.
   *(Màj 11/10/2026 : remplacée par la [phase Moteur IA](#-phase-moteur-ia--projet-ia--cognition-5ds),
   qui a son propre calendrier, indépendant des jalons J1–J4.)*

---

## 🧱 Stack technique (en place)

| Couche | Technologie | Rôle |
| --- | --- | --- |
| Site client | **Next.js 16 (App Router) + TypeScript** | SSR/SEO : catalogue indexable, metadata, sitemap, JSON-LD |
| Espace admin | React + Vite + TypeScript | SPA privée servie sous `/admin`, login admin dédié |
| Packages front | npm workspace `@voyara/{ui,api,auth,i18n}` | Design system, axios+refresh, session, i18n — partagés Vite/Next |
| UI | Tailwind CSS v4 (+ thème maquette 08/2026) | Palette sable/sarcelle/terracotta, Marcellus + Albert Sans |
| État / data | TanStack Query + Axios + Zustand | Cache API, intercepteur refresh sur 401, session persistée |
| i18n | react-i18next | FR / EN / AR (+ RTL) |
| Backend | **7 microservices Python + FastAPI** | auth · catalog · booking · payment · review · notification · admin (BFF) |
| Gateway | FastAPI + httpx | Point d'entrée unique :8000, routage, CORS, blocage `/internal` |
| Code partagé | `libs/common` (`voyara_common`) | JWT, sécurité, pagination, appels inter-services |
| ORM | SQLAlchemy 2 + Alembic (auth) | **Une base PostgreSQL par service** (database-per-service) |
| Base de données | PostgreSQL 16 (Docker, port 5434) | `voyara` + `voyara_{catalog,booking,payment,review}` |
| Auth | JWT HS256 partagé (python-jose) + passlib | Access 30 min + refresh rotatif hashé en base |
| Paiement | Stripe (SDK Python + Stripe.js) | *À intégrer — Phase 8 (jalon J2)* |
| Cartes | Carte interactive OSM (MapLibre GL + OpenFreeMap) | **Fait** — libellés fr / en / ar |
| E-mail | notification-service (fastapi-mail + SMTP Gmail) | Vérification de compte, reset mot de passe |
| QR Code | `qrcode` (Python) | *À intégrer — Phase 9 (jalon J2)* |
| IA | Service `ai` (FastAPI) + pgvector + LLM hybride Claude API / Ollama + OR-Tools | *Phase Moteur IA — étapes 0 à 13 (ADR-007)* |
| Déploiement | Docker Compose (11 conteneurs) + nginx | ✅ en place · CI/CD GitHub Actions à faire (J3) |
| Dossier PFE | Rapport + UML/C4 + slides + guide | *Phase 14 — en continu, ~1 j/semaine* |

---

## 🏗️ Phase A — Refonte d'architecture (août 2026) ✅

- [x]  Migration du monolithe FastAPI vers **7 microservices** + API Gateway (12/08)
    - [x]  Database-per-service, endpoints `/internal/*` protégés par clé partagée
    - [x]  admin-service en **BFF agrégateur** (asyncio.gather + endpoints `/batch`)
    - [x]  **Saga de réservation** : réservation atomique des places + compensation
    - [x]  Suppression des endpoints de debug hérités du monolithe
- [x]  Frontend découpé en **micro-frontends** (workspace npm apps/ + packages/) (13/08)
    - [x]  App admin autonome (`/admin`, login admin dédié — ex-Phase 5)
    - [x]  Packages partagés `@voyara/{ui,api,auth,i18n}` importés en source
- [x]  **Design system** appliqué depuis la maquette Claude Design (13/08)
    - [x]  Palette sable/sarcelle/terracotta + polices Marcellus & Albert Sans
    - [x]  Seed du catalogue : 5 catégories, 8 activités géolocalisées, ~88 créneaux
- [x]  Site client migré sur **Next.js (App Router)** pour le SEO (13/08)
    - [x]  SSR accueil/catalogue/détail, `generateMetadata`, ISR 60 s
    - [x]  `sitemap.xml` + `robots.txt` générés, JSON-LD `TouristAttraction`
- [x]  Docker Compose complet : Postgres + 8 conteneurs backend + client Next standalone + nginx (origine unique :8080)

---

## 📅 Phase 0 — Initialisation du projet ✅

- [x]  Créer le dépôt Git (monorepo)
- [x]  Définir la convention de branches (main, develop, feature/*) — ⚠ à re-vérifier : seule la branche `main` existe sur le dépôt
- [x]  Rédiger le `README.md` avec l'architecture générale
- [x]  Créer les fichiers `.gitignore` (Python + Node)
- [x]  Choisir et documenter la stack définitive (ci-dessus)

---

## 🗄️ Phase 1 — Conception & base de données ✅

- [x]  Modèle de données (MCD) : diagrammes ER Mermaid par service générés depuis les modèles réels — [docs/mcd.md](mcd.md)
- [x]  Tables principales : `users`, `activities`, `categories`, `bookings`, `payments`, `reviews`, `availabilities`, `promo_codes`, `favorites`
- [x]  Définir les rôles utilisateurs (touriste, administrateur)
- [x]  PostgreSQL (Docker) + bases par service créées automatiquement
- [x]  SQLAlchemy + Alembic (historique conservé sur la base auth)

---

## ⚙️ Phase 2 — Backend : fondations ✅

- [x]  Structure FastAPI par service (`app/`, `models`, `schemas`, `routers`, `services`)
- [x]  Connexion base par service (SQLAlchemy session, `libs/common.database`)
- [x]  Configuration par variables d'environnement (Pydantic Settings, `.env` par service)
- [x]  CORS (géré au gateway)
- [x]  Documentation auto Swagger (`/docs` par service)
- [x]  Logging + gestion centralisée des erreurs (`voyara_common`)

### 🔐 Authentification ✅

- [x]  Modèle `User` + schémas Pydantic
- [x]  `POST /auth/register` (hash pbkdf2_sha256)
- [x]  `POST /auth/login` (JWT access + refresh)
- [x]  Vérification du JWT **sans DB** dans tous les services (`get_current_identity`)
- [x]  Gestion des rôles (`require_admin`)
- [x]  `GET /auth/me`

---

## 📧 Phase 3 — Backend : authentification complète ✅

- [x]  notification-service dédié (SMTP via variables d'env, envoi asynchrone)
- [x]  Templates HTML : confirmation de compte, réinitialisation de mot de passe
- [x]  `is_active` / `is_verified` / `email_verified_at` sur `User`
- [x]  Table `email_verification_tokens` (hashé, expiration, usage unique)
- [x]  E-mail de confirmation à l'inscription + `POST /auth/verify-email` + `resend-verification` (rate-limité)
- [x]  Login bloqué tant que l'e-mail n'est pas vérifié
- [x]  Table `password_reset_tokens` + `forgot-password` (anti-énumération) + `reset-password` + `change-password`
- [x]  Refresh tokens **rotatifs** + `POST /auth/refresh` + `POST /auth/logout` + invalidation après reset
- [x]  Rate limiting sur les routes sensibles
- [x]  `PATCH /auth/me` + avatar (upload/suppression)
- [x]  Seed du compte administrateur (`scripts/seed_admin.py`)
- [x]  Tests pytest du parcours auth complet (register → verify → login → forgot → reset)

---

## ⚛️ Phase 4 — Frontend : fondations ✅

- [x]  Workspace npm : apps (client Next, admin Vite) + packages partagés
- [x]  Routing : App Router (client) / react-router (admin)
- [x]  Axios + intercepteurs (JWT, refresh auto sur 401) — `@voyara/api`
- [x]  TanStack Query (cache et requêtes)
- [x]  Design system (`@voyara/ui`, thème Tailwind v4 de la maquette)
- [x]  Layout responsive + Navbar 2 rangées / Footer (design)
- [x]  i18n FR / EN / AR + RTL + sélecteur de langue (pilules)
- [x]  **Contenu métier traduit en base** : colonnes `titre_en/ar`, `description_en/ar`, `nom_en/ar` (repli automatique sur le français) + champs de traduction dans le formulaire admin
- [x]  **Interface admin traduite** (10 pages, sélecteur de langue, RTL) — 116 clés
- [x]  Audit : 0 clé i18n manquante sur les 290 utilisées (client + admin)
- [x]  Session (`@voyara/auth` : store persisté, AuthProvider, useAuth)
- [x]  Gardes : `RequireAuth` / `GuestOnly` (client Next) · `AdminRoute` (admin)
- [x]  Erreurs globales + toasts (sonner) + états de chargement
- [x]  `.env` par app + proxys dev `/api` (rewrites Next / proxy Vite)

---

## 👤 Phase 5 — Frontend : parcours d'authentification ✅

### Espace client

- [x]  Inscription (validation zod : e-mail, mot de passe fort, confirmation)
- [x]  Écran « Vérifiez votre boîte mail » + renvoi avec cooldown
- [x]  Confirmation de compte (`/verify-email`) : succès, token expiré/invalide
- [x]  Connexion (erreurs : identifiants invalides, compte non vérifié) + `?next=`
- [x]  Mot de passe oublié + réinitialisation (`/reset-password`, code + robustesse)
- [x]  Déconnexion + persistance de session au rechargement (refresh token)
- [x]  Page profil : informations + mot de passe + avatar
- [x]  Traduction FR / EN / AR des écrans d'auth (dont RTL) — AR complété le 14/08 (11/11 sections)

### Espace administrateur

- [x]  Page de connexion admin dédiée (`/admin/login`)
- [x]  Un admin navigue librement sur le site public ; accès admin via menu/footer
- [x]  Layout admin (sidebar + protection de toutes les routes `/admin/*`)
- [x]  Page 403 / accès refusé

---

## 🧩 Phase 6 — Backend : modules métier (API REST) ✅ *(sauf 2 items liés au paiement)*

### Activités & catégories

- [x]  `GET /categories` (liste)
- [x]  CRUD admin des catégories (POST/PUT/DELETE, garde si activités liées)
- [x]  `GET /activities` : recherche (titre/lieu), filtre catégorie, pagination
- [x]  `GET /activities/{id}` (détail)
- [x]  Coordonnées GPS (latitude/longitude) en base — seed géolocalisé
- [x]  CRUD admin des activités (garde inter-services : refus si réservations existantes)
- [x]  Upload de photos d'activités (multipart → `/static/activities/`, servi par catalog via le gateway)

### Disponibilités

- [x]  Modèle `Availability` (date, heure, places) + `GET /activities/{id}/availabilities`
- [x]  Vérification + **décrément atomique** des places à la réservation (`/internal/…/reserve|release`)
- [x]  CRUD admin des créneaux (création/modification/suppression) — modifier « places » ajuste la **capacité** : le delta est reporté sur les places restantes, les réservations déjà prises restent décomptées
- [x]  `places_totales` : capacité d'origine figée à la création, exposée par l'API (« 6 places sur 8 ») et référence du contrôle de cohérence
- [x]  **Réconciliation catalog ↔ booking** (`booking/scripts/reconcile_seats.py`) : détecte places fantômes, places en trop et réservations orphelines ; `--fix` réaligne. Validé sur incohérences injectées (−3 et +4 places)

### Favoris ✅

- [x]  Ajouter / retirer / lister (review-service, contrainte d'unicité)

### Réservations

- [x]  Modèle `Booking` (activité, créneau, statut, `nb_places`, montant)
- [x]  `POST /bookings` : saga avec vérification de disponibilité, **multi-voyageurs** (1-8)
- [x]  Historique du touriste (`GET /bookings`, titres enrichis via catalog)
- [x]  Statuts (pending / confirmed / cancelled) + annulation avec libération des places
- [x]  Passage `pending → confirmed` déclenché par le paiement (webhook/simulation → confirm interne)
- [x]  **Concurrence durcie** (3 correctifs, validés par tests à 8 threads simultanés) :
    - Annulation : transition `→ cancelled` par UPDATE conditionnel — évitait 8 libérations pour une seule annulation (places fantômes)
    - Confirmation : transition `pending → confirmed` atomique — un seul e-mail même si Stripe rejoue le webhook
    - Anti-doublon : index unique partiel `uq_booking_active_user_slot` — un double-clic renvoie la réservation existante au lieu d'en créer deux
- [x]  **Expiration des réservations `pending` non payées** : tâche de fond (`app/expiry.py`) qui annule après **3 h** et rend les places au catalogue. Transition par UPDATE conditionnel → un paiement en cours gagne toujours la course, et des balayages répétés ne libèrent jamais deux fois. Réglable (`BOOKING_EXPIRY_MINUTES`), déclenchable à la demande (`POST /internal/bookings/expire-pending`). *(3/3 tests de concurrence)*

### Codes promo

- [x]  Modèle `PromoCode` (valeur, expiration, actif)
- [x]  Validation d'un code promo (`POST /bookings/validate-promo`, insensible à la casse) + application au montant à la réservation (`promo_code_id` stocké) — seeds `BIENVENUE10`/`ETE2026`

### Avis & notes

- [x]  Modèle `Review` + déposer / consulter les avis (`/reviews?activity_id=`)
- [x]  Dépôt d'avis restreint aux clients ayant réservé (appel interne review → booking `has-booked`, 403 sinon)
- [x]  Notes moyennes ★ sur cartes/détail (`GET /reviews/stats`, rendu SSR + `aggregateRating` JSON-LD)

### Données personnelles (RGPD) — *tâches ajoutées*

- [x]  Suppression de compte (`DELETE /auth/me` : anonymisation, révocation des sessions, purge des tokens, bouton page profil)
- [x]  Page « Politique de confidentialité » (`/privacy`, SSR indexable, liée au footer)

---

## 🖼️ Phase 7 — Frontend : catalogue & découverte ✅ *(périmètre retenu terminé ; panier volontairement reporté)*

- [x]  Accueil : hero + recherche (destination/date/voyageurs), destinations, activités populaires
- [x]  Page activités : recherche, chips catégories, tri prix, pagination serveur
- [x]  ~~Vue carte stylisée (pins positionnés par lat/lng)~~ → remplacée par la vraie carte ci-dessous
- [x]  Carte interactive OpenStreetMap (MapLibre GL + tuiles vectorielles OpenFreeMap : pins de prix cliquables, mini-carte sur la page détail, **libellés traduits fr / en / ar**)
- [x]  Page détail : description, catégorie, durée, réservation (créneaux réels + voyageurs)
- [x]  Bouton favoris (cœur) + page « Mes favoris »
- [x]  Sélection du créneau (liste des disponibilités avec places restantes)
- [x]  Page « Mes réservations » (statuts, montants, annulation)
- [x]  Photos réelles des activités : upload admin opérationnel + affichage automatique (placeholder dégradé sinon) + jeu de démo libre de droits (`seed_photos.py`) et page `/credits`
- [ ]  ~~Panier / réservation de plusieurs activités en une fois~~ → **reporté après la soutenance** (complexifie la saga et le paiement pour une valeur de démo faible)

---

## 💳 Phase 8 — Paiement en ligne — **J2 ATTEINT le 14/08** ✅ *(mode simulation ; clés Stripe test à brancher)*

> **Décision de cadrage proposée : paiement du montant total uniquement.** Le mode « avance /
> acompte » double les cas de test (webhook, remboursement, affichage) pour un gain de démo nul.
> À garder en perspective.

### Backend (payment-service)

- [ ]  Compte Stripe (mode test) + coller les clés dans `services/payment/.env` `S · must` *(seule étape restante — le code bascule automatiquement de la simulation au vrai Stripe)*
- [x]  `POST /payments/create-intent` (montant remisé de la réservation ; anti-doublon ; EUR car Stripe ne supporte pas le TND — documenté)
- [x]  Webhook `payment_intent.succeeded` : signature vérifiée + **idempotence** (table `processed_events`) + gestion `payment_failed`
- [x]  Route webhook via le gateway (`/api/v1/payments/webhook`, sans JWT — l'auth est la signature Stripe)
- [x]  Confirmation `pending → confirmed` via appel interne booking (idempotent, génère le QR, déclenche l'e-mail)
- [x]  Paiement en base (statut, montant, `stripe_intent_id`) — visible dans le dashboard admin (CA réel)

### Frontend (client Next)

- [x]  Tunnel `/bookings/{id}/pay` : récapitulatif → paiement → écran de confirmation avec QR
- [x]  Stripe.js Payment Element (mode réel) + bouton « Simuler le paiement » étiqueté démo (mode simulation) ; promo appliqué dès la réservation
- [x]  Écran de confirmation + QR code SVG (endpoint authentifié) + boutons Payer/QR dans « Mes réservations »
- [ ]  Historique enrichi (paiements liés aux réservations) `S · should`

---

## 📧 Phase 9 — Services externes (réservation) → jalon J2 (sauf mention)

- [x]  E-mail de confirmation après paiement (template `booking_confirmed.html`, envoyé en tâche de fond)
- [x]  **Notification e-mail aux administrateurs à chaque nouvelle réservation** (template `admin_new_booking.html`, destinataires = admins actifs via `/internal/admins`) *(ajouté le 14/08)*
- [x]  QR code de validation (`TB-{id}-{aléa}`, SVG via `GET /bookings/{id}/qrcode`, affiché après paiement)
- [ ]  Endpoint admin de scan / validation du QR Code sur place `M · should` *(J3 — bel effet en démo, mais pas bloquant)*
- [ ]  ~~Cartographie avancée (itinéraire, clustering de marqueurs)~~ → **reporté** (la carte de Phase 7 suffit)

---

## 🤖 Phase 10 — Fonctionnalités intelligentes — ~~recadrée `nice`~~ → **remplacée par la phase Moteur IA (ADR-007)**

> 🔁 **Remplacée le 11/10/2026 par la [phase Moteur IA](#-phase-moteur-ia--projet-ia--cognition-5ds)
> ([ADR-007](architecture.md#adr-007--microservice-ai-dédié-pgvector-et-llm-hybride)).** Conservée
> ci-dessous pour l'historique : le cadrage « règles dans catalog, pas de 8ᵉ service » ne s'applique plus.

> *(Historique)* **Surdimensionné pour 6 semaines.** À ne lancer que si J3 est atteint en avance. La version
> « règles » se démontre aussi bien que du ML, s'explique mieux au jury, et ne demande ni données
> d'entraînement (8 activités !) ni pipeline. Si la « recommandation IA » figure dans ton cahier des
> charges initial, la v1 règles y répond ; sinon, présenter la Phase 10 en « perspectives ».

- [ ]  Activités similaires sur la page détail (règles : même catégorie, prix proche) `M · nice`
- [ ]  Section « recommandations » sur l'accueil (règles : catégories des réservations/favoris de l'utilisateur) `M · nice`
- [ ]  ~~`GET /recommendations` en service dédié~~ → endpoint dans catalog-service (pas de 8ᵉ service)
- [ ]  ~~ML scikit-learn (filtrage collaboratif)~~ → **reporté** (aucune donnée réelle pour l'entraîner)

---

## 🛠️ Phase 11 — Frontend : Espace Administrateur — **J1 ATTEINT le 14/08** ✅ *(reste les gestions `should/nice`)*

- [x]  Tableau de bord : stats agrégées en temps réel (réservations, CA, clients, activités, dernières réservations)
- [x]  Consultation des utilisateurs (recherche + pagination)
- [x]  Consultation des réservations, activités (avec nb de réservations), paiements
- [x]  Gestion des activités : formulaire créer/modifier, suppression avec garde, upload photo (`/activities/new`, `/activities/:id/edit`)
- [x]  Gestion des catégories (page dédiée : ajout, renommage inline, suppression protégée)
- [x]  Gestion des disponibilités (section créneaux du formulaire activité : ajout, places éditables, suppression)
- [ ]  Gestion des réservations (changer le statut) `S · should` — scan QR `M · should` *(J3)*
- [ ]  Gestion des utilisateurs (activer/désactiver) `S · should` — gestion des rôles `S · nice`
- [ ]  Gestion des promotions et codes de réduction (CRUD) `S · should` *(la validation côté client, elle, est `must` — Phase 6)*
- [ ]  Gestion des avis (consultation / suppression) `S · should`

---

## 🧪 Phase 12 — Tests & qualité — EN COURS → jalon J3

- [x]  Tests pytest du parcours auth (isolation par transaction, 5 tests)
- [x]  Tests unitaires frontend (vitest — redirections post-login)
- [x]  Typecheck strict TypeScript sur les 2 apps + packages (0 erreur)
- [ ]  Tests pytest catalog + booking : **saga nominale, compensation, concurrence sur les places** (2 réservations simultanées sur le dernier créneau) `M · must` *(logique déjà validée hors pytest : 8 threads simultanés sur annulation / confirmation / doublon + expiration + réconciliation, tous verts — reste à formaliser en suite pytest rejouable en CI)*
- [ ]  Tests pytest payment : webhook (signature valide/invalide, idempotence) `S · must`
- [ ]  Tests pytest admin : agrégation BFF (services mockés) `S · should`
- [ ]  Test end-to-end (Playwright) du parcours nominal : inscription → confirmation → réservation → paiement test → QR `M · must` *(un seul parcours E2E solide vaut mieux que dix fragiles)*
- [ ]  Audit responsive + compatibilité navigateurs (Chrome/Firefox/mobile) `S · should`
- [ ]  Audit Lighthouse (performance, accessibilité, SEO) sur accueil/catalogue/détail + corrections rapides `S · should` *(tâche ajoutée — chiffres très valorisables dans le rapport)*
- [ ]  Passe accessibilité de base : labels de formulaires, contrastes, navigation clavier, `alt` des images `S · should` *(tâche ajoutée)*

---

## 🚀 Phase 13 — Déploiement & robustesse → jalon J3

- [x]  Dockeriser tous les services (`Dockerfile` par service + gateway + client Next standalone + nginx)
- [x]  `docker-compose.yml` complet (Postgres, 8 backend, client SSR, web :8080)
- [ ]  CI GitHub Actions : lint + tests backend/frontend + build des images à chaque push `M · must` *(pipeline simple mais vert — très apprécié des jurys)*
- [ ]  Timeouts + retry sur les appels inter-services (`ServiceClient`) + healthchecks/restart dans compose `S · must` *(voir architecture.md §12)*
- [ ]  Logs corrélés : `X-Request-ID` propagé gateway → services `S · should`
- [ ]  Script de sauvegarde/restauration PostgreSQL (`pg_dump` par base + procédure de restore documentée et **testée une fois**) `S · must` *(tâche ajoutée — question classique du jury)*
- [ ]  Déploiement en ligne (VPS + HTTPS + nom de domaine) `M · nice` *(la démo docker-compose locale suffit pour la soutenance — à confirmer avec l'encadrant ; si exigé, passe en `must` et se planifie en J3)*
- [ ]  ~~PostgreSQL managé~~ · ~~monitoring complet (logs centralisés, traces)~~ → **reportés après la soutenance**

---

## 🎓 Phase 14 — Dossier PFE & soutenance — *phase ajoutée, en continu* → jalon J4

> C'est la phase la plus rentable du plan : une grande partie de la note se joue sur le rapport et
> la soutenance, pas sur le code. ~1 jour/semaine dès maintenant.

### Rapport

- [ ]  Cahier des charges : contexte, objectifs, acteurs, besoins fonctionnels / non fonctionnels `M · must`
- [ ]  État de l'art / benchmark : plateformes existantes (GetYourGuide, Viator, acteurs locaux), positionnement de Voyara `S · should`
- [ ]  Diagrammes UML : cas d'utilisation (touriste/admin), diagramme de classes ou MCD par service `M · must`
- [ ]  Diagrammes de séquence : saga de réservation, authentification (repris d'architecture.md, déjà en Mermaid) `S · must`
- [ ]  Diagramme C4 (contexte + conteneurs) — l'ASCII d'architecture.md mis au propre `S · must`
- [ ]  Chapitre architecture : justification des choix (reprendre les ADR d'architecture.md) `M · must`
- [ ]  Chapitre réalisation : captures d'écran, extraits de code significatifs (saga, gateway, SSR) `M · must`
- [ ]  Chapitre tests & qualité : stratégie, résultats, chiffres Lighthouse `S · must`
- [ ]  Section données personnelles / RGPD : données collectées, minimisation, hachage, suppression de compte `S · should`
- [ ]  Perspectives (reprendre la section « Reporté après la soutenance ») `S · must`

### Soutenance

- [ ]  Guide d'utilisation (client + admin, avec captures) `S · must`
- [ ]  Jeu de données de démo soigné : activités avec vraies photos, comptes de test, réservations d'exemple `S · must`
- [ ]  Scénario de démo scripté (parcours client → paiement → QR → vue admin) + plan B (vidéo de secours enregistrée) `M · must`
- [ ]  Slides de soutenance `M · must`
- [ ]  Répétition chronométrée (au moins une à blanc) `S · must`

---

## 🧠 Phase Moteur IA — projet IA & Cognition 5DS

> **Date de présentation IA : à confirmer.**
> Les jalons J1–J4 ci-dessus concernent la **soutenance de la plateforme**, pas cette phase :
> elle n'a pas de date cible tant que la présentation IA n'est pas fixée (seuls les efforts sont estimés).
>
> Décision d'architecture : [ADR-007](architecture.md#adr-007--microservice-ai-dédié-pgvector-et-llm-hybride) ·
> vision, modules, modèle de rapport : [docs/ia/README.md](ia/README.md) · historique : [docs/ia/journal.md](ia/journal.md) ·
> source des étapes : [Guide_Moteur_IA_Voyara.html](../AgentIA_Voyara/Guide_Moteur_IA_Voyara.html) +
> [PresProjCom.pdf](../AgentIA_Voyara/PresProjCom.pdf).
> Chaque étape = une branche `ia/etape-NN` + un rapport dans `docs/ia/rapports/`.
> MVP de la présentation : étapes 0 à 9 (+ la version réduite de l'étape 11).

- [x]  **0 — Cadrage, conventions et architecture cible** (CLAUDE.md, docs/ia/, ADR-007, cette phase) `S · must` — [rapport](ia/rapports/etape-00-cadrage.md)
- [ ]  **1 — Données : points d'intérêt, météo et catalogue de démo** (module 2) — table `pois` dans `voyara_ai`, collecte automatisée de données web OSM/Overpass (≥ 300 POI, ≥ 5 villes) + Open-Meteo avec cache, notebook d'EDA `M · must` *(effort à réévaluer en L avec le seed ci-dessous)*
    - [ ]  **Seed réaliste et idempotent du catalogue** (décision du 11/10/2026 — 8 activités ne suffisent pas pour évaluer recherche, recommandation et solveur) : **≥ 30 activités à Djerba**, **60 à 100 au total sur 5 villes**, avec coordonnées GPS, prix en DT, durées, catégories et **créneaux sur 4 semaines**, traduits **fr / en / ar** (`titre_en/ar`, `description_en/ar`). Script dans `services/catalog/scripts/` (catalog reste propriétaire de ses données), sans écraser les activités existantes `must`
- [ ]  **2 — Enrichissement sémantique du catalogue** (modules 2 & 3) — attributs IA dans catalog (thèmes, public, `niveau_marche`, intérieur, moment idéal), `/internal/activities/export`, pré-étiquetage LLM + validation admin `M · must`
- [ ]  **3 — Service `ai` et couche LLM hybride** — scaffold :8008, gateway `/api/ai`, `LLMProvider` Claude/Ollama + fallback, table `llm_appels`, image `pgvector/pgvector:pg16` `M · must`
    - ⚠ **À trancher à l'étape 3** : changement d'image global (`postgres:16-alpine` → `pgvector/pgvector:pg16`, risque de collation/`REINDEX` sur les bases existantes) **ou** conteneur Postgres **dédié au service ai** (`pgvector/pgvector:pg16`, port hôte **5435**), qui laisse les 5 bases existantes intactes
- [ ]  **4 — Module 1 : comprendre le voyageur (NLU)** — `DemandeVoyage`, `POST /api/ai/comprendre`, 100 demandes annotées (≥ 20 ar/darija), F1 par champ (cible ≥ 0,85 avec Claude) `L · must`
- [ ]  **5 — Module 2 : recherche sémantique et RAG** — `documents_index` pgvector, BM25 + embeddings + RRF, `POST /api/ai/rechercher`, Recall@k / nDCG / MRR `L · must`
- [ ]  **6 — Module 3 : recommandation personnalisée Top-5** — score explicable pondéré + MMR, `POST /api/ai/recommander`, précision@5 + ablation `L · must`
- [ ]  **7 — Modules 4 & 5 : itinéraire et optimisation sous contraintes** — OR-Tools CP-SAT + glouton de secours, ventilation du budget, `POST /api/ai/itineraire`, tests de propriétés (cas Djerba 3 j / 300 DT / famille) `L · must`
- [ ]  **8 — Module 6 : agent intelligent** — boucle à outils, conversations persistées, SSE `POST /api/ai/agent/messages`, 3 scénarios (planifier, modifier, justifier) `L · must`
- [ ]  **9 — Interface voyageur « Planifier mon voyage »** — page `/planifier` (Next), chat streaming, timeline, carte, budget, partage, feedback, fr/en/ar + RTL `L · must`
- [ ]  **10 — Back-office : paramétrage et analytics IA** — paramètres, statistiques, qualité ; agrégation BFF admin ; écrans Vite `M · should`
- [ ]  **11 — Évaluation globale, tests et CI** `M`
    - [ ]  Version réduite : évaluations **NLU, recherche et itinéraire** chiffrées et reproductibles (`docs/ia/resultats/`) `must`
    - [ ]  Reste : bout en bout sur 30 scénarios, LLM-as-judge + évaluation humaine, comparaison Claude vs Ollama complète, CI GitHub Actions du service `ai` `should`
- [ ]  **12 — Sécurité, coûts et RGPD du moteur IA** — jeu adversarial d'injection de prompt, plafonds tokens/coût, masquage PII, suppression RGPD étendue aux conversations `M · should`
- [ ]  **13 — Démo, rapport et soutenance** — seed de démo, `docs/ia/demo.md` + plan B hors-ligne, diagrammes, chapitre « Moteur IA » dans `rapport.tex` `M · must`

---

## ✅ Livrables attendus

- [x]  Application web responsive multilingue (FR/EN/AR + RTL)
- [x]  API REST documentée (Swagger par microservice)
- [x]  Espace client + espace administrateur fonctionnels
- [x]  Authentification complète (inscription, confirmation e-mail, login, mot de passe oublié)
- [x]  Site public **optimisé SEO** (SSR, sitemap, robots, JSON-LD)
- [x]  Documentation technique ([architecture.md](architecture.md))
- [x]  Gestion complète du catalogue depuis l'admin (J1 — atteint le 14/08, une semaine d'avance)
- [ ]  Paiement Stripe opérationnel (montant total) + e-mail + QR code (J2)
- [ ]  Suite de tests + CI verte (J3)
- [ ]  Rapport de PFE + guide d'utilisation + slides (J4)
- [ ]  ~~Recommandations v1 par règles~~ → remplacé par le moteur IA (voir la [phase Moteur IA](#-phase-moteur-ia--projet-ia--cognition-5ds))

---

## 🗃️ Reporté après la soutenance (perspectives)

Volontairement **coupé** du périmètre PFE — à présenter comme perspectives dans le rapport :

- Panier / réservation multi-activités (saga multi-lignes + paiement groupé)
- Paiement par avance/acompte + gestion des remboursements Stripe
- Broker de messages (RabbitMQ/Redis) pour l'asynchrone
- RS256 + JWKS (remplacement du secret HS256 partagé)
- Alembic généralisé à tous les services (aujourd'hui : auth seulement, `AUTO_CREATE_TABLES` ailleurs)
- Routes localisées `/fr|/en|/ar` + hreflang (SEO multilingue)
- PostgreSQL managé, monitoring/observabilité complets (traces distribuées)
- Cartographie avancée (itinéraires, clusters de marqueurs)
- Moteur IA — perspectives de la présentation : **interface Prestataires** (gestion des offres par les
  partenaires), **application mobile**, **interaction vocale**, extension multi-destinations,
  apprentissage des préférences

> *Retiré le 11/10/2026* : les lignes IA/ML (« ML scikit-learn — filtrage collaboratif ») ne sont plus
> des perspectives, car le projet est désormais aussi un projet **IA & Cognition 5DS** dont le moteur IA
> est le livrable principal ([phase Moteur IA](#-phase-moteur-ia--projet-ia--cognition-5ds)).
