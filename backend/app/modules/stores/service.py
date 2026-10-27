import logging
from collections.abc import Sequence
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationException, ConflictException, ResourceNotFoundException, UnauthorizedActionException
from app.core.security import AuthenticatedUser
from app.modules.stores.models import Store
from app.modules.stores.repository import StoreRepository
from app.modules.stores.schemas import StoreCreate, StoreUpdate
from app.modules.users.repository import UserRepository
from app.modules.billing.models import Subscription
from app.modules.billing.service import subscription_status
from typing import Protocol
from app.core.storage import SupabaseStorage


class SubscriptionAccessPort(Protocol):
    async def get_subscription(self, owner_id: UUID) -> Subscription | None: ...
    async def ensure_subscription(self, owner_id: UUID) -> Subscription: ...

logger = logging.getLogger(__name__)


class StoreService:
    def __init__(self, session: AsyncSession, stores: StoreRepository, users: UserRepository,
                 subscriptions: SubscriptionAccessPort | None = None, today: date | None = None,
                 grace_days: int = 2, storage: SupabaseStorage | None = None,
                 trial_days: int = 6) -> None:
        self._session = session
        self._stores = stores
        self._users = users
        self._subscriptions = subscriptions
        self._today = today or date.today()
        self._grace_days = grace_days
        self._storage = storage
        self._trial_days = trial_days

    async def create_store(self, owner: AuthenticatedUser, data: StoreCreate) -> Store:
        if await self._stores.get_by_slug(data.slug):
            raise ConflictException("Ese slug ya está en uso. Elige otro.")

        is_new_account = await self._users.ensure_exists(owner.id, owner.email)
        if self._subscriptions is not None:
            subscription = await self._subscriptions.get_subscription(owner.id)
            if subscription is None and is_new_account:
                subscription = await self._subscriptions.ensure_subscription(owner.id)
                subscription.trial_until = self._today + timedelta(days=self._trial_days - 1)
                subscription.legacy_grandfathered = False
            elif subscription is not None and is_new_account:
                subscription.trial_until = self._today + timedelta(days=self._trial_days - 1)
                subscription.legacy_grandfathered = False
            elif subscription is None:
                subscription = await self._subscriptions.ensure_subscription(owner.id)
            access = subscription_status(subscription, self._today, self._grace_days)
            if subscription.legacy_grandfathered:
                access = "legacy"
            if access in {"blocked", "pending_payment", "suspended"}:
                raise BusinessRuleViolationException("Tu suscripción está vencida o bloqueada. Solicita la renovación para crear catálogos.")
            count = await self._stores.count_by_owner(owner.id)
            limit = 2 + subscription.extra_catalogs
            if count >= limit:
                raise BusinessRuleViolationException(
                    f"Tu plan incluye {limit} catálogos. Solicita una ampliación para agregar otro."
                )
        store = Store(owner_id=owner.id, **data.model_dump())
        try:
            await self._stores.add(store)
            await self._session.commit()
        except IntegrityError as exc:  # carrera: otro request tomó el slug entre el SELECT y el INSERT
            await self._session.rollback()
            raise ConflictException("Ese slug ya está en uso. Elige otro.") from exc

        logger.info("store_created store_id=%s owner_id=%s", store.id, owner.id)
        return store

    async def list_my_stores(self, owner: AuthenticatedUser) -> Sequence[Store]:
        return await self._stores.list_by_owner(owner.id)

    async def update_publication(
        self, owner: AuthenticatedUser, store_id: UUID, is_published: bool
    ) -> Store:
        store = await self._stores.get_by_id(store_id)
        if store is None:
            raise ResourceNotFoundException("El catálogo no existe.")
        if store.owner_id != owner.id:
            raise UnauthorizedActionException("No tienes permiso para modificar este catálogo.")
        if is_published and self._subscriptions is not None:
            subscription = await self._subscriptions.get_subscription(owner.id)
            access = subscription_status(
                subscription, self._today, self._grace_days
            )
            if subscription is not None and (
                subscription.access_override is True
                or (not subscription.legacy_grandfathered and access in {"pending_payment", "suspended"})
            ):
                raise BusinessRuleViolationException("El catálogo no se puede publicar mientras la cuenta esté suspendida.")
        store.is_published = is_published
        await self._session.commit()
        return store

    async def update_profile(self, owner: AuthenticatedUser, store_id: UUID, data: StoreUpdate) -> Store:
        store = await self._owned_store(owner, store_id)
        changes = data.model_dump(exclude_unset=True)
        next_whatsapp = changes.get("whatsapp_number", store.whatsapp_number)
        next_opt_in = changes.get("whatsapp_orders_opt_in", store.whatsapp_orders_opt_in)
        if next_opt_in and not next_whatsapp:
            raise BusinessRuleViolationException("Agrega primero tu WhatsApp de contacto para activar los pedidos automáticos.")
        for field, value in changes.items():
            setattr(store, field, value)
        await self._session.commit()
        return store

    async def get_owned_store(self, owner: AuthenticatedUser, store_id: UUID) -> Store:
        return await self._owned_store(owner, store_id)

    async def _owned_store(self, owner: AuthenticatedUser, store_id: UUID) -> Store:
        store = await self._stores.get_by_id(store_id)
        if store is None:
            raise ResourceNotFoundException("La tienda no existe.")
        if store.owner_id != owner.id:
            raise UnauthorizedActionException("No tienes permiso para modificar esta tienda.")
        return store

    async def update_brand_image(
        self, owner: AuthenticatedUser, store_id: UUID, path: str | None, url: str | None
    ) -> tuple[Store, str | None]:
        store = await self._owned_store(owner, store_id)
        previous_path = store.brand_image_path
        store.brand_image_path = path
        store.brand_image_url = url
        await self._session.commit()
        return store, previous_path

    async def delete_store(self, owner: AuthenticatedUser, store_id: UUID, confirmation_name: str) -> None:
        store = await self._owned_store(owner, store_id)
        if confirmation_name != store.name:
            raise BusinessRuleViolationException("El nombre no coincide. El catálogo no se eliminó.")
        image_paths = await self._stores.list_image_paths(store_id)
        if store.brand_image_path:
            image_paths.append(store.brand_image_path)
        if self._storage is not None:
            for path in image_paths:
                await self._storage.remove(path, best_effort=True)
        elif image_paths:
            logger.warning("store_deleted_with_unavailable_image_storage store_id=%s", store_id)
        await self._stores.delete(store)
        await self._session.commit()
        logger.info("store_deleted store_id=%s owner_id=%s", store_id, owner.id)
