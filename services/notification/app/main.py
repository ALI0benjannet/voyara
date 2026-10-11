import logging

from fastapi import BackgroundTasks, Depends, FastAPI
from pydantic import BaseModel, EmailStr

from voyara_common.exceptions import register_exception_handlers
from voyara_common.internal import require_internal_key
from voyara_common.logging import setup_logging

from app.config import settings
from app.emails import (
    send_admin_new_booking_email,
    send_booking_confirmation_email,
    send_reset_password_email,
    send_verification_email,
)

setup_logging(settings.SERVICE_NAME)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Service d'envoi d'e-mails transactionnels Voyara (interne uniquement).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

register_exception_handlers(app)


class EmailPayload(BaseModel):
    email: EmailStr
    name: str
    token: str


@app.get("/health", tags=["Système"])
def health():
    return {"service": settings.SERVICE_NAME, "status": "ok", "environment": settings.ENVIRONMENT}


@app.post(
    "/internal/emails/verification",
    dependencies=[Depends(require_internal_key)],
    tags=["Emails"],
)
def email_verification(payload: EmailPayload, background: BackgroundTasks):
    """Planifie l'envoi de l'e-mail de vérification de compte.

    L'envoi SMTP se fait en tâche de fond : on répond immédiatement à
    l'appelant (auth-service), qui a lui-même déjà répondu à l'utilisateur.
    """
    background.add_task(send_verification_email, payload.email, payload.name, payload.token)
    return {"status": "scheduled"}


@app.post(
    "/internal/emails/password-reset",
    dependencies=[Depends(require_internal_key)],
    tags=["Emails"],
)
def email_password_reset(payload: EmailPayload, background: BackgroundTasks):
    background.add_task(send_reset_password_email, payload.email, payload.name, payload.token)
    return {"status": "scheduled"}


class AdminNewBookingPayload(BaseModel):
    emails: list[EmailStr]
    client_name: str
    client_email: str
    activity: str
    date: str
    guests: int
    amount: float
    booking_id: int


@app.post(
    "/internal/emails/admin-new-booking",
    dependencies=[Depends(require_internal_key)],
    tags=["Emails"],
)
def email_admin_new_booking(payload: AdminNewBookingPayload, background: BackgroundTasks):
    """Notification aux administrateurs à chaque nouvelle réservation."""
    if not payload.emails:
        return {"status": "skipped", "reason": "no admin recipients"}
    background.add_task(
        send_admin_new_booking_email,
        [str(e) for e in payload.emails],
        payload.client_name,
        payload.client_email,
        payload.activity,
        payload.date,
        payload.guests,
        payload.amount,
        payload.booking_id,
    )
    return {"status": "scheduled"}


class BookingConfirmationPayload(BaseModel):
    email: EmailStr
    name: str
    activity: str
    date: str
    guests: int
    amount: float
    booking_id: int


@app.post(
    "/internal/emails/booking-confirmation",
    dependencies=[Depends(require_internal_key)],
    tags=["Emails"],
)
def email_booking_confirmation(payload: BookingConfirmationPayload, background: BackgroundTasks):
    """E-mail de confirmation après paiement d'une réservation."""
    background.add_task(
        send_booking_confirmation_email,
        payload.email,
        payload.name,
        payload.activity,
        payload.date,
        payload.guests,
        payload.amount,
        payload.booking_id,
    )
    return {"status": "scheduled"}
