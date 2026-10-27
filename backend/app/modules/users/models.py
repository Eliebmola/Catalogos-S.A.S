from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.stores.models import Store


class User(TimestampMixin, Base):
    """Perfil público de la aplicación. `id` es EXACTAMENTE el `auth.users.id` de Supabase Auth
    (la fuente de verdad de credenciales); aquí solo viven datos propios del negocio."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)  # sin default: lo asigna Supabase Auth
    email: Mapped[str | None] = mapped_column(String(320))
    full_name: Mapped[str | None] = mapped_column(String(120))

    # lazy="raise": cualquier acceso lazy accidental falla ruidosamente (evita N+1 silenciosos).
    stores: Mapped[list["Store"]] = relationship(
        back_populates="owner", lazy="raise", passive_deletes=True
    )
