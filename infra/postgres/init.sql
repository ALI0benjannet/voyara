-- Exécuté automatiquement au premier démarrage du conteneur Postgres.
-- La base `voyara` (auth) est créée via la variable POSTGRES_DB.
-- Une base par service = isolation des données (database-per-service).

CREATE DATABASE voyara_catalog;
CREATE DATABASE voyara_booking;
CREATE DATABASE voyara_payment;
CREATE DATABASE voyara_review;
