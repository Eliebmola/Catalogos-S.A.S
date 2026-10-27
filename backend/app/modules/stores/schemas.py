from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.sanitization import CleanStr

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
# Rutas que el frontend podría usar: un vendedor no debe poder "secuestrarlas" como slug.
RESERVED_SLUGS = frozenset(
    {"admin", "api", "app", "auth", "login", "logout", "signup", "dashboard", "settings",
     "static", "assets", "health", "docs", "www", "support", "help", "pricing", "terms", "privacy"}
)


class StoreCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Annotated[CleanStr, Field(min_length=2, max_length=120)]
    slug: Annotated[str, Field(min_length=3, max_length=63, pattern=SLUG_PATTERN)]
    description: Annotated[CleanStr, Field(max_length=500)] | None = None
    whatsapp_number: Annotated[str, Field(pattern=r"^\+[1-9]\d{7,14}$")] | None = Field(
        default=None, description="Formato E.164, ej. +573001234567"
    )
    instagram_handle: Annotated[str, Field(pattern=r"^[A-Za-z0-9._]{1,30}$")] | None = None
    is_published: bool = False

    @field_validator("slug", mode="before")
    @classmethod
    def _normalize_slug(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("slug")
    @classmethod
    def _slug_not_reserved(cls, value: str) -> str:
        if value in RESERVED_SLUGS:
            raise ValueError("Este slug está reservado")
        return value

    @field_validator("instagram_handle", mode="before")
    @classmethod
    def _strip_at(cls, value: Any) -> Any:
        return value.strip().lstrip("@") if isinstance(value, str) else value


class StoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None
    whatsapp_number: str | None
    whatsapp_orders_opt_in: bool
    instagram_handle: str | None
    brand_image_url: str | None
    is_published: bool
    created_at: datetime
    updated_at: datetime


class StorePublicationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_published: bool


class StoreDeleteConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    confirmation_name: Annotated[str, Field(min_length=2, max_length=120)]


class StoreUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Annotated[CleanStr, Field(min_length=2, max_length=120)] | None = None
    description: Annotated[CleanStr, Field(max_length=500)] | None = None
    whatsapp_number: Annotated[str, Field(pattern=r"^\+[1-9]\d{7,14}$")] | None = None
    whatsapp_orders_opt_in: bool | None = None
    instagram_handle: Annotated[str, Field(pattern=r"^[A-Za-z0-9._]{1,30}$")] | None = None

    @field_validator("instagram_handle", mode="before")
    @classmethod
    def _strip_at(cls, value: Any) -> Any:
        return value.strip().lstrip("@") if isinstance(value, str) else value

    @model_validator(mode="after")
    def _non_empty(self):
        if not self.model_fields_set:
            raise ValueError("Indica al menos un dato para actualizar")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("El nombre de la marca es obligatorio")
        return self
