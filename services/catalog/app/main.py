import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from voyara_common.exceptions import register_exception_handlers
from voyara_common.logging import setup_logging

from app.admin_routes import admin_router
from app.config import settings
from app.database import Base, engine
from app.offres_routes import offres_router
from app.provider_routes import moderation_router, provider_router
from app.routers import internal_router, public_router
from app.travel_routes import travel_router

setup_logging(settings.SERVICE_NAME)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Service catalogue : activités, catégories et disponibilités.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

register_exception_handlers(app)

# Photos d'activités — propriété du catalog-service (gateway : /static/activities → ici)
static_dir = Path(__file__).resolve().parents[1] / "static"
(static_dir / "activities").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
def init_db() -> None:
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables vérifiées/créées (AUTO_CREATE_TABLES=true)")


@app.get("/health", tags=["Système"])
def health():
    return {"service": settings.SERVICE_NAME, "status": "ok", "environment": settings.ENVIRONMENT}


app.include_router(public_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
app.include_router(travel_router, prefix=settings.API_V1_PREFIX)
app.include_router(offres_router, prefix=settings.API_V1_PREFIX)
app.include_router(provider_router, prefix=settings.API_V1_PREFIX)
app.include_router(moderation_router, prefix=settings.API_V1_PREFIX)
app.include_router(internal_router)
