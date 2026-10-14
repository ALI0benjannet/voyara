import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from voyara_common.exceptions import register_exception_handlers
from voyara_common.logging import setup_logging

from app.config import settings
from app.database import Base, engine
from app.expiry import expiry_sweeper
from app.routers import internal_router, public_router

setup_logging(settings.SERVICE_NAME)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Cycle de vie du service : démarre le balayage des réservations expirées.

    La tâche est annulée proprement à l'arrêt, sinon uvicorn attendrait
    indéfiniment une boucle qui ne se termine jamais.
    """
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables vérifiées/créées (AUTO_CREATE_TABLES=true)")

    sweeper: asyncio.Task | None = None
    if settings.BOOKING_EXPIRY_ENABLED:
        sweeper = asyncio.create_task(expiry_sweeper())
    else:
        logger.warning("Expiration des reservations DESACTIVEE (BOOKING_EXPIRY_ENABLED=false)")

    try:
        yield
    finally:
        if sweeper is not None:
            sweeper.cancel()
            # `CancelledError` est attendue ici : c'est la façon normale de
            # terminer la boucle.
            await asyncio.gather(sweeper, return_exceptions=True)
            logger.info("Balayage des reservations expirees arrete")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Service de réservation : bookings et codes promo.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

register_exception_handlers(app)


@app.get("/health", tags=["Système"])
def health():
    return {"service": settings.SERVICE_NAME, "status": "ok", "environment": settings.ENVIRONMENT}


app.include_router(public_router, prefix=settings.API_V1_PREFIX)
app.include_router(internal_router)
