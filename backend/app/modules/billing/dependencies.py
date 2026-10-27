from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, Request

from app.core.config import Settings
from app.core.database import DbSession
from app.modules.billing.repository import BillingRepository
from app.modules.billing.service import BillingService


def current_local_date(request: Request):
    settings: Settings = request.app.state.settings
    return datetime.now(ZoneInfo(settings.app_timezone)).date()


def get_billing_service(session: DbSession, request: Request) -> BillingService:
    settings: Settings = request.app.state.settings
    return BillingService(session, BillingRepository(session), settings.billing_grace_days)


BillingServiceDep = Annotated[BillingService, Depends(get_billing_service)]
