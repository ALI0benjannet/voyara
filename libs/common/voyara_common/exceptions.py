import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            # jsonable_encoder : un validateur qui lève ValueError place l'exception
            # elle-même dans `ctx`, non sérialisable telle quelle.
            content={"success": False, "detail": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(SQLAlchemyError)
    async def db_error(request: Request, exc: SQLAlchemyError):
        logger.exception("Erreur base de données: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": {"message": "Erreur base de données"}},
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        logger.exception("Erreur non gérée: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": {"message": "Erreur interne du serveur"}},
        )
