from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.products.models import Product
    from app.modules.users.models import User


class Store(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stores"

    owner_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    whatsapp_number: Mapped[str | None] = mapped_column(String(16))  # E.164: +573001234567
    whatsapp_orders_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), default=False)
    instagram_handle: Mapped[str | None] = mapped_column(String(30))
    brand_image_path: Mapped[str | None] = mapped_column(String(500))
    brand_image_url: Mapped[str | None] = mapped_column(String(1000))
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false(), default=False
    )

    owner: Mapped["User"] = relationship(back_populates="stores", lazy="raise")
    products: Mapped[list["Product"]] = relationship(
        back_populates="store",
        lazy="raise",  # se carga solo de forma explícita con selectinload()
        order_by="(Product.sort_order, Product.created_at)",
        passive_deletes=True,
    )

    @property
    def whatsapp_orders_enabled(self) -> bool:
        return bool(self.whatsapp_number and self.whatsapp_orders_opt_in)

    __table_args__ = (
        # Índice único explícito: sirve a la landing pública (WHERE slug = :slug) y garantiza unicidad.
        Index("ix_stores_slug", "slug", unique=True),
        # Las FK en PostgreSQL NO se indexan solas: acelera "mis tiendas" y los ON DELETE CASCADE.
        Index("ix_stores_owner_id", "owner_id"),
        # Defensa en BD (solo PostgreSQL; el operador ~ es regex POSIX).
        CheckConstraint(r"slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="slug_format").ddl_if(
            dialect="postgresql"
        ),
    )
