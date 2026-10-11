"""Endpoints internes (service → service), jamais exposés par le gateway.

Consommés par l'admin-service pour le dashboard et les listes.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from voyara_common.internal import require_internal_key
from voyara_common.pagination import paginate

from app.database import get_db
from app.models.enums import UserRole
from app.models.users import User

router = APIRouter(prefix="/internal", dependencies=[Depends(require_internal_key)])


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


@router.get("/stats/users")
def user_stats(db: Session = Depends(get_db)):
    base = select(func.count(User.id))

    def count(stmt) -> int:
        return int(db.scalar(stmt) or 0)

    return {
        "total": count(base),
        "active": count(base.where(User.is_active.is_(True))),
        "verified": count(base.where(User.is_verified.is_(True))),
        "admins": count(base.where(User.role == UserRole.admin)),
        "new_30_days": count(base.where(User.date_inscription >= _since(30))),
    }


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, min_length=1, max_length=100),
):
    stmt = select(User)
    if search:
        pattern = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(User.email).like(pattern),
                func.lower(User.nom).like(pattern),
                func.lower(User.prenom).like(pattern),
            )
        )

    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    users = db.scalars(
        stmt.order_by(User.date_inscription.desc()).offset((page - 1) * size).limit(size)
    ).all()

    items = [
        {
            "id": u.id,
            "nom": u.nom,
            "prenom": u.prenom,
            "email": u.email,
            "role": u.role.name,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "phone": u.phone,
            "date_inscription": u.date_inscription.isoformat(),
        }
        for u in users
    ]
    return paginate(total, page, size, items)


@router.get("/admins")
def list_admin_emails(db: Session = Depends(get_db)):
    """E-mails des administrateurs actifs — pour les notifications internes."""
    admins = db.scalars(
        select(User).where(User.role == UserRole.admin, User.is_active.is_(True))
    ).all()
    return [
        {"email": u.email, "prenom": u.prenom, "nom": u.nom}
        for u in admins
        # Les comptes anonymisés (RGPD) sont exclus
        if not u.email.startswith("deleted-")
    ]


@router.get("/users/batch")
def users_batch(
    ids: str = Query(..., description="IDs séparés par des virgules, ex: 1,2,3"),
    db: Session = Depends(get_db),
):
    """Résolution en masse d'utilisateurs (enrichissement côté admin-service)."""
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        return []
    if not id_list:
        return []
    users = db.scalars(select(User).where(User.id.in_(id_list[:200]))).all()
    return [
        {
            "id": u.id,
            "nom": u.nom,
            "prenom": u.prenom,
            "email": u.email,
        }
        for u in users
    ]
