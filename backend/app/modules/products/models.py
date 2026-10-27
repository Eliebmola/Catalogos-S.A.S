from datetime import datetime  # noqa: F401  (usado por los mixins en anotaciones)
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    UniqueConstraint,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.stores.models import Store


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    store_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)  # dinero: nunca float
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="COP")
    image_path: Mapped[str | None] = mapped_column(String(500))  # ruta en Supabase Storage (para borrar)
    image_url: Mapped[str | None] = mapped_column(String(1000))  # URL pública servida al catálogo
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true(), default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"), default=0)

    store: Mapped["Store"] = relationship(back_populates="products", lazy="raise")
    category: Mapped["ProductCategory | None"] = relationship(back_populates="products", lazy="raise")

    @property
    def category_name(self) -> str | None:
        return self.category.name if self.category else None

    __table_args__ = (
        # Panel del vendedor (todos los productos de una tienda) y ON DELETE CASCADE.
        Index("ix_products_store_id", "store_id"),
        Index("ix_products_category_id", "category_id"),
        # Landing pública: índice PARCIAL (solo activos) y ya ordenado por sort_order → lectura mínima.
        Index(
            "ix_products_store_active_sort",
            "store_id",
            "sort_order",
            postgresql_where=text("is_active"),
        ),
        CheckConstraint("price >= 0", name="price_non_negative"),
        CheckConstraint("length(currency) = 3", name="currency_iso4217_len"),
    )


class ProductCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_categories"

    store_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    products: Mapped[list[Product]] = relationship(back_populates="category", lazy="raise", passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("store_id", "name", name="uq_product_categories_store_name"),
        Index("ix_product_categories_store_id", "store_id"),
    )
