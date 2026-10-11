from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from voyara_common.internal import require_internal_key
from voyara_common.pagination import Page, paginate

from app.database import get_db
from app.models import Activity, Availability, Category
from app.schemas import ActivityRead, AvailabilityRead, CategoryRead

# ---------------------------------------------------------------------------
# Routes publiques (exposées par le gateway)
# ---------------------------------------------------------------------------

public_router = APIRouter(tags=["Catalogue"])


@public_router.get("/categories", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.nom)).all()


@public_router.get("/activities", response_model=Page[ActivityRead])
def list_activities(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category_id: int | None = None,
    search: str | None = Query(None, min_length=1, max_length=100),
):
    stmt = select(Activity).options(joinedload(Activity.category))
    if category_id:
        stmt = stmt.where(Activity.category_id == category_id)
    if search:
        pattern = f"%{search.lower()}%"
        # Recherche libre : titre (dans les trois langues), ville, et nom de la
        # catégorie — un visiteur qui tape « désert » ou « Djerba » doit trouver.
        stmt = stmt.join(Activity.category, isouter=True).where(
            func.lower(Activity.titre).like(pattern)
            | func.lower(func.coalesce(Activity.titre_en, "")).like(pattern)
            | func.lower(func.coalesce(Activity.titre_ar, "")).like(pattern)
            | func.lower(Activity.localisation).like(pattern)
            | func.lower(func.coalesce(Category.nom, "")).like(pattern)
            | func.lower(func.coalesce(Category.nom_en, "")).like(pattern)
            | func.lower(func.coalesce(Category.nom_ar, "")).like(pattern)
        )

    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    items = db.scalars(
        stmt.order_by(Activity.id.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return paginate(total, page, size, items)


@public_router.get("/activities/{activity_id}", response_model=ActivityRead)
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = db.scalar(
        select(Activity)
        .options(joinedload(Activity.category))
        .where(Activity.id == activity_id)
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Activité introuvable")
    return activity


@public_router.get("/activities/{activity_id}/availabilities", response_model=list[AvailabilityRead])
def list_activity_availabilities(activity_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(Availability)
        .where(Availability.activity_id == activity_id)
        .order_by(Availability.date, Availability.heure)
    ).all()


# ---------------------------------------------------------------------------
# Routes internes (service → service uniquement)
# ---------------------------------------------------------------------------

internal_router = APIRouter(prefix="/internal", dependencies=[Depends(require_internal_key)])


@internal_router.get("/stats/activities")
def activity_stats(db: Session = Depends(get_db)):
    return {
        "total": int(db.scalar(select(func.count(Activity.id))) or 0),
        "categories": int(db.scalar(select(func.count(Category.id))) or 0),
        "upcoming_availabilities": int(
            db.scalar(
                select(func.count(Availability.id)).where(
                    Availability.date >= datetime.now(timezone.utc).date()
                )
            )
            or 0
        ),
    }


@internal_router.get("/activities")
def internal_list_activities(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """Liste admin brute — le booking-count est ajouté par l'admin-service."""
    total = int(db.scalar(select(func.count(Activity.id))) or 0)
    rows = db.execute(
        select(Activity, Category.nom)
        .join(Category, Activity.category_id == Category.id, isouter=True)
        .order_by(Activity.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    items = [
        {
            "id": a.id,
            "titre": a.titre,
            "prix": float(a.prix or 0.0),
            "duree": a.duree,
            "localisation": a.localisation,
            "category": category_name,
        }
        for a, category_name in rows
    ]
    return paginate(total, page, size, items)


@internal_router.get("/activities/batch")
def activities_batch(ids: str = Query(...), db: Session = Depends(get_db)):
    """Résolution en masse d'activités (id → titre, prix, photo)."""
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        return []
    if not id_list:
        return []
    activities = db.scalars(select(Activity).where(Activity.id.in_(id_list[:200]))).all()
    return [
        {
            "id": a.id,
            "titre": a.titre,
            "titre_en": a.titre_en,
            "titre_ar": a.titre_ar,
            "prix": float(a.prix or 0.0),
            # `photos` permet aux autres services (réservations) d'afficher la
            # vignette sans un second appel au catalogue.
            "photos": a.photos,
        }
        for a in activities
    ]


@internal_router.get("/availabilities/{availability_id}")
def get_availability(availability_id: int, db: Session = Depends(get_db)):
    row = db.get(Availability, availability_id)
    if not row:
        raise HTTPException(status_code=404, detail="Disponibilité introuvable")
    return {
        "id": row.id,
        "activity_id": row.activity_id,
        "date": row.date.isoformat(),
        "heure": row.heure.isoformat(),
        "places_disponibles": row.places_disponibles,
    }


@internal_router.post("/availabilities/{availability_id}/reserve")
def reserve_seat(availability_id: int, seats: int = 1, db: Session = Depends(get_db)):
    """Décrément atomique des places — appelé par le booking-service.

    UPDATE conditionnel : échoue proprement s'il n'y a plus de place
    (pas de race condition entre deux réservations concurrentes).
    """
    result = db.execute(
        update(Availability)
        .where(
            Availability.id == availability_id,
            Availability.places_disponibles >= seats,
        )
        .values(places_disponibles=Availability.places_disponibles - seats)
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=409, detail="Plus de place disponible sur ce créneau")
    return {"status": "reserved", "availability_id": availability_id, "seats": seats}


@internal_router.post("/availabilities/{availability_id}/release")
def release_seat(availability_id: int, seats: int = 1, db: Session = Depends(get_db)):
    """Compensation (annulation de réservation) — libère les places."""
    db.execute(
        update(Availability)
        .where(Availability.id == availability_id)
        .values(places_disponibles=Availability.places_disponibles + seats)
    )
    db.commit()
    return {"status": "released", "availability_id": availability_id, "seats": seats}
