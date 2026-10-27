from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.stores.models import Store
from app.modules.products.models import Product


class StoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, store_id: UUID) -> Store | None:
        return await self._session.get(Store, store_id)

    async def get_by_id_for_update(self, store_id: UUID) -> Store | None:
        """Bloquea la fila de la tienda hasta el commit: serializa operaciones concurrentes sobre
        la misma tienda (p. ej. el límite de productos)."""
        stmt = select(Store).where(Store.id == store_id).with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Store | None:
        stmt = select(Store).where(Store.slug == slug)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_by_owner(self, owner_id: UUID) -> Sequence[Store]:
        stmt = select(Store).where(Store.owner_id == owner_id).order_by(Store.created_at)
        return (await self._session.execute(stmt)).scalars().all()

    async def count_by_owner(self, owner_id: UUID) -> int:
        return int(await self._session.scalar(select(func.count(Store.id)).where(Store.owner_id == owner_id)) or 0)

    async def add(self, store: Store) -> Store:
        self._session.add(store)
        await self._session.flush()  # los repositorios hacen flush; el commit es de los servicios
        return store

    async def list_image_paths(self, store_id: UUID) -> list[str]:
        product_stmt = select(Product.image_path).where(
            Product.store_id == store_id, Product.image_path.is_not(None)
        )
        product_paths = [path for path in (await self._session.execute(product_stmt)).scalars().all() if path]
        return product_paths

    async def delete(self, store: Store) -> None:
        await self._session.delete(store)
