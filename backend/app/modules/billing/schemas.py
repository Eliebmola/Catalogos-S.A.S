from datetime import date
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BillingAccountRead(BaseModel):
    owner_id: UUID
    email: str | None
    full_name: str | None
    catalog_count: int
    whatsapp_number: str | None
    paid_through: date | None
    trial_until: date | None
    extra_catalogs: int
    status: str
    access_override: bool | None
    legacy_grandfathered: bool


class WhatsAppContactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    whatsapp_number: Annotated[str, Field(min_length=8, max_length=16, pattern=r"^\+[1-9]\d{7,14}$")] | None


class AccessOverrideUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocked: bool | None


class ExtraCatalogsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    extra_catalogs: Annotated[int, Field(ge=0, le=100)]


class BillingProviderStatus(BaseModel):
    grace_days: int
    trial_days: int
    monthly_price_cop: int
    extra_catalog_price_cop: int
    max_image_bytes: int
    email_notifications_ready: bool
    whatsapp_notifications_ready: bool
    whatsapp_orders_ready: bool


class PlanInfoRead(BaseModel):
    status: str
    catalog_count: int
    included_catalogs: int
    extra_catalogs: int
    catalog_limit: int
    monthly_price_cop: int
    extra_catalog_price_cop: int
    monthly_total_cop: int
    trial_until: date | None
    paid_through: date | None
    grace_days: int
    billing_whatsapp_number: str | None
