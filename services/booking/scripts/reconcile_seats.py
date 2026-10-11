"""Réconciliation des places entre le booking-service et le catalog-service.

Pourquoi ce script — les deux services ont chacun leur base, sans transaction
commune. La saga de réservation les garde cohérents en fonctionnement normal,
mais deux situations peuvent les désynchroniser :

  * une compensation qui échoue (catalog injoignable au mauvais moment) laisse
    des places décrémentées sans réservation en face — des « places fantômes »
    invisibles pour les clients ;
  * un crash entre le `reserve` et l'INSERT de la réservation produit le même
    effet.

Ces cas sont journalisés en `error` par `_release_seats`, mais rien ne les
rattrape. Ce script compare les deux sources et rétablit la vérité :

    places_disponibles  ==  places_totales - somme(nb_places des bookings actifs)

Il lit les deux bases directement (pas d'API) : c'est un outil d'exploitation,
exécuté par un opérateur, pas un endpoint exposé.

Usage (depuis services/booking) :
    python scripts/reconcile_seats.py            # diagnostic seul (aucune écriture)
    python scripts/reconcile_seats.py --fix      # corrige les écarts détectés

Voir architecture.md §12 n° 3.
"""

import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import create_engine, func, select, text  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Booking, BookingStatus  # noqa: E402


def catalog_database_url() -> str:
    """URL de la base catalogue, déduite de celle du booking-service.

    Les deux bases vivent sur le même serveur PostgreSQL (docker-compose) ;
    seul le nom de la base change.
    """
    return settings.DATABASE_URL.replace(settings.POSTGRES_DB, "voyara_catalog")


def reserved_seats_by_slot() -> dict[int, int]:
    """Places réellement engagées, d'après les réservations non annulées."""
    db = SessionLocal()
    try:
        rows = db.execute(
            select(Booking.availability_id, func.sum(Booking.nb_places))
            .where(Booking.statut != BookingStatus.cancelled)
            .group_by(Booking.availability_id)
        ).all()
        return {int(slot): int(seats or 0) for slot, seats in rows if slot is not None}
    finally:
        db.close()


def bookings_by_slot() -> dict[int, list[tuple[int, str, int]]]:
    """Détail des réservations actives, pour expliquer chaque écart."""
    db = SessionLocal()
    try:
        rows = db.execute(
            select(Booking.availability_id, Booking.id, Booking.statut, Booking.nb_places)
            .where(Booking.statut != BookingStatus.cancelled)
            .order_by(Booking.availability_id, Booking.id)
        ).all()
        grouped: dict[int, list[tuple[int, str, int]]] = defaultdict(list)
        for slot, booking_id, statut, seats in rows:
            if slot is not None:
                grouped[int(slot)].append((int(booking_id), statut.value, int(seats or 1)))
        return grouped
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Corrige les écarts (sans cette option : diagnostic seul)",
    )
    args = parser.parse_args()

    reserved = reserved_seats_by_slot()
    details = bookings_by_slot()
    catalog_engine = create_engine(catalog_database_url(), pool_pre_ping=True)

    with catalog_engine.connect() as connection:
        slots = connection.execute(
            text(
                """
                SELECT a.id, a.activity_id, a.places_disponibles, a.places_totales,
                       act.titre
                FROM availabilities a
                LEFT JOIN activities act ON act.id = a.activity_id
                ORDER BY a.id
                """
            )
        ).all()

    anomalies: list[dict] = []
    orphans = set(reserved) - {row[0] for row in slots}

    for slot_id, activity_id, disponibles, totales, titre in slots:
        engaged = reserved.get(slot_id, 0)
        expected = (totales or 0) - engaged

        if disponibles == expected:
            continue

        anomalies.append(
            {
                "slot": slot_id,
                "activity": titre or f"#{activity_id}",
                "disponibles": disponibles,
                "totales": totales or 0,
                "engaged": engaged,
                "expected": expected,
                "delta": disponibles - expected,
                "bookings": details.get(slot_id, []),
            }
        )

    # ---------------------------------------------------------------- rapport
    print("=" * 72)
    print("RECONCILIATION DES PLACES  (catalog <-> booking)")
    print("=" * 72)
    print(f"Créneaux analysés            : {len(slots)}")
    print(f"Créneaux avec réservations   : {len(reserved)}")
    print(f"Incohérences détectées       : {len(anomalies)}")
    print()

    if orphans:
        print(f"!! {len(orphans)} réservation(s) sur un créneau INEXISTANT côté catalogue :")
        for slot_id in sorted(orphans):
            items = ", ".join(f"#{b} ({s}, {n} pl.)" for b, s, n in details.get(slot_id, []))
            print(f"   créneau #{slot_id} : {items}")
        print("   -> créneau supprimé alors que des réservations existaient.")
        print("      À traiter manuellement (annuler les réservations ou recréer le créneau).")
        print()

    if not anomalies:
        print("Aucun écart : les deux services sont cohérents.")
        return

    for item in anomalies:
        signe = "+" if item["delta"] > 0 else ""
        nature = (
            "places FANTOMES (bloquées sans réservation)"
            if item["delta"] < 0
            else "places EN TROP (réservations non décomptées)"
        )
        print(f"Créneau #{item['slot']} — {item['activity']}")
        print(f"   capacité                 : {item['totales']}")
        print(f"   réservées (bookings)     : {item['engaged']}")
        print(f"   disponibles attendues    : {item['expected']}")
        print(f"   disponibles constatées   : {item['disponibles']}   (écart {signe}{item['delta']})")
        print(f"   -> {nature}")
        for booking_id, statut, seats in item["bookings"]:
            print(f"      booking #{booking_id} : {seats} place(s), {statut}")
        print()

    if not args.fix:
        print("Diagnostic seul — relancez avec --fix pour corriger.")
        return

    # ---------------------------------------------------------------- correction
    with catalog_engine.begin() as connection:
        for item in anomalies:
            connection.execute(
                text("UPDATE availabilities SET places_disponibles = :v WHERE id = :id"),
                {"v": max(0, item["expected"]), "id": item["slot"]},
            )
            print(
                f"  CORRIGE créneau #{item['slot']} : "
                f"{item['disponibles']} -> {max(0, item['expected'])} places"
            )

    print(f"\nTerminé : {len(anomalies)} créneau(x) réaligné(s) sur les réservations réelles.")


if __name__ == "__main__":
    main()
