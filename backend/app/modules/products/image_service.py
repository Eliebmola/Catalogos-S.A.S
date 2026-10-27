import logging
from datetime import date
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationException, ExternalServiceException, ResourceNotFoundException, UnauthorizedActionException
from app.core.security import AuthenticatedUser
from app.core.storage import SupabaseStorage
from app.modules.products.models import Product
from app.modules.products.repository import ProductRepository
from app.modules.stores.repository import StoreRepository
from app.modules.billing.models import Subscription
from app.modules.billing.service import subscription_status


class SubscriptionAccessPort(Protocol):
    async def get_subscription(self, owner_id: UUID) -> Subscription | None: ...

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


class ProductImageService:
    def __init__(
        self,
        session: AsyncSession,
        products: ProductRepository,
        stores: StoreRepository,
        storage: SupabaseStorage | None,
        subscriptions: SubscriptionAccessPort,
        today: date,
        grace_days: int,
    ) -> None:
        self.session = session
        self.products = products
        self.stores = stores
        self.storage = storage
        self.subscriptions = subscriptions
        self.today = today
        self.grace_days = grace_days

    async def upload(
        self, owner: AuthenticatedUser, store_id: UUID, product_id: UUID,
        content: bytes, content_type: str,
    ) -> Product:
        if self.storage is None:
            raise ExternalServiceException(
                "No se pudo subir la imagen en este momento. Estamos revisando el servicio para solucionarlo pronto."
            )
        store = await self.stores.get_by_id(store_id)
        if store is None:
            raise ResourceNotFoundException("La tienda no existe.")
        if store.owner_id != owner.id:
            raise UnauthorizedActionException("No tienes permiso para modificar esta tienda.")
        status = subscription_status(
            await self.subscriptions.get_subscription(owner.id), self.today, self.grace_days
        )
        if status in {"blocked", "pending_payment", "suspended"}:
            raise BusinessRuleViolationException(
                "La cuenta está suspendida o pendiente de pago; contacta al administrador."
            )
        product = await self.products.get_by_id(store_id, product_id)
        if product is None:
            raise ResourceNotFoundException("El producto no existe.")

        extension = _IMAGE_EXTENSIONS[content_type]
        path = f"{store_id}/{product_id}/{uuid4().hex}.{extension}"
        image_url = await self.storage.upload(path, content, content_type)
        old_path = product.image_path
        try:
            product.image_path = path
            product.image_url = image_url
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            await self.storage.remove(path, best_effort=True)
            raise
        if old_path:
            await self.storage.remove(old_path, best_effort=True)
        logger.info("product_image_uploaded product_id=%s store_id=%s", product_id, store_id)
        return product

    async def remove_image(
        self, owner: AuthenticatedUser, store_id: UUID, product_id: UUID
    ) -> Product:
        product = await self._owned_product(owner, store_id, product_id)
        old_path = product.image_path
        if old_path:
            if self.storage is None:
                raise ExternalServiceException(
                    "No se pudo quitar la imagen en este momento. Inténtalo de nuevo pronto."
                )
            await self.storage.remove(old_path)
        product.image_path = None
        product.image_url = None
        await self.session.commit()
        return product

    async def delete_product(
        self, owner: AuthenticatedUser, store_id: UUID, product_id: UUID
    ) -> None:
        product = await self._owned_product(owner, store_id, product_id)
        if product.image_path:
            if self.storage is None:
                raise ExternalServiceException(
                    "No se pudo eliminar el producto en este momento. Inténtalo de nuevo pronto."
                )
            await self.storage.remove(product.image_path)
        await self.products.delete(product)
        await self.session.commit()

    async def _owned_product(
        self, owner: AuthenticatedUser, store_id: UUID, product_id: UUID
    ) -> Product:
        store = await self.stores.get_by_id(store_id)
        if store is None:
            raise ResourceNotFoundException("La tienda no existe.")
        if store.owner_id != owner.id:
            raise UnauthorizedActionException("No tienes permiso para modificar esta tienda.")
        status = subscription_status(
            await self.subscriptions.get_subscription(owner.id), self.today, self.grace_days
        )
        if status in {"blocked", "pending_payment", "suspended"}:
            raise BusinessRuleViolationException(
                "La cuenta está suspendida o pendiente de pago; contacta al administrador."
            )
        product = await self.products.get_by_id(store_id, product_id)
        if product is None:
            raise ResourceNotFoundException("El producto no existe.")
        return product
