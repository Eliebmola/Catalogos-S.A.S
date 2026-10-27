from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, ResourceNotFoundException, UnauthorizedActionException
from app.core.security import AuthenticatedUser
from app.modules.categories.repository import CategoryRepository
from app.modules.categories.schemas import CategoryCreate, CategoryUpdate
from app.modules.products.models import ProductCategory
from app.modules.stores.repository import StoreRepository


class CategoryService:
    def __init__(self, session: AsyncSession, categories: CategoryRepository, stores: StoreRepository) -> None:
        self.session = session
        self.categories = categories
        self.stores = stores

    async def _owned_store(self, owner: AuthenticatedUser, store_id: UUID):
        store = await self.stores.get_by_id(store_id)
        if store is None:
            raise ResourceNotFoundException("El catálogo no existe.")
        if store.owner_id != owner.id:
            raise UnauthorizedActionException("No tienes permiso para modificar este catálogo.")
        return store

    async def list(self, owner: AuthenticatedUser, store_id: UUID) -> list[ProductCategory]:
        await self._owned_store(owner, store_id)
        return await self.categories.list_by_store(store_id)

    async def create(self, owner: AuthenticatedUser, store_id: UUID, data: CategoryCreate) -> ProductCategory:
        await self._owned_store(owner, store_id)
        item = ProductCategory(store_id=store_id, name=data.name)
        self.session.add(item)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictException("Ya existe una categoría con ese nombre en este catálogo.") from exc
        return item

    async def update(self, owner: AuthenticatedUser, store_id: UUID, category_id: UUID,
                     data: CategoryUpdate) -> ProductCategory:
        await self._owned_store(owner, store_id)
        item = await self.categories.get(store_id, category_id)
        if item is None:
            raise ResourceNotFoundException("La categoría no existe.")
        item.name = data.name
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictException("Ya existe una categoría con ese nombre en este catálogo.") from exc
        return item

    async def delete(self, owner: AuthenticatedUser, store_id: UUID, category_id: UUID) -> None:
        await self._owned_store(owner, store_id)
        item = await self.categories.get(store_id, category_id)
        if item is None:
            raise ResourceNotFoundException("La categoría no existe.")
        await self.session.delete(item)
        await self.session.commit()
