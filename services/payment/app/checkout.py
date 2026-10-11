"""Tunnel de paiement : create-intent, webhook Stripe, simulation de démo.

Deux modes, sélectionnés par la présence de STRIPE_SECRET_KEY :
- **Stripe réel** : PaymentIntent + webhook `payment_intent.succeeded` signé et
  idempotent (table `processed_events`).
- **Simulation** (clé absente) : mêmes étapes et mêmes états en base, mais la
  confirmation vient d'un endpoint `mock-confirm` appelé par le bouton
  « Simuler le paiement » du front — clairement étiqueté démo.
"""

import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from voyara_common.auth import TokenIdentity, get_current_identity
from voyara_common.internal import ServiceClient

from app.config import settings
from app.database import get_db
from app.models import Payment, PaymentStatus, PaymentType, ProcessedEvent

logger = logging.getLogger(__name__)

booking_client = ServiceClient(settings.BOOKING_SERVICE_URL)

checkout_router = APIRouter(prefix="/payments", tags=["Paiement"])


class CreateIntentIn(BaseModel):
    booking_id: int


class MockConfirmIn(BaseModel):
    payment_id: int


async def _get_owned_pending_booking(booking_id: int, user_id: int) -> dict:
    """Récupère la réservation via le booking-service et vérifie propriétaire + statut."""
    try:
        rows = await booking_client.get(
            "/internal/bookings/batch", params={"ids": str(booking_id)}
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Service réservations indisponible")
    if not rows:
        raise HTTPException(status_code=404, detail="Réservation introuvable")
    booking = rows[0]
    if booking["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Réservation introuvable")
    if booking["statut"] == "cancelled":
        raise HTTPException(status_code=409, detail="Réservation annulée")
    if booking["statut"] == "confirmed":
        raise HTTPException(status_code=409, detail="Réservation déjà payée")
    return booking


async def _confirm_booking(booking_id: int) -> dict:
    """pending → confirmed côté booking-service (idempotent)."""
    try:
        return await booking_client.post(f"/internal/bookings/{booking_id}/confirm")
    except httpx.HTTPError:
        logger.exception("Confirmation impossible pour la réservation %s", booking_id)
        raise HTTPException(
            status_code=503,
            detail="Paiement enregistré mais confirmation en attente — réessayez",
        )


# ---------------------------------------------------------------------------
# Création de l'intention de paiement
# ---------------------------------------------------------------------------

@checkout_router.post("/create-intent", status_code=status.HTTP_201_CREATED)
async def create_intent(
    payload: CreateIntentIn,
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    booking = await _get_owned_pending_booking(payload.booking_id, identity.user_id)
    amount = float(booking["montant_total"])

    # Réutilise un paiement en attente existant (évite les doublons au refresh)
    payment = db.scalar(
        select(Payment).where(
            Payment.booking_id == payload.booking_id,
            Payment.statut == PaymentStatus.pending,
        )
    )

    if settings.stripe_enabled:
        import stripe

        stripe.api_key = settings.STRIPE_SECRET_KEY
        if payment and payment.stripe_intent_id and not payment.stripe_intent_id.startswith("mock_"):
            intent = stripe.PaymentIntent.retrieve(payment.stripe_intent_id)
        else:
            # Stripe ne supporte pas le TND → EUR à valeur égale (démo, documenté)
            intent = stripe.PaymentIntent.create(
                amount=int(round(amount * 100)),
                currency="eur",
                metadata={"booking_id": str(payload.booking_id)},
                automatic_payment_methods={"enabled": True},
            )
            if payment:
                payment.stripe_intent_id = intent.id
            else:
                payment = Payment(
                    booking_id=payload.booking_id,
                    montant=amount,
                    type=PaymentType.full,
                    methode="stripe",
                    statut=PaymentStatus.pending,
                    stripe_intent_id=intent.id,
                )
                db.add(payment)
            db.commit()
        return {
            "mode": "stripe",
            "payment_id": payment.id,
            "client_secret": intent.client_secret,
            "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "amount": amount,
        }

    # ---- MODE SIMULATION (aucune clé Stripe configurée) ----
    if not payment:
        payment = Payment(
            booking_id=payload.booking_id,
            montant=amount,
            type=PaymentType.full,
            methode="simulation",
            statut=PaymentStatus.pending,
            stripe_intent_id=f"mock_{uuid.uuid4().hex}",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
    return {"mode": "mock", "payment_id": payment.id, "amount": amount}


# ---------------------------------------------------------------------------
# Webhook Stripe (mode réel) — signature + idempotence
# ---------------------------------------------------------------------------

@checkout_router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """Route publique : l'authentification est la signature Stripe."""
    if not settings.stripe_enabled:
        raise HTTPException(status_code=404, detail="Stripe non configuré")

    import stripe

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Signature invalide")

    # Idempotence : un event.id déjà vu n'est pas retraité
    if db.scalar(select(ProcessedEvent).where(ProcessedEvent.event_id == event.id)):
        return {"received": True, "duplicate": True}
    db.add(ProcessedEvent(event_id=event.id))
    db.commit()

    if event.type in ("payment_intent.succeeded", "payment_intent.payment_failed"):
        intent = event.data.object
        payment = db.scalar(select(Payment).where(Payment.stripe_intent_id == intent.id))
        if not payment:
            logger.warning("Webhook pour un intent inconnu : %s", intent.id)
            return {"received": True}
        if event.type == "payment_intent.succeeded":
            payment.statut = PaymentStatus.succeeded
            db.commit()
            await _confirm_booking(payment.booking_id)
            logger.info("Paiement %s confirmé (réservation %s)", payment.id, payment.booking_id)
        else:
            payment.statut = PaymentStatus.failed
            db.commit()

    return {"received": True}


# ---------------------------------------------------------------------------
# Simulation (mode démo uniquement)
# ---------------------------------------------------------------------------

@checkout_router.post("/mock-confirm")
async def mock_confirm(
    payload: MockConfirmIn,
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """Simule le webhook `payment_intent.succeeded` — désactivé si Stripe est configuré."""
    if settings.stripe_enabled:
        raise HTTPException(status_code=404, detail="Mode simulation désactivé")

    payment = db.get(Payment, payload.payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Paiement introuvable")

    # Le paiement doit appartenir à une réservation de l'utilisateur
    try:
        rows = await booking_client.get(
            "/internal/bookings/batch", params={"ids": str(payment.booking_id)}
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Service réservations indisponible")
    if not rows or (rows[0]["user_id"] != identity.user_id and not identity.is_admin):
        raise HTTPException(status_code=404, detail="Paiement introuvable")

    if payment.statut != PaymentStatus.succeeded:
        payment.statut = PaymentStatus.succeeded
        db.commit()

    result = await _confirm_booking(payment.booking_id)
    return {
        "payment_id": payment.id,
        "statut": payment.statut.value,
        "booking": result,
        "simulated": True,
    }
