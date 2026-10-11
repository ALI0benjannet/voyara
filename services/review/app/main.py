import logging

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from voyara_common.auth import TokenIdentity, get_current_identity
from voyara_common.exceptions import register_exception_handlers
from voyara_common.internal import ServiceClient
from voyara_common.logging import setup_logging

from app.config import settings
from app.database import Base, engine, get_db
from app.models import Favorite, Review

setup_logging(settings.SERVICE_NAME)
logger = logging.getLogger(__name__)

catalog = ServiceClient(settings.CATALOG_SERVICE_URL)
booking = ServiceClient(settings.BOOKING_SERVICE_URL)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Service avis & favoris Voyara.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

register_exception_handlers(app)


@app.on_event("startup")
def init_db() -> None:
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables vérifiées/créées (AUTO_CREATE_TABLES=true)")


@app.get("/health", tags=["Système"])
def health():
    return {"service": settings.SERVICE_NAME, "status": "ok", "environment": settings.ENVIRONMENT}


# ---------------------------------------------------------------------------
# Avis
# ---------------------------------------------------------------------------

class ReviewCreate(BaseModel):
    activity_id: int
    note: int = Field(ge=1, le=5)
    commentaire: str | None = None


def _review_dict(r: Review) -> dict:
    return {
        "id": r.id,
        "user_id": r.user_id,
        "activity_id": r.activity_id,
        "note": r.note,
        "commentaire": r.commentaire,
        "date": r.date,
    }


@app.get(f"{settings.API_V1_PREFIX}/reviews/stats", tags=["Avis"])
def review_stats(activity_ids: str = Query(...), db: Session = Depends(get_db)):
    """Moyenne et nombre d'avis par activite — ex: ?activity_ids=1,2,3."""
    try:
        ids = [int(x) for x in activity_ids.split(",") if x.strip()]
    except ValueError:
        return {}
    if not ids:
        return {}
    rows = db.execute(
        select(Review.activity_id, func.avg(Review.note), func.count(Review.id))
        .where(Review.activity_id.in_(ids[:100]))
        .group_by(Review.activity_id)
    ).all()
    return {
        str(activity_id): {"average": round(float(avg), 1), "count": int(count)}
        for activity_id, avg, count in rows
    }


@app.get(f"{settings.API_V1_PREFIX}/reviews", tags=["Avis"])
def list_reviews(activity_id: int = Query(...), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Review).where(Review.activity_id == activity_id).order_by(Review.date.desc())
    ).all()
    return [_review_dict(r) for r in rows]


@app.post(f"{settings.API_V1_PREFIX}/reviews", status_code=status.HTTP_201_CREATED, tags=["Avis"])
async def create_review(
    payload: ReviewCreate,
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    # Seuls les clients ayant reserve l'activite peuvent deposer un avis
    try:
        check = await booking.get(
            "/internal/bookings/has-booked",
            params={"user_id": identity.user_id, "activity_id": payload.activity_id},
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=503, detail="Service reservations momentanement indisponible"
        )
    if not check.get("has_booked"):
        raise HTTPException(
            status_code=403,
            detail="Vous devez avoir reserve cette activite pour laisser un avis",
        )

    review = Review(
        user_id=identity.user_id,
        activity_id=payload.activity_id,
        note=payload.note,
        commentaire=payload.commentaire,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return _review_dict(review)


# ---------------------------------------------------------------------------
# Favoris
# ---------------------------------------------------------------------------

class FavoriteCreate(BaseModel):
    activity_id: int


@app.get(f"{settings.API_V1_PREFIX}/favorites", tags=["Favoris"])
async def list_favorites(
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(Favorite).where(Favorite.user_id == identity.user_id)).all()

    # Enrichissement avec les titres/prix du catalogue
    titles: dict[int, dict] = {}
    ids = sorted({f.activity_id for f in rows})
    if ids:
        try:
            data = await catalog.get(
                "/internal/activities/batch", params={"ids": ",".join(map(str, ids))}
            )
            titles = {item["id"]: item for item in data}
        except httpx.HTTPError:
            logger.warning("catalog-service injoignable — favoris non enrichis")

    return [
        {
            "id": f.id,
            "activity_id": f.activity_id,
            "activity": titles.get(f.activity_id),
        }
        for f in rows
    ]


@app.post(
    f"{settings.API_V1_PREFIX}/favorites", status_code=status.HTTP_201_CREATED, tags=["Favoris"]
)
def add_favorite(
    payload: FavoriteCreate,
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    fav = Favorite(user_id=identity.user_id, activity_id=payload.activity_id)
    db.add(fav)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Déjà dans les favoris")
    db.refresh(fav)
    return {"id": fav.id, "activity_id": fav.activity_id}


@app.delete(
    f"{settings.API_V1_PREFIX}/favorites/{{activity_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Favoris"],
)
def remove_favorite(
    activity_id: int,
    identity: TokenIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    db.query(Favorite).filter(
        Favorite.user_id == identity.user_id, Favorite.activity_id == activity_id
    ).delete()
    db.commit()
