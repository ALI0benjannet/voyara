"""Authentification stateless partagée entre services.

Dans une architecture microservices, seuls les services qui possèdent la table
`users` (auth-service) peuvent charger l'utilisateur depuis la base. Les autres
services vérifient le JWT localement et se fient à ses claims (id + rôle).
Le token d'accès étant à durée courte (30 min), c'est le compromis standard.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from voyara_common.security import ACCESS, decode_token

# Valeurs de rôle telles qu'encodées dans le JWT (voir UserRole du auth-service)
ROLE_ADMIN = 1
ROLE_TOURIST = 2

# tokenUrl pointe vers la route du gateway (utile uniquement pour Swagger)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/form")

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Identifiants invalides ou token expiré",
    headers={"WWW-Authenticate": "Bearer"},
)


class TokenIdentity(BaseModel):
    """Identité extraite du JWT — pas de lookup en base."""

    user_id: int
    role: int

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


def get_current_identity(token: str = Depends(oauth2_scheme)) -> TokenIdentity:
    payload = decode_token(token)
    if payload is None or payload.get("type") != ACCESS:
        raise CREDENTIALS_ERROR
    try:
        return TokenIdentity(user_id=int(payload["sub"]), role=int(payload["role"]))
    except (KeyError, TypeError, ValueError):
        raise CREDENTIALS_ERROR


def require_admin(identity: TokenIdentity = Depends(get_current_identity)) -> TokenIdentity:
    if not identity.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé à l'administrateur",
        )
    return identity
