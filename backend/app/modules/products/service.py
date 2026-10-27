"""Lógica de negocio de productos. Depende de ABSTRACCIONES (Protocols), no de implementaciones:
no importa el módulo `stores` ni SQLAlchemy (DIP / ISP) y es trivial de testear con dobles."""

import logging
from datetime import date
from typing import Protocol
from uuid import UUID

from app.core.exceptions import (
    BusinessRuleViolationException,
    ResourceNotFoundException,
    UnauthorizedActionException,
)
from app.core.security import AuthenticatedUser
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate, ProductUpdate
from app.modules.billing.service import subscription_status
from app.modules.billing.models import Subscription

logger = logging.getLogger(__name__)


class StoreOwnershipPort(Protocol):
    async def get_by_id_for_update(self, store_id: UUID): ...  # -> objeto con .id y .owner_id | None
    async def get_by_id(self, store_id: UUID): ...


class ProductRepositoryPort(Protocol):
    async def add(self, product: Product) -> Product: ...
    async def count_by_store(self, store_id: UUID) -> int: ...
    async def list_by_store(self, store_id: UUID) -> list[Product]: ...
    async def category_belongs_to_store(self, store_id: UUID, category_id: UUID) -> bool: ...
    async def get_by_id(self, store_id: UUID, product_id: UUID) -> Product | None: ...
    async def delete(self, product: Product) -> None: ...


class UnitOfWork(Protocol):
    async def commit(self) -> None: ...


class SubscriptionAccessPort(Protocol):
    async def get_subscription(self, owner_id: UUID) -> Subscription | None: ...


class ProductService:
    def __init__(
        self,
        uow: UnitOfWork,
        products: ProductRepositoryPort,
        stores: StoreOwnershipPort,
        max_products_per_store: int,
        subscriptions: SubscriptionAccessPort | None = None,
        today: date | None = None,
        grace_days: int = 2,
    ) -> None:
        self._uow = uow
        self._products = products
        self._stores = stores
        self._max_products = max_products_per_store
        self._subscriptions = subscriptions
        self._today = today or date.today()
        self._grace_days = grace_days

    async def list_products(self, owner: AuthenticatedUser, store_id: UUID) -> list[Product]:
        store = await self._stores.get_by_id(store_id)
        if store is None:
            raise ResourceNotFoundException("La tienda no existe.")
        if store.owner_id != owner.id:
            raise UnauthorizedActionException("No tienes permiso para consultar esta tienda.")
        return await self._products.list_by_store(store_id)

    async def create_product(
        self, owner: AuthenticatedUser, store_id: UUID, data: ProductCreate
    ) -> Product:
        # 1) Existencia + 2) PROPIEDAD, verificadas en backend. La fila se bloquea (FOR UPDATE)
        #    para que el conteo de abajo no pueda superarse con requests concurrentes.
        store = await self._stores.get_by_id_for_update(store_id)
        if store is None:
            raise ResourceNotFoundException("La tienda no existe.")
        if store.owner_id != owner.id:
            logger.warning("forbidden_product_create user_id=%s store_id=%s", owner.id, store_id)
            raise UnauthorizedActionException("No tienes permiso para modificar esta tienda.")

        if self._subscriptions is not None:
            status = subscription_status(
                await self._subscriptions.get_subscription(owner.id), self._today, self._grace_days
            )
            if status in {"blocked", "pending_payment", "suspended"}:
                raise BusinessRuleViolationException(
                    "La cuenta está suspendida o pendiente de pago; contacta al administrador."
                )

        if data.category_id is not None and not await self._products.category_belongs_to_store(store_id, data.category_id):
            raise BusinessRuleViolationException("La categoría seleccionada no pertenece a este catálogo.")

        # 3) Regla de negocio (límite del plan).
        if await self._products.count_by_store(store_id) >= self._max_products:
            raise BusinessRuleViolationException(
                f"Alcanzaste el límite de {self._max_products} productos para esta tienda."
            )

        # 4) Persistencia. Los datos ya vienen validados y saneados por Pydantic.
        product = Product(store_id=store_id, **data.model_dump())
        await self._products.add(product)
        await self._uow.commit()

        logger.info("product_created product_id=%s store_id=%s", product.id, store_id)
        return product

    async def update_product(
        self, owner: AuthenticatedUser, store_id: UUID, product_id: UUID, data: ProductUpdate
    ) -> Product:
        store = await self._stores.get_by_id(store_id)
        if store is None:
            raise ResourceNotFoundException("La tienda no existe.")
        if store.owner_id != owner.id:
            raise UnauthorizedActionException("No tienes permiso para modificar esta tienda.")
        if self._subscriptions is not None:
            status = subscription_status(
                await self._subscriptions.get_subscription(owner.id), self._today, self._grace_days
            )
            if status in {"blocked", "pending_payment", "suspended"}:
                raise BusinessRuleViolationException(
                    "La cuenta está suspendida o pendiente de pago; contacta al administrador."
                )
        product = await self._products.get_by_id(store_id, product_id)
        if product is None:
            raise ResourceNotFoundException("El producto no existe.")
        if data.category_id is not None and not await self._products.category_belongs_to_store(store_id, data.category_id):
            raise BusinessRuleViolationException("La categoría seleccionada no pertenece a este catálogo.")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)
        await self._uow.commit()
        logger.info("product_updated product_id=%s store_id=%s", product.id, store_id)
        return product
