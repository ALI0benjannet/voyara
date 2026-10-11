"""Routes d'administration du catalogue (JWT admin requis).

CRUD catégories / activités / créneaux + upload de photo d'activité.
Exposées par le gateway sous /api/v1/* comme les routes publiques — la
protection est le rôle admin du JWT (`require_admin`).
"""

import logging
from datetime import date as date_type, time as time_type
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field

from voyara_common.auth import require_admin
from voyara_common.internal import ServiceClient

from app.config import settings
from app.database import get_db
from app.models import Activity, Availability, Category
from app.schemas import ActivityRead, AvailabilityRead, CategoryRead

logger = logging.getLogger(__name__)

booking = ServiceClient(settings.BOOKING_SERVICE_URL)

admin_router = APIRouter(tags=["Catalogue — administration"], dependencies=[Depends(require_admin)])

# services/catalog/static/activities
PHOTO_DIR = Path(__file__).resolve().parents[1] / "static" / "activities"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


# ---------------------------------------------------------------------------
# Schémas d'entrée
# ---------------------------------------------------------------------------

class CategoryIn(BaseModel):
    nom: str = Field(min_length=2, max_length=100)
    nom_en: str | None = Field(default=None, max_length=100)
    nom_ar: str | None = Field(default=None, max_length=100)


class ActivityIn(BaseModel):
    titre: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    # Traductions facultatives ; vides, le français est affiché en repli.
    titre_en: str | None = Field(default=None, max_length=200)
    titre_ar: str | None = Field(default=None, max_length=200)
    description_en: str | None = None
    description_ar: str | None = None
    prix: float = Field(gt=0)
    duree: int = Field(gt=0, description="Durée en minutes")
    localisation: str = Field(min_length=2, max_length=255)
    latitude: float | None = None
    longitude: float | None = None
    category_id: int


class ActivityUpdate(BaseModel):
    titre: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10)
    titre_en: str | None = Field(default=None, max_length=200)
    titre_ar: str | None = Field(default=None, max_length=200)
    description_en: str | None = None
    description_ar: str | None = None
    prix: float | None = Field(default=None, gt=0)
    duree: int | None = Field(default=None, gt=0)
    localisation: str | None = Field(default=None, min_length=2, max_length=255)
    latitude: float | None = None
    longitude: float | None = None
    category_id: int | None = None


class AvailabilityIn(BaseModel):
    activity_id: int
    date: date_type
    heure: time_type
    places_disponibles: int = Field(ge=0, le=100)


class AvailabilityUpdate(BaseModel):
    date: date_type | None = None
    heure: time_type | None = None
    places_disponibles: int | None = Field(default=None, ge=0, le=100)


def _get_or_404(db: Session, model, obj_id: int, label: str):
    obj = db.get(model, obj_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"{label} introuvable")
    return obj


# ---------------------------------------------------------------------------
# Catégories
# ---------------------------------------------------------------------------

