"""Envoi d'e-mails transactionnels (repris de l'ancien email_service)."""

import logging
from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.config import settings

logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER=Path(__file__).parent / "templates" / "email",
)

fm = FastMail(conf)


async def send_verification_email(email: str, name: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/verify-email?email={email}"
    message = MessageSchema(
        subject="Confirmez votre compte Voyara",
        recipients=[email],
        template_body={
            "name": name,
            "code": token,
            "link": link,
            "hours": settings.EMAIL_VERIFICATION_EXPIRE_HOURS,
        },
        subtype=MessageType.html,
    )
    try:
        await fm.send_message(message, template_name="verify_account.html")
        logger.info("Verification email sent to %s", email)
    except Exception:
        logger.exception("Failed to send verification email to %s", email)
        raise


async def send_booking_confirmation_email(
    email: str, name: str, activity: str, date: str, guests: int, amount: float, booking_id: int
) -> None:
    message = MessageSchema(
        subject=f"Réservation confirmée — {activity}",
        recipients=[email],
        template_body={
            "name": name,
            "activity": activity,
            "date": date,
            "guests": guests,
            "amount": f"{amount:g}",
            "booking_id": booking_id,
            "link": f"{settings.FRONTEND_URL}/bookings",
        },
        subtype=MessageType.html,
    )
    try:
        await fm.send_message(message, template_name="booking_confirmed.html")
        logger.info("Booking confirmation email sent to %s", email)
    except Exception:
        logger.exception("Failed to send booking confirmation email to %s", email)
        raise


async def send_admin_new_booking_email(
    emails: list[str],
    client_name: str,
    client_email: str,
    activity: str,
    date: str,
    guests: int,
    amount: float,
    booking_id: int,
) -> None:
    """Notifie tous les administrateurs d'une nouvelle réservation."""
    message = MessageSchema(
        subject=f"Nouvelle réservation #{booking_id} — {activity}",
        recipients=emails,
        template_body={
            "booking_id": booking_id,
            "client_name": client_name,
            "client_email": client_email,
            "activity": activity,
            "date": date,
            "guests": guests,
            "amount": f"{amount:g}",
            "link": f"{settings.ADMIN_URL}/bookings",
        },
        subtype=MessageType.html,
    )
    try:
        await fm.send_message(message, template_name="admin_new_booking.html")
        logger.info("Admin new-booking email sent to %s admin(s)", len(emails))
    except Exception:
        logger.exception("Failed to send admin new-booking email")
        raise


async def send_reset_password_email(email: str, name: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/reset-password?email={email}"
    message = MessageSchema(
        subject="Réinitialisation de votre mot de passe",
        recipients=[email],
        template_body={
            "name": name,
            "code": token,
            "link": link,
            "minutes": settings.PASSWORD_RESET_EXPIRE_MINUTES,
        },
        subtype=MessageType.html,
    )
    try:
        await fm.send_message(message, template_name="reset_password.html")
        logger.info("Reset password email sent to %s", email)
    except Exception:
        logger.exception("Failed to send reset password email to %s", email)
        raise
