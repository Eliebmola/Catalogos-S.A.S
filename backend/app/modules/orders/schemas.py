from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

OrderStatus = Literal["new", "contacted", "completed", "cancelled"]


class OrderItemRead(BaseModel):
    product_id: UUID
    product_name: str
    image_url: str | None
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    currency: str


class SellerOrderRead(BaseModel):
    id: UUID
    order_number: str
    store_name: str
    buyer_name: str
    buyer_phone: str
    buyer_email: str | None
    requires_shipping: bool
    city: str | None
    neighborhood: str | None
    address: str | None
    status: OrderStatus
    created_at: datetime
    items: list[OrderItemRead]
    totals: dict[str, Decimal]


class OrderStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: OrderStatus
