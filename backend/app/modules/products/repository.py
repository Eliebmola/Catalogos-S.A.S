from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.products.models import Product
from app.modules.products.models import ProductCategory


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, product: Product) -> Product:
        self._session.add(product)
        await self._session.flush()
        return product

    async def count_by_store(self, store_id: UUID) -> int:
        stmt = select(func.count()).select_from(Product).where(Product.store_id == store_id)
        return (await self._session.execute(stmt)).scalar_one()

    async def category_belongs_to_store(self, store_id: UUID, category_id: UUID) -> bool:
        stmt = select(ProductCategory.id).where(
            ProductCategory.store_id == store_id, ProductCategory.id == category_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def get_by_id(self, store_id: UUID, product_id: UUID) -> Product | None:
        stmt = select(Product).where(Product.store_id == store_id, Product.id == product_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_by_store(self, store_id: UUID) -> list[Product]:
        stmt = select(Product).where(Product.store_id == store_id).order_by(Product.sort_order, Product.created_at)
        return list((await self._session.execute(stmt)).scalars().all())

    async def delete(self, product: Product) -> None:
        await self._session.delete(product)
