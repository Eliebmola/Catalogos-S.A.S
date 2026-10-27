from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin


class StoreOrder(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "store_orders"

    order_number: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    store_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("stores.id", ondelete="SET NULL"))
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    store_name: Mapped[str] = mapped_column(String(120), nullable=False)
    buyer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    buyer_phone: Mapped[str] = mapped_column(String(24), nullable=False)
    buyer_email: Mapped[str | None] = mapped_column(String(160))
    requires_shipping: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    city: Mapped[str | None] = mapped_column(String(100))
    neighborhood: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(180))
    privacy_consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    items: Mapped[list["StoreOrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="raise",
        order_by="StoreOrderItem.created_at",
    )

    __table_args__ = (
        CheckConstraint("status in ('new', 'contacted', 'completed', 'cancelled')", name="store_order_status"),
        Index("ix_store_orders_owner_created", "owner_id", "created_at"),
        Index("ix_store_orders_store_created", "store_id", "created_at"),
    )


class StoreOrderItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "store_order_items"

    order_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("store_orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    product_name: Mapped[str] = mapped_column(String(150), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1000))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order: Mapped[StoreOrder] = relationship(back_populates="items", lazy="raise")

    __table_args__ = (
        CheckConstraint("quantity between 1 and 99", name="store_order_item_quantity"),
        CheckConstraint("unit_price >= 0 and line_total >= 0", name="store_order_item_amounts"),
        Index("ix_store_order_items_order_id", "order_id"),
    )
