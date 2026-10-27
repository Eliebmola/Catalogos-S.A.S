from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.sanitization import CleanStr


class ProductCreate(BaseModel):
    """Entrada. extra='forbid' bloquea mass-assignment: el cliente no puede enviar store_id,
    image_url, id, etc. (el store viene de la URL; la imagen se gestiona por su propio endpoint)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Annotated[CleanStr, Field(min_length=2, max_length=150)]
    category_id: UUID | None = None
    description: Annotated[CleanStr, Field(max_length=2000)] | None = None
    price: Annotated[Decimal, Field(ge=0, lt=Decimal("10000000000"), max_digits=12, decimal_places=2)]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] = "COP"
    is_active: bool = True
    sort_order: Annotated[int, Field(ge=0, le=10_000)] = 0


class ProductUpdate(BaseModel):
    """Campos editables; las rutas de Storage nunca pueden modificarse desde este contrato."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Annotated[CleanStr, Field(min_length=2, max_length=150)] | None = None
    category_id: UUID | None = None
    description: Annotated[CleanStr, Field(max_length=2000)] | None = None
    price: Annotated[Decimal, Field(ge=0, lt=Decimal("10000000000"), max_digits=12, decimal_places=2)] | None = None
    is_active: bool | None = None
    sort_order: Annotated[int, Field(ge=0, le=10_000)] | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "ProductUpdate":
        if not self.model_fields_set:
            raise ValueError("Debes indicar al menos un campo para actualizar.")
        for field in ("name", "price", "is_active", "sort_order"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"El campo {field} no puede ser nulo.")
        return self


class ProductRead(BaseModel):
    """Salida. Nota: Decimal se serializa como string en JSON ("19990.00"), lo que evita
    errores de punto flotante en el cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    store_id: UUID
    category_id: UUID | None
    name: str
    description: str | None
    price: Decimal
    currency: str
    image_url: str | None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
