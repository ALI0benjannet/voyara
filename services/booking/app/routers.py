import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import qrcode
import qrcode.image.svg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from voyara_common.auth import TokenIdentity, get_current_identity
from voyara_common.internal import ServiceClient, require_internal_key
from voyara_common.pagination import paginate

from app.config import settings
from app.database import get_db
from app.models import Booking, BookingStatus, PromoCode

logger = logging.getLogger(__name__)

catalog = ServiceClient(settings.CATALOG_SERVICE_URL)
auth = ServiceClient(settings.AUTH_SERVICE_URL)
notification = ServiceClient(settings.NOTIFICATION_SERVICE_URL)

# ---------------------------------------------------------------------------
# Routes publiques (utilisateur connecté)
# ---------------------------------------------------------------------------

public_router = APIRouter(prefix="/bookings", tags=["Réservations"])


class BookingCreate(BaseModel):
    activity_id: int
    availability_id: int
    guests: int = 1  # nombre de voyageurs (1-8)
    promo_code: str | None = None


class PromoValidateIn(BaseModel):
    code: str


def _find_valid_promo(db: Session, code: str) -> PromoCode:
    """Retourne le code promo actif et non expire, sinon leve une HTTPException."""
    from datetime import date as date_type

    promo = db.scalar(select(PromoCode).where(func.lower(PromoCode.code) == code.strip().lower()))
    if not promo:
        raise HTTPException(status_code=404, detail="Code promo inconnu")
    if not promo.actif:
        raise HTTPException(status_code=410, detail="Code promo desactive")
    if promo.date_expiration < date_type.today():
        raise HTTPException(status_code=410, detail="Code promo expire")
    return promo


async def _release_seats(availability_id: int, seats: int, *, reason: str) -> bool:
    """Rend des places au catalogue (compensation de saga).

    Ne lève jamais : l'appelant est déjà en train de traiter une erreur, et
    échouer ici masquerait la cause d'origine. Un échec est journalisé en
    `error` avec toutes les données nécessaires pour rejouer l'opération
    manuellement — sans quoi les places resteraient bloquées indéfiniment.

    Retourne True si les places ont bien été libérées.
    """
    try:
        await catalog.post(
            f"/internal/availabilities/{availability_id}/release",
            params={"seats": seats},
        )
        return True
    except httpx.HTTPError:
        logger.error(
            "COMPENSATION ECHOUEE (%s) : %s place(s) non liberee(s) sur "
            "availability_id=%s — rejouer : POST /internal/availabilities/%s/release?seats=%s",
            reason,
            seats,
            availability_id,
            availability_id,
            seats,
        )
        return False


def _booking_dict(b: Booking, activities: dict[int, dict] | None = None) -> dict:
    """Sérialise une réservation, enrichie des infos d'activité quand le
    catalog-service a répondu (titre traduit et vignette)."""
    info = (activities or {}).get(b.activity_id) or {}
    return {
        "id": b.id,
        "user_id": b.user_id,
        "activity_id": b.activity_id,
        "activity": info.get("titre"),
        "activity_titre_en": info.get("titre_en"),
        "activity_titre_ar": info.get("titre_ar"),
        "activity_photo": info.get("photos"),
        "availability_id": b.availability_id,
        "statut": b.statut.value,
        "montant_total": float(b.montant_total or 0.0),
        "nb_places": int(getattr(b, "nb_places", 1) or 1),
        "qr_code": b.qr_code,
        "date_reservation": b.date_reservation,
    }


