# Modèle de données Voyara (MCD)

> Généré depuis les modèles SQLAlchemy réels (14/08/2026). Architecture
> **database-per-service** : chaque diagramme correspond à une base distincte ;
> les références inter-services (pointillés du dernier schéma) sont de simples
> entiers **sans clé étrangère**, validés par appel API (voir
> [architecture.md — ADR-002](architecture.md#adr-002--une-base-postgresql-par-service)).

## 1. Base `voyara` — auth-service

```mermaid
erDiagram
    USERS {
        int id PK
        string nom
        string prenom
        string email UK "index"
        string hashed_password "pbkdf2_sha256"
        enum role "admin=1 | tourist=2"
        string preferences "nullable"
        datetime date_inscription
        bool is_active
        bool is_verified
        datetime email_verified_at "nullable"
        string preferred_language "fr par defaut"
        string phone "nullable"
        string avatar_url "nullable"
        datetime created_at
        datetime updated_at
    }
    REFRESH_TOKENS {
        uuid id PK
        int user_id FK "ON DELETE CASCADE"
        string token_hash UK "SHA-256, index"
        datetime expires_at
        bool revoked
        string user_agent "nullable"
    }
    EMAIL_VERIFICATION_TOKENS {
        uuid id PK
        int user_id FK "ON DELETE CASCADE"
        string token_hash "index"
        datetime expires_at
        datetime used_at "nullable = non utilise"
    }
    PASSWORD_RESET_TOKENS {
        uuid id PK
        int user_id FK "ON DELETE CASCADE"
        string token_hash UK "index"
        datetime expires_at
        datetime used_at "nullable = non utilise"
    }

    USERS ||--o{ REFRESH_TOKENS : "possede"
    USERS ||--o{ EMAIL_VERIFICATION_TOKENS : "recoit"
    USERS ||--o{ PASSWORD_RESET_TOKENS : "recoit"
```

## 2. Base `voyara_catalog` — catalog-service

```mermaid
erDiagram
    CATEGORIES {
        int id PK
        string nom UK
    }
    ACTIVITIES {
        int id PK
        string titre
        text description
        float prix
        int duree "minutes"
        string localisation
        float latitude "nullable"
        float longitude "nullable"
        text photos "nullable — /static/activities/…"
        int category_id FK
    }
    AVAILABILITIES {
        int id PK
        int activity_id FK
        date date
        time heure
        int places_disponibles "decrement atomique"
    }

    CATEGORIES ||--o{ ACTIVITIES : "classe"
    ACTIVITIES ||--o{ AVAILABILITIES : "propose"
```

### Offres de voyage (tables préparées, API à venir)

Onglets Séjours, Vols, Voitures de location et Transferts de la navbar. Tables
indépendantes, sans relation entre elles ni avec les activités.

```mermaid
erDiagram
    STAYS {
        int id PK
        string nom
        string type "hotel | riad | maison_hotes | appartement"
        text description
        string localisation
        float latitude "nullable"
        float longitude "nullable"
        int etoiles "nullable, 1 a 5"
        float prix_nuit
        int capacite "voyageurs max"
        text equipements "nullable"
        text photos "nullable"
        bool actif
    }
    FLIGHTS {
        int id PK
        string compagnie
        string numero_vol "index"
        string aeroport_depart "IATA"
        string aeroport_arrivee "IATA"
        string ville_depart
        string ville_arrivee
        datetime depart_le
        datetime arrivee_le
        string classe "economy | business"
        float prix
        int places_disponibles
        int places_totales
    }
    CAR_RENTALS {
        int id PK
        string marque
        string modele
        string categorie "economique | compacte | suv | van"
        string transmission "manuelle | automatique"
        string carburant
        int nb_places
        string agence
        string localisation "prise en charge"
        float prix_jour
        text photos "nullable"
        bool disponible
    }
    TRANSFERS {
        int id PK
        string depart
        string arrivee
        string type_vehicule "taxi | grand_taxi | berline | van | minibus"
        int capacite
        int bagages
        int duree "minutes"
        float prix "par vehicule"
        text description "nullable"
        bool actif
    }
```

## 3. Base `voyara_booking` — booking-service

```mermaid
erDiagram
    PROMO_CODES {
        int id PK
        string code UK "index"
        float reduction "pourcentage"
        date date_expiration
        bool actif
    }
    BOOKINGS {
        int id PK
        int user_id "ref auth (sans FK)"
        int activity_id "ref catalog (sans FK)"
        int availability_id "ref catalog (sans FK)"
        int promo_code_id FK "nullable"
        datetime date_reservation
        enum statut "pending | confirmed | cancelled"
        string qr_code "nullable — Phase 9"
        float montant_total "prix x nb_places, promo deduit"
        int nb_places "1 a 8"
    }

    PROMO_CODES ||--o{ BOOKINGS : "remise"
```

## 4. Base `voyara_payment` — payment-service

```mermaid
erDiagram
    PAYMENTS {
        int id PK
        int booking_id "ref booking (sans FK), index"
        float montant
        enum type "full | deposit"
        string methode "stripe par defaut"
        enum statut "pending | succeeded | failed"
        string stripe_intent_id "nullable — Phase 8"
        datetime date_paiement
    }
```

## 5. Base `voyara_review` — review-service

```mermaid
erDiagram
    REVIEWS {
        int id PK
        int user_id "ref auth (sans FK), index"
        int activity_id "ref catalog (sans FK), index"
        int note "1 a 5"
        text commentaire "nullable"
        datetime date
    }
    FAVORITES {
        int id PK
        int user_id "ref auth (sans FK)"
        int activity_id "ref catalog (sans FK)"
    }
```

> `FAVORITES` : contrainte d'unicité `(user_id, activity_id)` — un favori par
> utilisateur et par activité.

## 5 bis. Base `voyara_ai` — moteur IA (conteneur `postgres-ai`, port 5435)

> Ajoutée à l'étape 1 du moteur IA (13/10/2026, [ADR-007](architecture.md#adr-007--microservice-ai-dédié-pgvector-et-llm-hybride)).
> Modèles : `services/ai/app/models.py`. Aucune référence vers les autres bases : une activité
> du catalogue est rapprochée d'un POI par ses coordonnées GPS, jamais par clé.

```mermaid
erDiagram
    POIS {
        int id PK
        string type "restaurant|plage|musee|monument|souk|parc|cafe"
        string nom
        string nom_en "nullable"
        string nom_ar "nullable"
        string ville "index (ville, type)"
        float latitude
        float longitude
        text horaires_ouverture "OSM opening_hours brut, nullable"
        json horaires_normalises "par jour, nullable si non analysable"
        float prix_moyen "DT, nullable"
        json tags "tags OSM complets"
        string source "osm"
        string source_id UK "node/123, way/456 : cle de l'upsert"
        datetime maj_le
    }
    METEO_CACHE {
        int id PK
        string ville "unique (ville, date)"
        date date
        float temp_min "nullable"
        float temp_max "nullable"
        float precipitations "mm, nullable"
        int code_meteo "WMO, nullable"
        datetime maj_le "expire apres 6 h"
    }
```

## 6. Vue d'ensemble — relations inter-services (logiques, sans FK)

```mermaid
erDiagram
    USERS ||--o{ BOOKINGS : "reserve (user_id)"
    USERS ||--o{ REVIEWS : "note (user_id)"
    USERS ||--o{ FAVORITES : "aime (user_id)"
    ACTIVITIES ||--o{ BOOKINGS : "objet de (activity_id)"
    AVAILABILITIES ||--o{ BOOKINGS : "creneau de (availability_id)"
    ACTIVITIES ||--o{ REVIEWS : "evaluee par (activity_id)"
    ACTIVITIES ||--o{ FAVORITES : "favorite de (activity_id)"
    BOOKINGS ||--o{ PAYMENTS : "reglee par (booking_id)"

    USERS { int id PK }
    ACTIVITIES { int id PK }
    AVAILABILITIES { int id PK }
    BOOKINGS { int id PK }
    PAYMENTS { int id PK }
    REVIEWS { int id PK }
    FAVORITES { int id PK }
```

**Règles de cohérence applicative** (remplacent les FK inter-services) :
- La création d'une réservation **vérifie** l'activité et le créneau via l'API du
  catalog-service (saga, [architecture.md §4.5](architecture.md#45-saga-de-réservation-multi-voyageurs)).
- La suppression d'une activité est **refusée** s'il existe des réservations
  (garde inter-services 409).
- Le dépôt d'un avis est **refusé** si l'utilisateur n'a pas de réservation non
  annulée de l'activité (`has-booked`).
- La suppression de compte **anonymise** l'utilisateur au lieu de le supprimer :
  les `user_id` référencés ailleurs restent valides.
