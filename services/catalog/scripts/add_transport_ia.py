"""Ouvre les hébergements et le transport au moteur IA (étape 2-bis) — idempotent.

`create_all` ne modifie pas une table existante et catalog n'utilise pas
Alembic : ce script applique la migration sur une base déjà remplie, sans
toucher aux données existantes. Il ne fait que des ajouts :
  1. table `aeroports` + les 14 aéroports du référentiel (app/lieux.py),
     insérés seulement s'ils manquent (une correction admin n'est pas écrasée) ;
  2. `stays.modifie_le` + index + trigger (synchronisation incrémentale) ;
  3. colonnes de lieu `car_rentals.ville / aeroport` et
     `transfers.ville_depart / ville_arrivee / aeroport_depart / aeroport_arrivee` ;
  4. remplissage de ces colonnes, uniquement là où elles sont vides, à partir
     des libellés existants (`deduire_lieu`) ; les libellés non résolus sont listés.
Tout passe dans une seule transaction : en cas d'erreur, rien n'est appliqué.
Faire un `pg_dump` avant reste la règle (voir RUN.md).

Usage (depuis services/catalog) :
    python scripts/add_transport_ia.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import text  # noqa: E402
from sqlalchemy.dialects.postgresql import insert  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import engine  # noqa: E402
from app.lieux import AEROPORTS_REFERENCE, completer_lieux  # noqa: E402
from app.models import Aeroport, CarRental, Flight, Stay, Transfer, ddl_trigger_modifie_le  # noqa: E402

COLONNES = [
    "ALTER TABLE stays ADD COLUMN IF NOT EXISTS modifie_le TIMESTAMPTZ NOT NULL DEFAULT now()",
    "CREATE INDEX IF NOT EXISTS ix_stays_modifie_le ON stays (modifie_le)",
    "ALTER TABLE car_rentals ADD COLUMN IF NOT EXISTS ville VARCHAR(100)",
    "ALTER TABLE car_rentals ADD COLUMN IF NOT EXISTS aeroport VARCHAR(3)",
    "CREATE INDEX IF NOT EXISTS ix_car_rentals_ville ON car_rentals (ville)",
    "ALTER TABLE transfers ADD COLUMN IF NOT EXISTS ville_depart VARCHAR(100)",
    "ALTER TABLE transfers ADD COLUMN IF NOT EXISTS ville_arrivee VARCHAR(100)",
    "ALTER TABLE transfers ADD COLUMN IF NOT EXISTS aeroport_depart VARCHAR(3)",
    "ALTER TABLE transfers ADD COLUMN IF NOT EXISTS aeroport_arrivee VARCHAR(3)",
    "CREATE INDEX IF NOT EXISTS ix_transfers_ville_depart ON transfers (ville_depart)",
    "CREATE INDEX IF NOT EXISTS ix_transfers_ville_arrivee ON transfers (ville_arrivee)",
]


def main() -> None:
    with engine.begin() as connection:
        # 1. Référentiel des aéroports (checkfirst : la table peut déjà exister).
        cree = not engine.dialect.has_table(connection, Aeroport.__tablename__)
        Aeroport.__table__.create(connection, checkfirst=True)  # le listener la remplit si créée
        ajoutes = connection.execute(
            insert(Aeroport).values(list(AEROPORTS_REFERENCE))
            .on_conflict_do_nothing(index_elements=["code_iata"])
            .returning(Aeroport.code_iata)
        ).fetchall()

        # 2-3. Colonnes et trigger.
        for instruction in COLONNES:
            connection.execute(text(instruction))
        for instruction in ddl_trigger_modifie_le("stays"):
            connection.execute(text(instruction))

        # 4. Remplissage des lieux vides, dans la même transaction.
        session = Session(bind=connection)
        aeroports = session.query(Aeroport).all()
        voitures = session.query(CarRental).filter(CarRental.ville.is_(None)).all()
        transferts = session.query(Transfer).filter(
            Transfer.ville_depart.is_(None) | Transfer.ville_arrivee.is_(None)
        ).all()
        for offre in (*voitures, *transferts):
            completer_lieux(offre, aeroports)
        session.flush()

        non_resolus = [f"voiture n° {v.id} : {v.localisation!r}" for v in voitures if not v.ville]
        for t in transferts:
            for sens in ("depart", "arrivee"):
                if not getattr(t, f"ville_{sens}"):
                    non_resolus.append(f"transfert n° {t.id} ({sens}) : {getattr(t, sens)!r}")

        comptes = {
            "séjours": session.query(Stay).count(),
            "vols": session.query(Flight).count(),
            "voitures": session.query(CarRental).count(),
            "transferts": session.query(Transfer).count(),
            "aéroports": len(aeroports),
        }
        avec_aeroport = (
            session.query(CarRental).filter(CarRental.aeroport.isnot(None)).count(),
            session.query(Transfer).filter(
                Transfer.aeroport_depart.isnot(None) | Transfer.aeroport_arrivee.isnot(None)
            ).count(),
        )
        session.close()

    print(f"Table aeroports {'créée' if cree else 'déjà présente'} ; "
          f"{len(ajoutes) if not cree else len(AEROPORTS_REFERENCE)} aéroport(s) ajouté(s).")
    print(f"Lieux complétés : {len(voitures)} voiture(s), {len(transferts)} transfert(s) "
          f"({avec_aeroport[0]} voitures et {avec_aeroport[1]} transferts liés à un aéroport).")
    if non_resolus:
        print(f"{len(non_resolus)} libellé(s) non résolu(s) — à corriger dans l'admin :")
        for ligne in non_resolus:
            print(f"  - {ligne}")
    else:
        print("Tous les libellés sont résolus.")
    print("Conservé(e)s : " + ", ".join(f"{n} {k}" for k, n in comptes.items()) + ".")


if __name__ == "__main__":
    main()