@public_router.get("")
async def my_bookings(
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    stmt = select(Booking).where(Booking.user_id == identity.user_id)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.scalars(
        stmt.order_by(Booking.date_reservation.desc()).offset((page - 1) * size).limit(size)
    ).all()

    # Enrichissement : titres et vignettes depuis le catalog-service
    activities: dict[int, dict] = {}
    activity_ids = sorted({b.activity_id for b in rows})
    if activity_ids:
        try:
            data = await catalog.get(
                "/internal/activities/batch", params={"ids": ",".join(map(str, activity_ids))}
            )
            activities = {item["id"]: item for item in data}
        except httpx.HTTPError:
            logger.warning("catalog-service injoignable — activités non enrichies")

    return paginate(total, page, size, [_booking_dict(b, activities) for b in rows])


@public_router.post("/validate-promo")
def validate_promo(payload: PromoValidateIn, db: Session = Depends(get_db)):
    """Valide un code promo et retourne sa reduction (en %)."""
    promo = _find_valid_promo(db, payload.code)
    return {"valid": True, "code": promo.code, "reduction": float(promo.reduction)}


@public_router.post("", status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    background: BackgroundTasks,
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Création d'une réservation — mini-saga synchrone :

    1. Vérifie l'activité et le créneau auprès du catalog-service
    2. Réserve la place (décrément atomique côté catalogue)
    3. Crée la réservation locale ; en cas d'échec → compensation (release)
    """
    # 1. L'activité existe ?
    try:
        activities = await catalog.get(
            "/internal/activities/batch", params={"ids": str(payload.activity_id)}
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Catalogue momentanément indisponible")
    if not activities:
        raise HTTPException(status_code=404, detail="Activité introuvable")
    activity = activities[0]

    # Le créneau appartient bien à l'activité ?
    try:
        availability = await catalog.get(f"/internal/availabilities/{payload.availability_id}")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Créneau introuvable")
        raise HTTPException(status_code=503, detail="Catalogue momentanément indisponible")
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Catalogue momentanément indisponible")
    if availability["activity_id"] != payload.activity_id:
        raise HTTPException(status_code=400, detail="Ce créneau n'appartient pas à cette activité")

    guests = max(1, min(8, payload.guests))

    # Code promo optionnel — valide AVANT de reserver les places
    promo = _find_valid_promo(db, payload.promo_code) if payload.promo_code else None

    # 2. Réservation atomique des places
    try:
        await catalog.post(
            f"/internal/availabilities/{payload.availability_id}/reserve",
            params={"seats": guests},
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 409:
            raise HTTPException(status_code=409, detail="Plus de place disponible sur ce créneau")
        raise HTTPException(status_code=503, detail="Catalogue momentanément indisponible")
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Catalogue momentanément indisponible")

    # 3. Création locale + compensation si échec
    try:
        montant = float(activity["prix"]) * guests
        if promo:
            montant = round(montant * (1 - float(promo.reduction) / 100), 2)
        booking = Booking(
            user_id=identity.user_id,
            activity_id=payload.activity_id,
            availability_id=payload.availability_id,
            promo_code_id=promo.id if promo else None,
            statut=BookingStatus.pending,
            montant_total=montant,
            nb_places=guests,
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
    except IntegrityError:
        # L'index `uq_booking_active_user_slot` a rejeté un doublon : cet
        # utilisateur a déjà une réservation active sur ce créneau (double-clic
        # ou requête rejouée). On rend les places prises à l'étape 2 et on
        # renvoie la réservation existante — la requête reste idempotente.
        db.rollback()
        await _release_seats(payload.availability_id, guests, reason="doublon")

        existing = db.scalar(
            select(Booking).where(
                Booking.user_id == identity.user_id,
                Booking.availability_id == payload.availability_id,
                Booking.statut != BookingStatus.cancelled,
            )
        )
        if existing is None:
            # Cas très improbable : le doublon a été annulé entre-temps.
            raise HTTPException(status_code=409, detail="Réservation en double détectée")
        logger.info(
            "Doublon evite (user=%s, availability=%s) -> reservation #%s",
            identity.user_id,
            payload.availability_id,
            existing.id,
        )
        return _booking_dict(existing, {activity["id"]: activity})
    except Exception:
        db.rollback()
        await _release_seats(payload.availability_id, guests, reason="echec creation")
        raise

    # Notification des administrateurs (tache de fond, sans impact sur la reponse)
    background.add_task(_notify_admins_new_booking, booking.id)

    return _booking_dict(booking, {activity["id"]: activity})


@public_router.get("/{booking_id}")
async def get_booking(
    booking_id: int,
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Detail d'une reservation (proprietaire ou admin) — page de paiement."""
    booking = db.get(Booking, booking_id)
    if not booking or (booking.user_id != identity.user_id and not identity.is_admin):
        raise HTTPException(status_code=404, detail="Réservation introuvable")

    activities: dict[int, dict] = {}
    try:
        data = await catalog.get(
            "/internal/activities/batch", params={"ids": str(booking.activity_id)}
        )
        activities = {item["id"]: item for item in data}
    except httpx.HTTPError:
        pass
    return _booking_dict(booking, activities)


@public_router.get("/{booking_id}/qrcode")
def booking_qrcode(
    booking_id: int,
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """QR code SVG de la reservation confirmee (verification sur place)."""
    booking = db.get(Booking, booking_id)
    if not booking or (booking.user_id != identity.user_id and not identity.is_admin):
        raise HTTPException(status_code=404, detail="Réservation introuvable")
    if booking.statut != BookingStatus.confirmed or not booking.qr_code:
        raise HTTPException(status_code=409, detail="Réservation non confirmée")

    image = qrcode.make(booking.qr_code, image_factory=qrcode.image.svg.SvgPathImage)
    return Response(
        content=image.to_string(),
        media_type="image/svg+xml",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@public_router.delete("/{booking_id}")
async def cancel_booking(
    booking_id: int,
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Annule une réservation et rend les places au catalogue.

    Concurrence : lire le statut puis l'écrire laisserait une fenêtre pendant
    laquelle deux requêtes simultanées (double-clic, requête rejouée) se
    croiseraient — chacune verrait `pending` et chacune libérerait les places,
    créant des places fantômes. La transition est donc faite par un UPDATE
    conditionnel : la base ne l'accorde qu'à un seul appelant.
    """
    booking = db.get(Booking, booking_id)
    if not booking or booking.user_id != identity.user_id:
        raise HTTPException(status_code=404, detail="Réservation introuvable")

    seats = int(booking.nb_places or 1)
    availability_id = booking.availability_id

    # Transition atomique pending|confirmed -> cancelled. `rowcount` vaut 1 pour
    # le seul appelant qui a effectivement opéré le changement d'état.
    result = db.execute(
        update(Booking)
        .where(Booking.id == booking_id, Booking.statut != BookingStatus.cancelled)
        .values(statut=BookingStatus.cancelled)
    )
    db.commit()

    if result.rowcount == 0:
        # Un autre appel a déjà annulé : ne pas libérer les places une 2e fois.
        return {"message": "Réservation déjà annulée"}

    # Compensation : on libère les places côté catalogue — exactement une fois.
    await _release_seats(availability_id, seats, reason=f"annulation booking #{booking_id}")

    return {"message": "Réservation annulée"}


# ---------------------------------------------------------------------------
# Routes internes (admin-service, payment-service)
# ---------------------------------------------------------------------------

internal_router = APIRouter(prefix="/internal", dependencies=[Depends(require_internal_key)])


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


@internal_router.get("/stats/bookings")
def booking_stats(db: Session = Depends(get_db)):
    base = select(func.count(Booking.id))

    def count(stmt) -> int:
        return int(db.scalar(stmt) or 0)

    return {
        "total": count(base),
        "pending": count(base.where(Booking.statut == BookingStatus.pending)),
        "confirmed": count(base.where(Booking.statut == BookingStatus.confirmed)),
        "cancelled": count(base.where(Booking.statut == BookingStatus.cancelled)),
        "last_30_days": count(base.where(Booking.date_reservation >= _since(30))),
    }


@internal_router.get("/stats/confirmed-revenue")
def confirmed_revenue(db: Session = Depends(get_db)):
    """Somme des réservations confirmées — fallback du chiffre d'affaires."""
    total = db.scalar(
        select(func.coalesce(func.sum(Booking.montant_total), 0.0)).where(
            Booking.statut == BookingStatus.confirmed
        )
    )
    confirmed_count = db.scalar(
        select(func.count(Booking.id)).where(Booking.statut == BookingStatus.confirmed)
    )
    return {"total": float(total or 0.0), "confirmed_count": int(confirmed_count or 0)}


@internal_router.get("/bookings/recent")
def recent_bookings(limit: int = Query(8, ge=1, le=50), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Booking).order_by(Booking.date_reservation.desc()).limit(limit)
    ).all()
    return [_booking_dict(b) for b in rows]


@internal_router.get("/bookings")
def internal_list_bookings(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    statut: BookingStatus | None = None,
):
    stmt = select(Booking)
    if statut:
        stmt = stmt.where(Booking.statut == statut)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = db.scalars(
        stmt.order_by(Booking.date_reservation.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return paginate(total, page, size, [_booking_dict(b) for b in rows])


async def _send_confirmation_email(booking_id: int) -> None:
    """Tache de fond : compose et envoie l'e-mail de confirmation."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        booking = db.get(Booking, booking_id)
        if not booking:
            return
        activity_title, slot_date = f"Activité #{booking.activity_id}", ""
        email, name = None, ""
        try:
            acts = await catalog.get(
                "/internal/activities/batch", params={"ids": str(booking.activity_id)}
            )
            if acts:
                activity_title = acts[0]["titre"]
            slot = await catalog.get(f"/internal/availabilities/{booking.availability_id}")
            slot_date = slot.get("date", "")
        except httpx.HTTPError:
            pass
        try:
            users = await auth.get("/internal/users/batch", params={"ids": str(booking.user_id)})
            if users:
                email = users[0]["email"]
                name = f"{users[0].get('prenom', '')} {users[0].get('nom', '')}".strip()
        except httpx.HTTPError:
            pass
        if not email:
            logger.warning("E-mail de confirmation impossible : utilisateur %s introuvable", booking.user_id)
            return
        try:
            await notification.post(
                "/internal/emails/booking-confirmation",
                json={
                    "email": email,
                    "name": name or "Voyageur",
                    "activity": activity_title,
                    "date": slot_date,
                    "guests": int(booking.nb_places or 1),
                    "amount": float(booking.montant_total or 0.0),
                    "booking_id": booking.id,
                },
            )
            logger.info("E-mail de confirmation envoyé pour la réservation %s", booking_id)
        except httpx.HTTPError:
            logger.exception("notification-service injoignable (réservation %s)", booking_id)
    finally:
        db.close()


async def _notify_admins_new_booking(booking_id: int) -> None:
    """Tache de fond : previent tous les admins d'une nouvelle reservation."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        booking = db.get(Booking, booking_id)
        if not booking:
            return
        try:
            admins = await auth.get("/internal/admins")
        except httpx.HTTPError:
            logger.warning("auth-service injoignable — admins non notifies (resa %s)", booking_id)
            return
        emails = [a["email"] for a in admins]
        if not emails:
            return
        client_name, client_email = "Client", "-"
        activity_title, slot_date = f"Activite #{booking.activity_id}", ""
        try:
            users = await auth.get("/internal/users/batch", params={"ids": str(booking.user_id)})
            if users:
                client_email = users[0]["email"]
                client_name = f"{users[0].get('prenom', '')} {users[0].get('nom', '')}".strip() or "Client"
        except httpx.HTTPError:
            pass
        try:
            acts = await catalog.get("/internal/activities/batch", params={"ids": str(booking.activity_id)})
            if acts:
                activity_title = acts[0]["titre"]
            slot = await catalog.get(f"/internal/availabilities/{booking.availability_id}")
            slot_date = slot.get("date", "")
        except httpx.HTTPError:
            pass
        try:
            await notification.post(
                "/internal/emails/admin-new-booking",
                json={
                    "emails": emails,
                    "client_name": client_name,
                    "client_email": client_email,
                    "activity": activity_title,
                    "date": slot_date,
                    "guests": int(booking.nb_places or 1),
                    "amount": float(booking.montant_total or 0.0),
                    "booking_id": booking.id,
                },
            )
            logger.info("Admins notifies de la reservation %s", booking_id)
        except httpx.HTTPError:
            logger.exception("notification-service injoignable (notif admin, resa %s)", booking_id)
    finally:
        db.close()


@internal_router.post("/bookings/{booking_id}/confirm")
def confirm_booking(
    booking_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Passe la reservation en `confirmed` (appelee par payment-service).

    Idempotent : une reservation deja confirmee renvoie son etat sans effet.
    Genere le code QR de verification et declenche l'e-mail de confirmation.

    Concurrence : Stripe peut rejouer un webhook, et le payment-service peut
    retenter son appel. La transition pending -> confirmed passe donc par un
    UPDATE conditionnel : un seul appelant l'obtient, donc un seul e-mail de
    confirmation part, meme si dix requetes arrivent en meme temps.
    """
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Réservation introuvable")
    if booking.statut == BookingStatus.cancelled:
        raise HTTPException(status_code=409, detail="Réservation annulée — confirmation impossible")

    # Le QR est genere ici : il doit etre pose par la meme requete atomique que
    # le changement de statut, sinon deux appels concurrents produiraient deux
    # codes differents pour la meme reservation.
    qr_code = booking.qr_code or f"TB-{booking_id}-{uuid.uuid4().hex[:12].upper()}"

    result = db.execute(
        update(Booking)
        .where(Booking.id == booking_id, Booking.statut == BookingStatus.pending)
        .values(statut=BookingStatus.confirmed, qr_code=qr_code)
    )
    db.commit()

    transitioned = result.rowcount == 1
    if transitioned:
        background.add_task(_send_confirmation_email, booking_id)
    else:
        # Deja confirmee (ou annulee entre-temps) : on relit l'etat reel.
        db.refresh(booking)
        if booking.statut == BookingStatus.cancelled:
            raise HTTPException(
                status_code=409, detail="Réservation annulée — confirmation impossible"
            )
        qr_code = booking.qr_code

    return {
        "booking_id": booking_id,
        "statut": BookingStatus.confirmed.value,
        "qr_code": qr_code,
        "already_confirmed": not transitioned,
    }


@internal_router.post("/bookings/expire-pending")
async def expire_pending_now():
    """Déclenche immédiatement le balayage des réservations abandonnées.

    La tâche de fond s'en charge automatiquement ; cet endpoint permet de la
    forcer — démonstration, exploitation, ou après un incident.
    """
    from app.expiry import expire_pending_bookings

    report = await expire_pending_bookings()
    return {
        "expiry_minutes": settings.BOOKING_EXPIRY_MINUTES,
        **report,
    }


@internal_router.get("/bookings/has-booked")
def has_booked(user_id: int, activity_id: int, db: Session = Depends(get_db)):
    """L'utilisateur a-t-il une reservation (non annulee) pour cette activite ?"""
    row = db.scalar(
        select(Booking.id).where(
            Booking.user_id == user_id,
            Booking.activity_id == activity_id,
            Booking.statut != BookingStatus.cancelled,
        ).limit(1)
    )
    return {"has_booked": row is not None}


@internal_router.get("/bookings/batch")
def bookings_batch(ids: str = Query(...), db: Session = Depends(get_db)):
    """Résolution en masse (payment-service / admin-service)."""
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        return []
    if not id_list:
        return []
    rows = db.scalars(select(Booking).where(Booking.id.in_(id_list[:200]))).all()
    return [_booking_dict(b) for b in rows]


@internal_router.get("/bookings/count-by-activity")
def count_by_activity(ids: str = Query(...), db: Session = Depends(get_db)):
    """Nombre de réservations par activité (liste admin des activités)."""
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        return {}
    if not id_list:
        return {}
    rows = db.execute(
        select(Booking.activity_id, func.count(Booking.id))
        .where(Booking.activity_id.in_(id_list[:200]))
        .group_by(Booking.activity_id)
    ).all()
    return {str(activity_id): int(nb) for activity_id, nb in rows}
