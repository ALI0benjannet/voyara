"""Espace prestataire et modération.

- `/prestataire/*` (JWT, tout utilisateur connecté) : un prestataire propose
  des activités. Elles sont créées « en_attente » : rien n'est visible des
  voyageurs avant validation.
- `/moderation/*` (JWT admin) : l'admin publie ou refuse ces propositions.

Les créneaux d'une activité validée sont ajoutés depuis l'espace admin
(CRUD `/availabilities` existant).
"""

from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from voyara_common.auth import TokenIdentity, get_current_identity, require_admin

from app.admin_routes import ActivityIn, _delete_photo_file, _get_or_404, save_activity_photo
from app.database import get_db
from app.models import Activity, Category
from app.schemas import ActivityRead

provider_router = APIRouter(prefix="/prestataire", tags=["Espace prestataire"])
moderation_router = APIRouter(
    prefix="/moderation", tags=["Modération"], dependencies=[Depends(require_admin)]
)

STATUTS_MODIFIABLES = {"en_attente", "refusee"}


class StatutIn(BaseModel):
    statut: Literal["publiee", "refusee"]


def _activity_with_category(db: Session, activity_id: int) -> Activity:
    return db.scalar(
        select(Activity).options(joinedload(Activity.category)).where(Activity.id == activity_id)
    )


def _own_activity(db: Session, activity_id: int, identity: TokenIdentity) -> Activity:
    activity = db.get(Activity, activity_id)
    if not activity or activity.prestataire_id != identity.user_id:
        raise HTTPException(status_code=404, detail="Activité introuvable")
    return activity


# ---------------------------------------------------------------------------
# Activités du prestataire
# ---------------------------------------------------------------------------

@provider_router.get("/activities", response_model=list[ActivityRead])
def my_activities(
    identity: TokenIdentity = Depends(get_current_identity), db: Session = Depends(get_db)
):
    return db.scalars(
        select(Activity)
        .options(joinedload(Activity.category))
        .where(Activity.prestataire_id == identity.user_id)
        .order_by(Activity.id.desc())
    ).all()


@provider_router.post(
    "/activities", response_model=ActivityRead, status_code=status.HTTP_201_CREATED
)
def propose_activity(
    payload: ActivityIn,
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    _get_or_404(db, Category, payload.category_id, "Catégorie")
    activity = Activity(
        **payload.model_dump(), statut="en_attente", prestataire_id=identity.user_id
    )
    db.add(activity)
    db.commit()
    return _activity_with_category(db, activity.id)


@provider_router.post("/activities/{activity_id}/photo", response_model=ActivityRead)
async def upload_my_activity_photo(
    activity_id: int,
    photo: UploadFile = File(...),
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    activity = _own_activity(db, activity_id, identity)
    if activity.statut not in STATUTS_MODIFIABLES:
        raise HTTPException(status_code=409, detail="Activité déjà publiée : contactez l'admin")
    await save_activity_photo(activity, photo)
    db.commit()
    return _activity_with_category(db, activity_id)


@provider_router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_activity(
    activity_id: int,
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    # Une activité publiée peut avoir des réservations : sa suppression passe
    # par l'admin, qui vérifie auprès du booking-service.
    activity = _own_activity(db, activity_id, identity)
    if activity.statut not in STATUTS_MODIFIABLES:
        raise HTTPException(status_code=409, detail="Activité déjà publiée : contactez l'admin")
    _delete_photo_file(activity)
    db.delete(activity)
    db.commit()


# ---------------------------------------------------------------------------
# Modération (admin)
# ---------------------------------------------------------------------------

@moderation_router.get("/activities", response_model=list[ActivityRead])
def pending_activities(statut: str = "en_attente", db: Session = Depends(get_db)):
    return db.scalars(
        select(Activity)
        .options(joinedload(Activity.category))
        .where(Activity.prestataire_id.is_not(None), Activity.statut == statut)
        .order_by(Activity.id.desc())
    ).all()


@moderation_router.patch("/activities/{activity_id}", response_model=ActivityRead)
def moderate_activity(activity_id: int, payload: StatutIn, db: Session = Depends(get_db)):
    activity = _get_or_404(db, Activity, activity_id, "Activité")
    activity.statut = payload.statut
    db.commit()
    return _activity_with_category(db, activity_id)
