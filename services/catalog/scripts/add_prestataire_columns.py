"""Ajoute les colonnes de l'espace prestataire aux activités (idempotent).

`create_all` ne modifie pas une table existante : ce script applique
`statut` (modération) et `prestataire_id` (propriétaire). Les activités déjà
en base restent publiées.

Usage (depuis services/catalog) :
    python scripts/add_prestataire_columns.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402

STATEMENTS = [
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS statut VARCHAR(20) NOT NULL DEFAULT 'publiee'",
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS prestataire_id INTEGER",
    "CREATE INDEX IF NOT EXISTS ix_activities_statut ON activities (statut)",
    "CREATE INDEX IF NOT EXISTS ix_activities_prestataire_id ON activities (prestataire_id)",
]


def main() -> None:
    with engine.begin() as connection:
        for statement in STATEMENTS:
            connection.execute(text(statement))
    print("Terminé : colonnes statut et prestataire_id en place.")


if __name__ == "__main__":
    main()
