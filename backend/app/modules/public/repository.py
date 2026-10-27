from datetime import date, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from app.modules.products.models import Product, ProductCategory
from app.modules.stores.models import Store
from app.modules.billing.models import Subscription
from app.modules.orders.models import StoreOrder


class PublicCatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_published_by_slug(self, slug: str, today: date, grace_days: int) -> Store | None:
        """Exactamente 2 consultas SIN importar cuántos productos haya (sin N+1):
        1) la tienda por slug (índice único)  2) sus productos activos con `IN` (índice parcial).
        `load_only` evita traer columnas innecesarias (owner_id, fechas, image_path…)."""
        stmt = (
            select(Store)
            .where(Store.slug == slug, Store.is_published.is_(True))
            .outerjoin(Subscription, Subscription.owner_id == Store.owner_id)
            .where(
                or_(
                    Subscription.owner_id.is_(None),  # compatibilidad con cuentas antiguas sin migración
                    Subscription.access_override.is_(False),
                    and_(
                        Subscription.access_override.is_(None),
                        or_(
                            Subscription.paid_through >= today - timedelta(days=grace_days),
                            Subscription.trial_until >= today - timedelta(days=grace_days),
                        ),
                    ),
                )
            )
            .options(
                load_only(
                    Store.id,
                    Store.owner_id,
                    Store.name,
                    Store.slug,
                    Store.description,
                    Store.whatsapp_number,
                    Store.whatsapp_orders_opt_in,
                    Store.instagram_handle,
                    Store.brand_image_url,
                ),
                selectinload(Store.products.and_(Product.is_active.is_(True))).load_only(
                    Product.is_active,
                    Product.name,
                    Product.description,
                    Product.price,
                    Product.currency,
                    Product.image_url,
                    Product.category_id,
                ).selectinload(Product.category).load_only(ProductCategory.name),
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create_order(self, order: StoreOrder) -> StoreOrder:
        self._session.add(order)
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(order)
        return order
