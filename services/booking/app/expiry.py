"""Expiration des réservations `pending` non payées.

Une réservation créée mais jamais payée garde ses places décrémentées côté
catalogue : sans expiration, un utilisateur qui abandonne son paiement bloque le
créneau pour tout le monde, indéfiniment.

Ce module passe ces réservations en `cancelled` après
`BOOKING_EXPIRY_MINUTES` et rend les places au catalogue.

Sûreté en concurrence — deux points traités ici :

1. **Course avec le paiement.** Une réservation peut être confirmée pendant le
   balayage. La transition est donc faite par un UPDATE conditionnel
   (`WHERE statut = 'pending'`) : si le paiement a gagné la course, `rowcount`
   vaut 0 et on ne libère pas les places. Une réservation payée n'est jamais
   expirée.

2. **Course entre instances.** Si plusieurs workers du booking-service tournent,
   ils balaient en même temps. Le même UPDATE conditionnel garantit qu'une seule
   instance obtient chaque réservation, donc que les places ne sont libérées
   qu'une fois.

Voir architecture.md §12 n° 2.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.config import settings
from app.database import SessionLocal
from app.models import Booking, BookingStatus

logger = logging.getLogger(__name__)


def _expiry_cutoff() -> datetime:
    """Instant avant lequel une réservation `pending` est considérée abandonnée.

    `date_reservation` est stocké en `DateTime` sans fuseau (naïf, heure du
    serveur de base) : on compare donc avec un datetime naïf lui aussi, sinon
    PostgreSQL refuse la comparaison.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=settings.BOOKING_EXPIRY_MINUTES
    )


async def expire_pending_bookings() -> dict[str, int]:
    """Annule les réservations `pending` trop anciennes et libère leurs places.

    Retourne un compte-rendu : réservations expirées, places rendues, échecs de
    libération (journalisés pour rejeu manuel).
    """
    # Import tardif : `routers` importe ce module pour l'endpoint interne, un
    # import en tête de fichier créerait un cycle.
    from app.routers import _release_seats

    cutoff = _expiry_cutoff()
    expired = released = failed = 0

    db = SessionLocal()
    try:
        candidates = db.scalars(
            select(Booking).where(
                Booking.statut == BookingStatus.pending,
                Booking.date_reservation < cutoff,
            )
        ).all()

        # On capture les valeurs avant tout commit : après, l'objet peut être
        # expiré par SQLAlchemy et déclencher un rechargement inutile.
        targets = [
            (b.id, b.availability_id, int(b.nb_places or 1), b.date_reservation) for b in candidates
        ]
    finally:
        db.close()

    for booking_id, availability_id, seats, created_at in targets:
        db = SessionLocal()
        try:
            # Transition atomique : perd la course contre un paiement en cours,
            # ce qui est le comportement voulu.
            result = db.execute(
                update(Booking)
                .where(Booking.id == booking_id, Booking.statut == BookingStatus.pending)
                .values(statut=BookingStatus.cancelled)
            )
            db.commit()
        finally:
            db.close()

        if result.rowcount == 0:
            # Payée ou annulée entre la sélection et maintenant : on n'y touche pas.
            logger.info(
                "Reservation #%s confirmee ou annulee pendant le balayage — non expiree",
                booking_id,
            )
            continue

        expired += 1
        if await _release_seats(
            availability_id, seats, reason=f"expiration booking #{booking_id}"
        ):
            released += seats
        else:
            failed += 1

        logger.info(
            "Reservation #%s expiree (creee le %s, %s place(s) rendue(s))",
            booking_id,
            created_at,
            seats,
        )

    if expired:
        logger.info(
            "Balayage : %s reservation(s) expiree(s), %s place(s) rendue(s), %s echec(s)",
            expired,
            released,
            failed,
        )

    return {"expired": expired, "seats_released": released, "release_failures": failed}


async def expiry_sweeper() -> None:
    """Boucle de fond : balaie périodiquement les réservations abandonnées.

    Lancée au démarrage du service (voir `main.py`). Toute erreur est capturée :
    une exception non gérée tuerait la tâche et l'expiration s'arrêterait
    silencieusement jusqu'au prochain redémarrage.
    """
    interval = settings.BOOKING_EXPIRY_SWEEP_SECONDS
    logger.info(
        "Expiration des reservations active : pending > %s min, balayage toutes les %s s",
        settings.BOOKING_EXPIRY_MINUTES,
        interval,
    )
    while True:
        try:
            await expire_pending_bookings()
        except asyncio.CancelledError:
            raise  # arrêt du service : on laisse remonter
        except Exception:
            logger.exception("Balayage des reservations expirees en echec — nouvelle tentative")
        await asyncio.sleep(interval)
