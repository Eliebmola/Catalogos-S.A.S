from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.orders.models import StoreOrder


class OrdersRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_owner(self, owner_id: UUID) -> list[StoreOrder]:
        stmt = (select(StoreOrder).where(StoreOrder.owner_id == owner_id)
                .options(selectinload(StoreOrder.items))
                .order_by(StoreOrder.created_at.desc()))
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_owner(self, order_id: UUID, owner_id: UUID) -> StoreOrder | None:
        stmt = (select(StoreOrder).where(StoreOrder.id == order_id, StoreOrder.owner_id == owner_id)
                .options(selectinload(StoreOrder.items)))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def add(self, order: StoreOrder) -> StoreOrder:
        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order)
        return order

    async def commit(self) -> None:
        await self.session.commit()
