"""Manejo global de excepciones: toda respuesta de error comparte la misma forma JSON
y jamás expone trazas internas al cliente (las trazas van solo al log del servidor)."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import Settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

_HTTP_MESSAGES = {
    404: "Recurso no encontrado.",
    405: "Método no permitido.",
    429: "Demasiadas solicitudes. Intenta de nuevo en unos instantes.",
}


def _error_response(
    status_code: int,
    message: str,
    error_type: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {"error": message, "code": status_code, "type": error_type}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def register_exception_handlers(app: FastAPI, settings: Settings) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("AppException %s en %s %s", exc.error_type, request.method, request.url.path)
        return _error_response(
            exc.status_code, exc.message, exc.error_type, exc.details, exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Solo campo + mensaje: se omite 'input' y 'ctx' para no reflejar datos del cliente.
        details = [
            {"field": ".".join(str(part) for part in err["loc"]), "message": err["msg"].removeprefix("Value error, ")}
            for err in exc.errors()
        ]
        return _error_response(
            422, "Los datos enviados no son válidos.", "validation_error", details
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = _HTTP_MESSAGES.get(exc.status_code) or (
            exc.detail if isinstance(exc.detail, str) else "Error en la solicitud."
        )
        return _error_response(
            exc.status_code, message, "http_error", headers=getattr(exc, "headers", None)
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Error no controlado en %s %s", request.method, request.url.path)
        details = {"exception": repr(exc)} if settings.debug and not settings.is_production else None
        return _error_response(
            500, "Ocurrió un error interno. Inténtalo de nuevo más tarde.", "internal_error", details
        )
