"""Ajoute les attributs IA aux activités (étape 2 du moteur IA) — idempotent.

`create_all` ne modifie pas une table existante et catalog n'utilise pas
Alembic : ce script applique la migration sur une base déjà remplie, sans
toucher aux données. Il ne fait que des ajouts :
  1. colonnes themes, public, niveau_marche, interieur, moment_ideal,
     tags_valides, tags_proposes, modifie_le (`ADD COLUMN IF NOT EXISTS`,
     valeurs par défaut neutres : listes vides, NULL, tags non validés) ;
  2. contraintes CHECK, lues dans le modèle (une seule source de vérité),
     ajoutées seulement si elles n'existent pas ;
  3. trigger qui met à jour `modifie_le` à chaque UPDATE.
Tout passe dans une seule transaction : en cas d'erreur, rien n'est appliqué.
Faire un `pg_dump` avant reste la règle (voir RUN.md).

Usage (depuis services/catalog) :
    python scripts/add_tags_ia_columns.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import CheckConstraint, text  # noqa: E402

from app.database import engine  # noqa: E402
from app.models import DDL_TRIGGER_MODIFIE_LE, Activity  # noqa: E402

COLONNES = [
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS themes JSONB NOT NULL DEFAULT '[]'::jsonb",
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS public JSONB NOT NULL DEFAULT '[]'::jsonb",
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS niveau_marche INTEGER",
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS interieur BOOLEAN",
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS moment_ideal VARCHAR(20)",
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS tags_valides BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS tags_proposes JSONB",
    "ALTER TABLE activities ADD COLUMN IF NOT EXISTS modifie_le TIMESTAMPTZ NOT NULL DEFAULT now()",
    "CREATE INDEX IF NOT EXISTS ix_activities_tags_valides ON activities (tags_valides)",
    "CREATE INDEX IF NOT EXISTS ix_activities_modifie_le ON activities (modifie_le)",
]


def main() -> None:
    contraintes = [
        c for c in Activity.__table__.constraints
        if isinstance(c, CheckConstraint) and c.name
    ]
    ajoutees = 0
    with engine.begin() as connection:
        for instruction in COLONNES:
            connection.execute(text(instruction))
        for contrainte in contraintes:
            existe = connection.scalar(
                text("SELECT 1 FROM pg_constraint WHERE conname = :nom"),
                {"nom": contrainte.name},
            )
            if not existe:
                connection.execute(text(
                    f"ALTER TABLE activities ADD CONSTRAINT {contrainte.name} "
                    f"CHECK ({contrainte.sqltext})"
                ))
                ajoutees += 1
        for instruction in DDL_TRIGGER_MODIFIE_LE:
            connection.execute(text(instruction))
        total = connection.scalar(text("SELECT count(*) FROM activities"))
    print(
        f"Terminé : 8 colonnes IA en place, {ajoutees} contrainte(s) ajoutée(s) "
        f"sur {len(contraintes)}, trigger modifie_le à jour. {total} activité(s) conservée(s)."
    )


if __name__ == "__main__":
    main()
