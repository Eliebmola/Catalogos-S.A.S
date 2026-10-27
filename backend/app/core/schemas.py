"""Esquemas transversales."""

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Forma única de todas las respuestas de error de la API."""

    error: str
    code: int
    type: str
    details: Any | None = None
