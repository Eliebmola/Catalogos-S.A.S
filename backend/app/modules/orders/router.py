from uuid import UUID

from fastapi import APIRouter

from app.core.security import CurrentUser
from app.modules.orders.dependencies import OrdersServiceDep
from app.modules.orders.schemas import OrderStatusUpdate, SellerOrderRead

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[SellerOrderRead], summary="Listar pedidos recibidos por mis catálogos")
async def list_my_orders(user: CurrentUser, service: OrdersServiceDep):
    return await service.list_for_owner(user)


@router.patch("/{order_id}", response_model=SellerOrderRead, summary="Actualizar estado de un pedido")
async def update_order(order_id: UUID, payload: OrderStatusUpdate,
                       user: CurrentUser, service: OrdersServiceDep):
    return await service.update_status(order_id, user, payload.status)
