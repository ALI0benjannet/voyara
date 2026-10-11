"""Ajoute les colonnes de traduction au catalogue (idempotent).

Le service catalogue crée son schéma avec `Base.metadata.create_all`, qui ne
sait pas modifier une table déjà existante : ce script applique les colonnes
ajoutées après coup (titre/description en EN et AR, nom de catégorie en EN/AR).

Usage (depuis services/catalog) : python scripts/add_translation_columns.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402

STATEMENTS = [
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS titre_en VARCHAR(200)",
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS titre_ar VARCHAR(200)",
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS description_en TEXT",
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS description_ar TEXT",
    "ALTER TABLE categories ADD COLUMN IF NOT EXISTS nom_en VARCHAR(100)",
    "ALTER TABLE categories ADD COLUMN IF NOT EXISTS nom_ar VARCHAR(100)",
]


def main() -> None:
    with engine.begin() as connection:
        for statement in STATEMENTS:
            connection.execute(text(statement))
            print(f"  OK {statement.split('ADD COLUMN IF NOT EXISTS')[1].strip()}")
    print(f"Terminé : {len(STATEMENTS)} colonne(s) vérifiée(s).")


if __name__ == "__main__":
    main()
