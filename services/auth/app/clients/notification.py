"""Client vers le notification-service (remplace l'ancien email_service local).

L'envoi réel de l'e-mail (SMTP) appartient désormais au notification-service.
Ces fonctions sont utilisées via BackgroundTasks : un échec du service de
notification n'impacte pas la réponse HTTP à l'utilisateur.
"""

import logging

from voyara_common.internal import ServiceClient

from app.config import settings

logger = logging.getLogger(__name__)

_client = ServiceClient(settings.NOTIFICATION_SERVICE_URL)


async def send_verification_email(email: str, name: str, token: str) -> None:
    try:
        await _client.post(
            "/internal/emails/verification",
            json={"email": email, "name": name, "token": token},
        )
        logger.info("Verification email dispatched for %s", email)
    except Exception:
        logger.exception("Failed to dispatch verification email for %s", email)


async def send_reset_password_email(email: str, name: str, token: str) -> None:
    try:
        await _client.post(
            "/internal/emails/password-reset",
            json={"email": email, "name": name, "token": token},
        )
        logger.info("Reset password email dispatched for %s", email)
    except Exception:
        logger.exception("Failed to dispatch reset password email for %s", email)
