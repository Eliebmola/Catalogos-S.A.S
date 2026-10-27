from decimal import Decimal
from uuid import UUID

from app.core.exceptions import ResourceNotFoundException
from app.core.security import AuthenticatedUser
from app.modules.orders.models import StoreOrder
from app.modules.orders.repository import OrdersRepository


def order_read(order: StoreOrder) -> dict:
    items = [{
        "product_id": item.product_id, "product_name": item.product_name,
        "image_url": item.image_url, "quantity": item.quantity,
        "unit_price": item.unit_price, "line_total": item.line_total,
        "currency": item.currency,
    } for item in order.items]
    totals: dict[str, Decimal] = {}
    for item in order.items:
        totals[item.currency] = totals.get(item.currency, Decimal("0")) + item.line_total
    return {
        "id": order.id, "order_number": order.order_number,
        "store_name": order.store_name, "buyer_name": order.buyer_name,
        "buyer_phone": order.buyer_phone, "buyer_email": order.buyer_email,
        "requires_shipping": order.requires_shipping, "city": order.city,
        "neighborhood": order.neighborhood, "address": order.address,
        "status": order.status, "created_at": order.created_at,
        "items": items, "totals": totals,
    }


class OrdersService:
    def __init__(self, repository: OrdersRepository) -> None:
        self.repository = repository

    async def list_for_owner(self, user: AuthenticatedUser) -> list[dict]:
        return [order_read(order) for order in await self.repository.list_for_owner(user.id)]

    async def update_status(self, order_id: UUID, user: AuthenticatedUser, status: str) -> dict:
        order = await self.repository.get_for_owner(order_id, user.id)
        if order is None:
            raise ResourceNotFoundException("El pedido no existe.")
        order.status = status
        await self.repository.commit()
        return order_read(order)
