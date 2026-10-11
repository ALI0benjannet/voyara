import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from voyara_common.security import hash_password, verify_password

from app.models.enums import UserRole
from app.models.users import User
from app.schemas.user import UserCreate


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def create_user(
    db: Session, data: UserCreate, role: UserRole = UserRole.tourist
) -> User:
    user = User(
        email=data.email.lower(),
        nom=data.nom,
        prenom=data.prenom,
        hashed_password=hash_password(data.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    logger = logging.getLogger(__name__)
    user = get_by_email(db, email)
    if not user:
        return None
    try:
        ok = verify_password(password, user.hashed_password)
    except Exception as exc:
        logger.exception("Error verifying password for user %s: %s", email, exc)
        return None
    if not ok:
        return None
    return user
