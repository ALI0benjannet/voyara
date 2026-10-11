"""Ajoute `places_totales` aux créneaux (idempotent).

Le catalog-service crée son schéma avec `Base.metadata.create_all`, qui ne
modifie pas une table existante : ce script applique la colonne ajoutée après
coup.

`places_disponibles` est un compteur décrémenté à chaque réservation. Seul, il
ne permet pas de vérifier quoi que ce soit : « 6 places » est-il correct ? Il
faut connaître la capacité d'origine. `places_totales` la fige à la création du
créneau et sert de référence au script de réconciliation
(`services/booking/scripts/reconcile_seats.py`).

Initialisation des créneaux existants : `places_totales` vaut `places_disponibles`
augmenté des places déjà réservées. Ce nombre n'est pas connu du catalogue (il
vit dans le booking-service) : il doit donc être fourni via `--reserved`, sous
la forme `availability_id:places`. Sans cette option, la capacité est initialisée
à `places_disponibles`, ce qui est correct uniquement si aucune réservation
active n'existe encore.

Usage (depuis services/catalog) :
    python scripts/add_places_totales.py
    python scripts/add_places_totales.py --reserved 1:2,7:4
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402

ADD_COLUMN = """
ALTER TABLE availabilities
ADD COLUMN IF NOT EXISTS places_totales INTEGER NOT NULL DEFAULT 0
"""

# On ne réinitialise que les créneaux jamais initialisés (places_totales = 0),
# pour que le script puisse être relancé sans écraser une capacité correcte.
INIT_DEFAULT = """
UPDATE availabilities
SET places_totales = places_disponibles
WHERE places_totales = 0
"""

INIT_WITH_RESERVED = """
UPDATE availabilities
SET places_totales = places_disponibles + :reserved
WHERE id = :id AND places_totales = 0
"""


def parse_reserved(raw: str | None) -> dict[int, int]:
    """« 1:2,7:4 » -> {1: 2, 7: 4}."""
    if not raw:
        return {}
    result: dict[int, int] = {}
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            availability_id, seats = chunk.split(":")
            result[int(availability_id)] = int(seats)
        except ValueError:
            raise SystemExit(f"Format invalide : « {chunk} » (attendu id:places)")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reserved",
        help="Places déjà réservées par créneau, ex. « 1:2,7:4 » "
        "(à récupérer via reconcile_seats.py)",
    )
    args = parser.parse_args()
    reserved = parse_reserved(args.reserved)

    with engine.begin() as connection:
        connection.execute(text(ADD_COLUMN))
        print("  OK colonne places_totales")

        for availability_id, seats in reserved.items():
            result = connection.execute(
                text(INIT_WITH_RESERVED), {"id": availability_id, "reserved": seats}
            )
            if result.rowcount:
                print(f"  OK créneau #{availability_id} : capacité = disponibles + {seats}")

        result = connection.execute(text(INIT_DEFAULT))
        if result.rowcount:
            print(f"  OK {result.rowcount} créneau(x) initialisé(s) à places_disponibles")

    print("Terminé : places_totales en place.")


if __name__ == "__main__":
    main()
