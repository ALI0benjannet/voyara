from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from voyara_common.auth import CREDENTIALS_ERROR, oauth2_scheme
from voyara_common.security import ACCESS, decode_token

from app.database import get_db
from app.models.enums import UserRole
from app.models.users import User
from app.services import user_service


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    payload = decode_token(token)
    if payload is None or payload.get("type") != ACCESS:
        raise CREDENTIALS_ERROR
    user = user_service.get_by_id(db, int(payload["sub"]))
    if user is None:
        raise CREDENTIALS_ERROR
    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")
    return user


def require_admin(user: User = Depends(get_current_active_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé à l'administrateur",
        )
    return user
