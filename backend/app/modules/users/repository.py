from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.billing.models import Subscription


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_exists(self, user_id: UUID, email: str | None) -> bool:
        """Alta idempotente y segura ante concurrencia del perfil (INSERT … ON CONFLICT DO NOTHING)."""
        stmt = (
            pg_insert(User)
            .values(id=user_id, email=email)
            .on_conflict_do_nothing(index_elements=[User.id])
        )
        result = await self._session.execute(stmt.returning(User.id))
        created = result.scalar_one_or_none() is not None
        if created:
            # La capa de onboarding asigna la fecha de fin de prueba a esta nueva suscripción.
            self._session.add(Subscription(owner_id=user_id))
        return created
