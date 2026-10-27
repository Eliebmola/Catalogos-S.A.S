import calendar
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import BillingPayment, Subscription
from app.modules.billing.repository import BillingRepository
from app.modules.stores.models import Store
from sqlalchemy import update


def subscription_status(
    subscription: Subscription | None, today: date, grace_days: int = 2
) -> str:
    if subscription is None:
        # Conserva acceso a las cuentas existentes hasta que el administrador las registre.
        return "legacy"
    if subscription.access_override is True:
        return "blocked"
    if subscription.access_override is False:
        return "manual_access"
    if subscription.trial_until is not None:
        if today <= subscription.trial_until:
            return "trial"
        if today <= subscription.trial_until + timedelta(days=grace_days):
            return "grace"
        return "suspended"
    if subscription.paid_through is None:
        return "pending_payment"
    if today < subscription.paid_through:
        return "active"
    if today <= subscription.paid_through + timedelta(days=grace_days):
        return "grace"
    return "suspended"


def add_calendar_month(day: date) -> date:
    month_index = day.month  # next month's 1-based index
    year = day.year + (1 if month_index == 12 else 0)
    month = 1 if month_index == 12 else month_index + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


class BillingService:
    def __init__(self, session: AsyncSession, repository: BillingRepository, grace_days: int) -> None:
        self.session = session
        self.repository = repository
        self.grace_days = grace_days

    async def list_accounts(self, today: date) -> list[dict]:
        rows = await self.repository.list_accounts()
        result = []
        for user, subscription, store_count in rows:
            status = subscription_status(subscription, today, self.grace_days)
            if subscription and subscription.legacy_grandfathered:
                status = "legacy"
            result.append({
                "owner_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "catalog_count": store_count,
                "whatsapp_number": subscription.whatsapp_number if subscription else None,
                "paid_through": subscription.paid_through if subscription else None,
                "trial_until": subscription.trial_until if subscription else None,
                "extra_catalogs": subscription.extra_catalogs if subscription else 0,
                "status": status,
                "access_override": subscription.access_override if subscription else None,
                "legacy_grandfathered": subscription.legacy_grandfathered if subscription else True,
            })
        return result

    async def update_whatsapp(self, owner_id: UUID, whatsapp_number: str | None) -> Subscription:
        subscription = await self.repository.ensure_subscription(owner_id)
        subscription.whatsapp_number = whatsapp_number
        await self.session.commit()
        return subscription

    async def record_payment(self, owner_id: UUID, today: date, recorded_by_email: str) -> Subscription:
        subscription = await self.repository.ensure_subscription(owner_id)
        renewal_base = subscription.paid_through if subscription.paid_through and today <= subscription.paid_through else today
        subscription.paid_through = add_calendar_month(renewal_base)
        subscription.trial_until = None
        subscription.access_override = None
        subscription.legacy_grandfathered = False
        await self.repository.add_payment(BillingPayment(
            owner_id=owner_id,
            recorded_by_email=recorded_by_email,
            paid_through=subscription.paid_through,
        ))
        await self.session.commit()
        return subscription

    async def set_extra_catalogs(self, owner_id: UUID, count: int) -> Subscription:
        subscription = await self.repository.ensure_subscription(owner_id)
        subscription.extra_catalogs = count
        await self.session.commit()
        return subscription

    async def set_access_override(self, owner_id: UUID, blocked: bool | None) -> Subscription:
        subscription = await self.repository.ensure_subscription(owner_id)
        subscription.access_override = blocked
        if blocked is True:
            # El dueño verá sus catálogos como borradores; no podrán re-publicarse hasta desbloquearse.
            await self.session.execute(
                update(Store).where(Store.owner_id == owner_id).values(is_published=False)
            )
        await self.session.commit()
        return subscription


