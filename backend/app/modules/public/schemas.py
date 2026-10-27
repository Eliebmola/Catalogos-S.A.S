"""Contrato mínimo de la landing: solo lo que el visitante necesita (sin owner_id, fechas, flags internos)."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PublicProduct(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    price: Decimal
    currency: str
    image_url: str | None
    category_name: str | None


class PublicCatalog(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    slug: str
    description: str | None
    whatsapp_number: str | None
    whatsapp_orders_enabled: bool
    instagram_handle: str | None
    brand_image_url: str | None
    products: list[PublicProduct]


class PublicOrderLineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: UUID
    quantity: Annotated[int, Field(ge=1, le=99)]


class PublicOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    buyer_name: Annotated[str, Field(min_length=2, max_length=120)]
    buyer_phone: Annotated[str, Field(min_length=8, max_length=24)]
    buyer_email: Annotated[str, Field(max_length=160, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")] | None = None
    requires_shipping: bool = False
    city: Annotated[str, Field(max_length=100)] | None = None
    neighborhood: Annotated[str, Field(max_length=100)] | None = None
    address: Annotated[str, Field(max_length=180)] | None = None
    privacy_consent: bool
    items: Annotated[list[PublicOrderLineIn], Field(min_length=1, max_length=10)]

    @field_validator("buyer_phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: Any) -> Any:
        if isinstance(value, str):
            return "".join(c for c in value.strip() if c.isdigit() or c == "+")
        return value

    @model_validator(mode="after")
    def validate_order(self):
        if not self.privacy_consent:
            raise ValueError("Debes autorizar que el vendedor reciba los datos de este pedido.")
        if self.requires_shipping and not all((self.city, self.neighborhood, self.address)):
            raise ValueError("Completa la ciudad, el barrio y la dirección para solicitar envío.")
        if len({item.product_id for item in self.items}) != len(self.items):
            raise ValueError("Cada producto debe aparecer una sola vez en el pedido.")
        return self


class PublicOrderLineRead(BaseModel):
    product_id: UUID
    name: str
    image_url: str | None
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    currency: str


class PublicOrderReceipt(BaseModel):
    id: str
    created_at: datetime
    catalog_name: str
    buyer_name: str
    buyer_phone: str
    buyer_email: str | None
    requires_shipping: bool
    city: str | None
    neighborhood: str | None
    address: str | None
    items: list[PublicOrderLineRead]
    totals: dict[str, Decimal]
    saved_for_seller: bool
    whatsapp_url: str | None