@admin_router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryIn, db: Session = Depends(get_db)):
    if db.scalar(select(Category).where(Category.nom == payload.nom)):
        raise HTTPException(status_code=409, detail="Cette catégorie existe déjà")
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@admin_router.put("/categories/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, payload: CategoryIn, db: Session = Depends(get_db)):
    category = _get_or_404(db, Category, category_id, "Catégorie")
    duplicate = db.scalar(
        select(Category).where(Category.nom == payload.nom, Category.id != category_id)
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Cette catégorie existe déjà")
    for key, value in payload.model_dump().items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


@admin_router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = _get_or_404(db, Category, category_id, "Catégorie")
    if db.scalar(select(Activity.id).where(Activity.category_id == category_id).limit(1)):
        raise HTTPException(
            status_code=409,
            detail="Impossible : des activités utilisent encore cette catégorie",
        )
    db.delete(category)
    db.commit()


# ---------------------------------------------------------------------------
# Activités
# ---------------------------------------------------------------------------

@admin_router.post("/activities", response_model=ActivityRead, status_code=status.HTTP_201_CREATED)
def create_activity(payload: ActivityIn, db: Session = Depends(get_db)):
    _get_or_404(db, Category, payload.category_id, "Catégorie")
    activity = Activity(**payload.model_dump())
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return db.scalar(
        select(Activity).options(joinedload(Activity.category)).where(Activity.id == activity.id)
    )


@admin_router.put("/activities/{activity_id}", response_model=ActivityRead)
def update_activity(activity_id: int, payload: ActivityUpdate, db: Session = Depends(get_db)):
    activity = _get_or_404(db, Activity, activity_id, "Activité")
    updates = payload.model_dump(exclude_unset=True)
    if "category_id" in updates:
        _get_or_404(db, Category, updates["category_id"], "Catégorie")
    for key, value in updates.items():
        setattr(activity, key, value)
    db.commit()
    return db.scalar(
        select(Activity).options(joinedload(Activity.category)).where(Activity.id == activity_id)
    )


@admin_router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = _get_or_404(db, Activity, activity_id, "Activité")

    # Garde inter-services : refuser si des réservations existent (ADR-002)
    try:
        counts = await booking.get(
            "/internal/bookings/count-by-activity", params={"ids": str(activity_id)}
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=503,
            detail="Service réservations injoignable — suppression refusée par prudence",
        )
    if int(counts.get(str(activity_id), 0)) > 0:
        raise HTTPException(
            status_code=409,
            detail="Impossible : des réservations existent pour cette activité",
        )

    _delete_photo_file(activity)
    for availability in db.scalars(
        select(Availability).where(Availability.activity_id == activity_id)
    ):
        db.delete(availability)
    db.delete(activity)
    db.commit()


# ---------------------------------------------------------------------------
# Photo d'activité (multipart → /static/activities/, servi par ce service)
# ---------------------------------------------------------------------------

def _delete_photo_file(activity: Activity) -> None:
    if activity.photos and activity.photos.startswith("/static/activities/"):
        old = PHOTO_DIR / activity.photos.split("/static/activities/", 1)[1]
        if old.exists():
            old.unlink()


@admin_router.post("/activities/{activity_id}/photo", response_model=ActivityRead)
async def upload_activity_photo(
    activity_id: int,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    activity = _get_or_404(db, Activity, activity_id, "Activité")

    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Le fichier doit être une image")
    extension = Path(photo.filename or "").suffix.lower() or ".jpg"
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Format non supporté (JPG, PNG ou WebP)")

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{activity_id}-{uuid4().hex}{extension}"
    (PHOTO_DIR / filename).write_bytes(await photo.read())

    _delete_photo_file(activity)
    activity.photos = f"/static/activities/{filename}"
    db.commit()
    return db.scalar(
        select(Activity).options(joinedload(Activity.category)).where(Activity.id == activity_id)
    )


@admin_router.delete("/activities/{activity_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity_photo(activity_id: int, db: Session = Depends(get_db)):
    activity = _get_or_404(db, Activity, activity_id, "Activité")
    _delete_photo_file(activity)
    activity.photos = None
    db.commit()


# ---------------------------------------------------------------------------
# Disponibilités (créneaux)
# ---------------------------------------------------------------------------

@admin_router.post(
    "/availabilities", response_model=AvailabilityRead, status_code=status.HTTP_201_CREATED
)
def create_availability(payload: AvailabilityIn, db: Session = Depends(get_db)):
    _get_or_404(db, Activity, payload.activity_id, "Activité")
    # À la création, la capacité d'origine est le nombre de places saisi :
    # `places_totales` sert ensuite de référence fixe à la réconciliation.
    availability = Availability(
        **payload.model_dump(),
        places_totales=payload.places_disponibles,
    )
    db.add(availability)
    db.commit()
    db.refresh(availability)
    return availability


@admin_router.put("/availabilities/{availability_id}", response_model=AvailabilityRead)
def update_availability(
    availability_id: int, payload: AvailabilityUpdate, db: Session = Depends(get_db)
):
    availability = _get_or_404(db, Availability, availability_id, "Créneau")
    updates = payload.model_dump(exclude_unset=True)

    # L'admin qui modifie « places » ajuste la CAPACITÉ du créneau, pas le
    # compteur de restantes : passer 8 -> 10 alors que 2 sont déjà réservées
    # doit donner 8 restantes, pas 10. On applique donc le delta aux deux
    # colonnes, en gardant les restantes dans [0, capacité].
    if "places_disponibles" in updates:
        nouvelle_capacite = updates.pop("places_disponibles")
        delta = nouvelle_capacite - (availability.places_totales or 0)
        availability.places_totales = nouvelle_capacite
        availability.places_disponibles = max(
            0, min(nouvelle_capacite, (availability.places_disponibles or 0) + delta)
        )

    for key, value in updates.items():
        setattr(availability, key, value)
    db.commit()
    db.refresh(availability)
    return availability


@admin_router.delete("/availabilities/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_availability(availability_id: int, db: Session = Depends(get_db)):
    availability = _get_or_404(db, Availability, availability_id, "Créneau")
    db.delete(availability)
    db.commit()
