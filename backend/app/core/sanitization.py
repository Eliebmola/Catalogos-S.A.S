"""Sanitización de texto libre. Defensa en profundidad: el frontend DEBE seguir escapando al renderizar."""

import re
import unicodedata
from typing import Annotated, Any

from pydantic import BeforeValidator

_TAG_RE = re.compile(r"<[^>]*>")
# Controles C0/C1 (salvo \t \n \r) y caracteres invisibles / de direccionalidad usados para spoofing.
_INVISIBLE_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]")


def clean_text(value: Any) -> Any:
    """Normaliza a NFC, elimina etiquetas HTML y caracteres invisibles. No-str pasa intacto
    (pydantic reportará el error de tipo)."""
    if not isinstance(value, str):
        return value
    value = unicodedata.normalize("NFC", value)
    value = _TAG_RE.sub("", value)
    value = _INVISIBLE_RE.sub("", value)
    return value.strip()


# Se aplica ANTES de las restricciones de longitud: "<b></b>" queda vacío y falla min_length.
CleanStr = Annotated[str, BeforeValidator(clean_text)]
