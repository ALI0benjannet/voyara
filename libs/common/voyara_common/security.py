"""Sécurité partagée : hash des mots de passe, tokens e-mail, JWT.

Code repris tel quel de l'ancien monolithe (backend/app/core/security.py)
pour que les mots de passe hachés et les JWT existants restent valides.
"""

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, field_validator

from voyara_common.config import get_common_settings

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
)

ACCESS = "access"
REFRESH = "refresh"

PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


def generate_raw_token() -> str:
    """Token aléatoire envoyé par e-mail (URL-safe)."""
    return secrets.token_urlsafe(48)


def generate_verification_code(length: int = 4) -> str:
    """Code de vérification numérique envoyé par e-mail."""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_token(raw: str) -> str:
    """Hash stocké en base."""
    return hashlib.sha256(raw.encode()).hexdigest()


def expires_in(minutes: int = 0, hours: int = 0, days: int = 0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes, hours=hours, days=days)


def is_valid(token_row) -> bool:
    return (
        token_row is not None
        and token_row.used_at is None
        and token_row.expires_at > datetime.now(timezone.utc)
    )


class PasswordMixin(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def strong(cls, v: str) -> str:
        if not PASSWORD_RE.match(v):
            raise ValueError("8 caractères minimum, avec majuscule, minuscule et chiffre")
        return v


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(subject, role, token_type: str, expires: timedelta) -> str:
    settings = get_common_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject, role) -> str:
    settings = get_common_settings()
    return _create_token(
        subject,
        role,
        ACCESS,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject, role) -> str:
    settings = get_common_settings()
    return _create_token(
        subject,
        role,
        REFRESH,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any] | None:
    settings = get_common_settings()
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        return None
