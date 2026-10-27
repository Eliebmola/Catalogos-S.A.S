from typing import Annotated

from fastapi import Depends

from app.core.database import DbSession
from app.modules.orders.repository import OrdersRepository
from app.modules.orders.service import OrdersService


def get_orders_service(session: DbSession) -> OrdersService:
    return OrdersService(OrdersRepository(session))


OrdersServiceDep = Annotated[OrdersService, Depends(get_orders_service)]
