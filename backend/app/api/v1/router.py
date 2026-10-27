from fastapi import APIRouter

from app.modules.billing.router import router as billing_router
from app.modules.categories.router import router as categories_router
from app.modules.products.router import router as products_router
from app.modules.privacy.router import router as privacy_router
from app.modules.orders.router import router as orders_router
from app.modules.users.router import router as users_router
from app.modules.public.router import router as public_router
from app.modules.stores.router import router as stores_router
from app.modules.support.router import router as support_router

api_router = APIRouter()
api_router.include_router(stores_router)
api_router.include_router(products_router)
api_router.include_router(categories_router)
api_router.include_router(public_router)
api_router.include_router(billing_router)
api_router.include_router(privacy_router)
api_router.include_router(support_router)
api_router.include_router(orders_router)
api_router.include_router(users_router)
