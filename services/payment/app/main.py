import logging
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from voyara_common.exceptions import register_exception_handlers
from voyara_common.internal import require_internal_key
from voyara_common.logging import setup_logging
from voyara_common.pagination import paginate

from app.checkout import checkout_router
from app.config import settings
from app.database import Base, engine, get_db
from app.models import Payment, PaymentStatus

setup_logging(settings.SERVICE_NAME)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Service de paiement Voyara (intégration Stripe : Phase 8).",
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
    return {
        "service": settings.SERVICE_NAME,
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "payment_mode": "stripe" if settings.stripe_enabled else "simulation",
    }


app.include_router(checkout_router, prefix=settings.API_V1_PREFIX)


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _payment_dict(p: Payment) -> dict:
    return {
        "id": p.id,
        "booking_id": p.booking_id,
        "montant": float(p.montant or 0.0),
        "type": p.type.value,
        "methode": p.methode,
        "statut": p.statut.value,
        "date_paiement": p.date_paiement,
    }


@app.get("/internal/stats/revenue", dependencies=[Depends(require_internal_key)])
def revenue_stats(db: Session = Depends(get_db)):
    """Chiffre d'affaires basé sur les paiements réussis.

    Le fallback « aucun paiement → somme des réservations confirmées »
    est appliqué par l'admin-service (donnée du booking-service).
    """
    paid = select(func.coalesce(func.sum(Payment.montant), 0.0)).where(
        Payment.statut == PaymentStatus.succeeded
    )

    def total_of(stmt) -> float:
        return float(db.scalar(stmt) or 0.0)

    return {
        "total": round(total_of(paid), 2),
        "last_30_days": round(total_of(paid.where(Payment.date_paiement >= _since(30))), 2),
        "pending": round(
            total_of(
                select(func.coalesce(func.sum(Payment.montant), 0.0)).where(
                    Payment.statut == PaymentStatus.pending
                )
            ),
            2,
        ),
    }


@app.get("/internal/payments", dependencies=[Depends(require_internal_key)])
def internal_list_payments(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    total = int(db.scalar(select(func.count(Payment.id))) or 0)
    rows = db.scalars(
        select(Payment)
        .order_by(Payment.date_paiement.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return paginate(total, page, size, [_payment_dict(p) for p in rows])
