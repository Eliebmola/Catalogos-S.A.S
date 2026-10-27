from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.products.models import ProductCategory


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_store(self, store_id: UUID) -> list[ProductCategory]:
        stmt = select(ProductCategory).where(ProductCategory.store_id == store_id).order_by(ProductCategory.name)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, store_id: UUID, category_id: UUID) -> ProductCategory | None:
        stmt = select(ProductCategory).where(
            ProductCategory.store_id == store_id, ProductCategory.id == category_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
