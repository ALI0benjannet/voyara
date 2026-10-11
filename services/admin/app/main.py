import logging

from fastapi import Depends, FastAPI, Query

from voyara_common.auth import require_admin
from voyara_common.exceptions import register_exception_handlers
from voyara_common.logging import setup_logging
from voyara_common.pagination import Page

from app import aggregator
from app.config import settings
from app.schemas import (
    AdminActivityRow,
    AdminBookingRow,
    AdminPaymentRow,
    AdminUserRow,
    DashboardStats,
)

setup_logging(settings.SERVICE_NAME)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Backend-for-frontend de l'espace administrateur : agrège les données "
        "des services auth, catalog, booking et payment."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

register_exception_handlers(app)


@app.get("/health", tags=["Système"])
def health():
    return {"service": settings.SERVICE_NAME, "status": "ok", "environment": settings.ENVIRONMENT}


PREFIX = f"{settings.API_V1_PREFIX}/admin"
admin_dep = Depends(require_admin)


@app.get(f"{PREFIX}/stats", response_model=DashboardStats, tags=["Administration"], dependencies=[admin_dep])
async def dashboard_stats():
    """Toutes les métriques du tableau de bord en un seul appel."""
    return await aggregator.dashboard_stats()


@app.get(f"{PREFIX}/users", response_model=Page[AdminUserRow], tags=["Administration"], dependencies=[admin_dep])
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, min_length=1, max_length=100),
):
    return await aggregator.list_users(page, size, search)


@app.get(f"{PREFIX}/bookings", response_model=Page[AdminBookingRow], tags=["Administration"], dependencies=[admin_dep])
async def list_bookings(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    statut: str | None = Query(None, pattern="^(pending|confirmed|cancelled)$"),
):
    return await aggregator.list_bookings(page, size, statut)


@app.get(f"{PREFIX}/activities", response_model=Page[AdminActivityRow], tags=["Administration"], dependencies=[admin_dep])
async def list_activities(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    return await aggregator.list_activities(page, size)


@app.get(f"{PREFIX}/payments", response_model=Page[AdminPaymentRow], tags=["Administration"], dependencies=[admin_dep])
async def list_payments(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    return await aggregator.list_payments(page, size)
