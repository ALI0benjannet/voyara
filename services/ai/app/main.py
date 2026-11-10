"""Microservice `ai` — moteur IA de Voyara (port 8008, ADR-007).

Étape 3 : socle (configuration, base `voyara_ai` + pgvector, logs, limiteur, santé),
couche LLM hybride et client catalog. Étape 4 : module 1, compréhension du voyageur
(`POST /api/ai/comprendre`). Endpoints métier sous le préfixe `/api/ai` routé par le gateway.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from voyara_common.exceptions import register_exception_handlers
from voyara_common.limiter import limiter, rate_limit_exceeded_handler
from voyara_common.logging import setup_logging

from app.clients.catalog import ClientCatalog
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.llm.fabrique import creer_client_llm
from app.llm.journal import JournalLLM
from app.nlu.routes import router as router_nlu
from app.routes import router

setup_logging(settings.SERVICE_NAME)
logger = logging.getLogger(__name__)


def initialiser_base() -> None:
    """Extension pgvector (embeddings de l'étape 5) puis tables, si AUTO_CREATE_TABLES."""
    if not settings.AUTO_CREATE_TABLES:
        return
    with engine.begin() as connexion:
        connexion.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    logger.info("Extension vector et tables vérifiées/créées (AUTO_CREATE_TABLES=true)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialiser_base()
    app.state.llm = creer_client_llm(settings, JournalLLM(SessionLocal))
    app.state.catalog = ClientCatalog(settings.CATALOG_SERVICE_URL, settings.CATALOG_TIMEOUT_S)
    logger.info("Fournisseur LLM : %s (clé Claude %s)", settings.LLM_PROVIDER,
                "présente" if settings.ANTHROPIC_API_KEY else "absente")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Moteur IA : compréhension, recherche, recommandation, itinéraire, agent.",
    version="0.4.0",
    docs_url="/docs",
    redoc_url=None,
    openapi_url=f"{settings.API_AI_PREFIX}/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
register_exception_handlers(app)


@app.get("/health", tags=["Système"])
def health():
    """Santé minimale, interrogée par le /health agrégé du gateway."""
    return {"service": settings.SERVICE_NAME, "status": "ok", "environment": settings.ENVIRONMENT}


app.include_router(router, prefix=settings.API_AI_PREFIX)
app.include_router(router_nlu, prefix=settings.API_AI_PREFIX)
