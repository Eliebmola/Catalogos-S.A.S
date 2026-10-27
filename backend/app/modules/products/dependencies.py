from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings
from app.core.database import DbSession
from app.modules.products.repository import ProductRepository
from app.modules.products.service import ProductService
from app.modules.products.image_service import ProductImageService
from app.core.storage import SupabaseStorage
from app.modules.billing.repository import BillingRepository
from datetime import datetime
from zoneinfo import ZoneInfo
from app.modules.stores.repository import StoreRepository


def get_product_service(session: DbSession, request: Request) -> ProductService:
    """Composition root del módulo: aquí (y solo aquí) se cablean las implementaciones concretas."""
    settings: Settings = request.app.state.settings
    return ProductService(
        uow=session,
        products=ProductRepository(session),
        stores=StoreRepository(session),
        max_products_per_store=settings.max_products_per_store,
        subscriptions=BillingRepository(session),
        today=datetime.now(ZoneInfo(settings.app_timezone)).date(),
        grace_days=settings.billing_grace_days,
    )


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]


def get_product_image_service(session: DbSession, request: Request) -> ProductImageService:
    settings: Settings = request.app.state.settings
    return ProductImageService(
        session,
        ProductRepository(session),
        StoreRepository(session),
        SupabaseStorage(settings) if settings.supabase_service_role_key else None,
        BillingRepository(session),
        datetime.now(ZoneInfo(settings.app_timezone)).date(),
        settings.billing_grace_days,
    )


ProductImageServiceDep = Annotated[ProductImageService, Depends(get_product_image_service)]
