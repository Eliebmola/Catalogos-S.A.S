from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.models import BillingNotification, BillingPayment, Subscription
from app.modules.stores.models import Store
from app.modules.users.models import User


class BillingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_accounts(self):
        stmt = (
            select(User, Subscription, func.count(Store.id).label("store_count"))
            .outerjoin(Subscription, Subscription.owner_id == User.id)
            .outerjoin(Store, Store.owner_id == User.id)
            .group_by(User.id, Subscription.owner_id)
            .order_by(User.created_at.desc())
        )
        return (await self.session.execute(stmt)).all()

    async def get_subscription(self, owner_id: UUID) -> Subscription | None:
        return await self.session.get(Subscription, owner_id)

    async def ensure_subscription(self, owner_id: UUID) -> Subscription:
        subscription = await self.get_subscription(owner_id)
        if subscription is None:
            subscription = Subscription(owner_id=owner_id)
            self.session.add(subscription)
            await self.session.flush()
        return subscription

    async def count_stores(self, owner_id: UUID) -> int:
        return int(await self.session.scalar(select(func.count(Store.id)).where(Store.owner_id == owner_id)) or 0)

    async def due_accounts(self, today: date):
        stmt = (
            select(User, Subscription)
            .join(Subscription, Subscription.owner_id == User.id)
            .where(Subscription.paid_through.is_not(None), Subscription.access_override.is_(None))
            .where(Subscription.paid_through <= today)
        )
        return (await self.session.execute(stmt)).all()

    async def get_notification(
        self, owner_id: UUID, period_end: date, kind: str, channel: str
    ) -> BillingNotification | None:
        stmt = select(BillingNotification).where(
            BillingNotification.owner_id == owner_id,
            BillingNotification.period_end == period_end,
            BillingNotification.kind == kind,
            BillingNotification.channel == channel,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def add_payment(self, payment: BillingPayment) -> None:
        self.session.add(payment)
        await self.session.flush()
