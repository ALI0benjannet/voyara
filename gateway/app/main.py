"""API Gateway Voyara — point d'entrée unique (port 8000).

Le frontend continue d'appeler http://localhost:8000/api/v1/... exactement
comme avec l'ancien monolithe : le gateway route chaque préfixe vers le
microservice propriétaire et bloque les endpoints internes.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | gateway | %(message)s")
logger = logging.getLogger("gateway")

# Table de routage : préfixe → service amont (ordre = priorité)
ROUTES: list[tuple[str, str, str]] = [
    ("/api/v1/auth", settings.AUTH_SERVICE_URL, "auth"),
    ("/api/v1/admin", settings.ADMIN_SERVICE_URL, "admin"),
    ("/api/v1/activities", settings.CATALOG_SERVICE_URL, "catalog"),
    ("/api/v1/categories", settings.CATALOG_SERVICE_URL, "catalog"),
    ("/api/v1/availabilities", settings.CATALOG_SERVICE_URL, "catalog"),
    ("/api/v1/stays", settings.CATALOG_SERVICE_URL, "catalog"),
    ("/api/v1/flights", settings.CATALOG_SERVICE_URL, "catalog"),
    ("/api/v1/car-rentals", settings.CATALOG_SERVICE_URL, "catalog"),
    ("/api/v1/transfers", settings.CATALOG_SERVICE_URL, "catalog"),
    ("/api/v1/prestataire", settings.CATALOG_SERVICE_URL, "catalog"),
    ("/api/v1/moderation", settings.CATALOG_SERVICE_URL, "catalog"),
    ("/api/v1/bookings", settings.BOOKING_SERVICE_URL, "booking"),
    ("/api/v1/payments", settings.PAYMENT_SERVICE_URL, "payment"),
    ("/api/v1/reviews", settings.REVIEW_SERVICE_URL, "review"),
    ("/api/v1/favorites", settings.REVIEW_SERVICE_URL, "review"),
    ("/static/activities", settings.CATALOG_SERVICE_URL, "catalog"),  # photos d'activités
    ("/static", settings.AUTH_SERVICE_URL, "auth"),  # avatars servis par auth-service
]

SERVICES_HEALTH = {
    "auth": settings.AUTH_SERVICE_URL,
    "catalog": settings.CATALOG_SERVICE_URL,
    "booking": settings.BOOKING_SERVICE_URL,
    "payment": settings.PAYMENT_SERVICE_URL,
    "review": settings.REVIEW_SERVICE_URL,
    "notification": settings.NOTIFICATION_SERVICE_URL,
    "admin": settings.ADMIN_SERVICE_URL,
}

# Headers hop-by-hop à ne pas retransmettre
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(
        timeout=settings.PROXY_TIMEOUT_SECONDS,
        headers={"accept-encoding": "identity"},
    )
    yield
    await app.state.client.aclose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Reverse-proxy des microservices Voyara.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Santé du gateway + de chaque microservice."""
    async def check(name: str, url: str) -> tuple[str, str]:
        try:
            resp = await app.state.client.get(f"{url}/health", timeout=3.0)
            return name, "ok" if resp.status_code == 200 else f"error ({resp.status_code})"
        except httpx.HTTPError:
            return name, "unreachable"

    results = await asyncio.gather(*(check(n, u) for n, u in SERVICES_HEALTH.items()))
    services = dict(results)
    all_ok = all(v == "ok" for v in services.values())
    return {
        "service": "gateway",
        "status": "ok" if all_ok else "degraded",
        "environment": settings.ENVIRONMENT,
        "services": services,
    }


@app.get("/")
async def index():
    return {
        "name": settings.PROJECT_NAME,
        "routes": [
            {"prefix": prefix, "service": name} for prefix, _, name in ROUTES
        ],
        "docs": {
            name: f"{url}/docs"
            for name, url in SERVICES_HEALTH.items()
            if name != "notification"
        },
    }


def _resolve(path: str) -> tuple[str, str] | None:
    for prefix, upstream, name in ROUTES:
        if path == prefix or path.startswith(prefix + "/"):
            return upstream, name
    return None


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy(path: str, request: Request):
    full_path = "/" + path

    # Les endpoints internes ne sont JAMAIS accessibles depuis l'extérieur
    if "/internal" in full_path:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    resolved = _resolve(full_path)
    if resolved is None:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    upstream, service_name = resolved
    url = f"{upstream}{full_path}"

    # Transfert des headers (en conservant Host pour que les URLs générées
    # par les services — ex. avatars — pointent vers le gateway)
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP and k.lower() != "accept-encoding"
    }
    client_host = request.client.host if request.client else "unknown"
    headers["x-forwarded-for"] = request.headers.get("x-forwarded-for", client_host)
    headers["x-forwarded-proto"] = request.url.scheme

    body = await request.body()
    start = time.perf_counter()
    try:
        upstream_resp = await request.app.state.client.request(
            request.method,
            url,
            params=request.url.query,
            content=body,
            headers=headers,
        )
    except httpx.HTTPError:
        logger.exception("Service '%s' injoignable (%s)", service_name, url)
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "detail": f"Le service '{service_name}' est momentanément indisponible",
            },
        )

    duration = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s [%s] (%.1f ms)",
        request.method,
        full_path,
        upstream_resp.status_code,
        service_name,
        duration,
    )

    response_headers = {
        k: v for k, v in upstream_resp.headers.items() if k.lower() not in HOP_BY_HOP
    }
    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=response_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )
