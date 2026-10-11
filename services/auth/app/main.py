import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from voyara_common.exceptions import register_exception_handlers
from voyara_common.limiter import limiter, rate_limit_exceeded_handler
from voyara_common.logging import setup_logging

from app.config import settings
from app.routers.auth import router as auth_router
from app.routers.internal import router as internal_router

setup_logging(settings.SERVICE_NAME)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Service d'authentification et de gestion des comptes Voyara.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

app.add_middleware(SlowAPIMiddleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
register_exception_handlers(app)

# Fichiers statiques (avatars) — propriété du auth-service
static_dir = Path(__file__).resolve().parents[1] / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )
    response.headers["X-Process-Time-ms"] = f"{duration:.1f}"
    return response


@app.get("/health", tags=["Système"])
def health():
    return {"service": settings.SERVICE_NAME, "status": "ok", "environment": settings.ENVIRONMENT}


app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(internal_router)
