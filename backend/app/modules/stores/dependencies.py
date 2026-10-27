from typing import Annotated

from fastapi import Depends, Request
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.database import DbSession
from app.core.config import Settings
from app.core.storage import SupabaseStorage
from app.modules.stores.repository import StoreRepository
from app.modules.stores.service import StoreService
from app.modules.users.repository import UserRepository
from app.modules.billing.repository import BillingRepository


def get_store_service(session: DbSession, request: Request) -> StoreService:
    settings: Settings = request.app.state.settings
    today = datetime.now(ZoneInfo(settings.app_timezone)).date()
    return StoreService(session, StoreRepository(session), UserRepository(session),
                        BillingRepository(session), today, settings.billing_grace_days,
                        SupabaseStorage(settings) if settings.supabase_service_role_key else None,
                        settings.billing_trial_days)


StoreServiceDep = Annotated[StoreService, Depends(get_store_service)]
