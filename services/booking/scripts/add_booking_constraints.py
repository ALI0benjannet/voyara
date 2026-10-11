"""Contraintes de concurrence sur les réservations (idempotent).

Le booking-service crée son schéma avec `Base.metadata.create_all`, qui ne sait
pas modifier une table existante : ce script applique l'index d'unicité ajouté
après coup.

`uq_booking_active_user_slot` empêche un même utilisateur d'avoir deux
réservations actives sur le même créneau. C'est la seule protection anti-doublon
fiable en concurrence : un contrôle en Python laisserait passer deux requêtes
simultanées (double-clic, requête rejouée après un timeout réseau).

L'index est partiel (`WHERE statut <> 'cancelled'`) pour qu'un utilisateur
puisse re-réserver un créneau qu'il avait annulé.

Usage (depuis services/booking) : python scripts/add_booking_constraints.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402

DUPLICATES_QUERY = """
SELECT user_id, availability_id, COUNT(*) AS n
FROM bookings
WHERE statut <> 'cancelled'
GROUP BY user_id, availability_id
HAVING COUNT(*) > 1
"""

CREATE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_booking_active_user_slot
ON bookings (user_id, availability_id)
WHERE statut <> 'cancelled'
"""


def main() -> None:
    with engine.begin() as connection:
        # Un index unique échoue si des doublons existent déjà : on prévient
        # avec un message clair plutôt qu'une erreur SQL brute.
        duplicates = connection.execute(text(DUPLICATES_QUERY)).fetchall()
        if duplicates:
            print(f"  ! {len(duplicates)} doublon(s) actif(s) à traiter avant l'index :")
            for user_id, availability_id, count in duplicates:
                print(f"      user={user_id} availability={availability_id} ({count} réservations)")
            print("  Annulez les réservations en trop, puis relancez ce script.")
            raise SystemExit(1)

        connection.execute(text(CREATE_INDEX))
        print("  OK uq_booking_active_user_slot (user_id, availability_id) WHERE actif")

    print("Terminé : contrainte anti-doublon en place.")


if __name__ == "__main__":
    main()
