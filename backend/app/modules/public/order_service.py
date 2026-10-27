from datetime import date, datetime, timezone
from decimal import Decimal
from urllib.parse import quote
from uuid import uuid4

from app.core.exceptions import BusinessRuleViolationException, ResourceNotFoundException
from app.modules.orders.models import StoreOrder, StoreOrderItem
from app.modules.public.repository import PublicCatalogRepository
from app.modules.public.schemas import PublicOrderCreate, PublicOrderReceipt


class PublicOrderService:
    def __init__(self, repository: PublicCatalogRepository, today: date, grace_days: int) -> None:
        self.repository = repository
        self.today = today
        self.grace_days = grace_days

    async def submit(self, slug: str, data: PublicOrderCreate) -> PublicOrderReceipt:
        store = await self.repository.get_published_by_slug(slug, self.today, self.grace_days)
        if store is None:
            raise ResourceNotFoundException("Catálogo no encontrado.")
        products = {product.id: product for product in store.products if product.is_active}
        lines = []
        totals: dict[str, Decimal] = {}
        for requested in data.items:
            product = products.get(requested.product_id)
            if product is None:
                raise BusinessRuleViolationException(
                    "Uno de los productos ya no está disponible. Actualiza el catálogo e inténtalo de nuevo."
                )
            line_total = product.price * requested.quantity
            totals[product.currency] = totals.get(product.currency, Decimal("0")) + line_total
            lines.append({
                "product_id": product.id,
                "name": product.name,
                "image_url": product.image_url,
                "quantity": requested.quantity,
                "unit_price": product.price,
                "line_total": line_total,
                "currency": product.currency,
            })

        order_number = uuid4().hex[:10].upper()
        order = StoreOrder(
            order_number=order_number, store_id=store.id, owner_id=store.owner_id,
            store_name=store.name, buyer_name=data.buyer_name, buyer_phone=data.buyer_phone,
            buyer_email=str(data.buyer_email) if data.buyer_email else None,
            requires_shipping=data.requires_shipping,
            city=data.city if data.requires_shipping else None,
            neighborhood=data.neighborhood if data.requires_shipping else None,
            address=data.address if data.requires_shipping else None, status="new",
            items=[StoreOrderItem(
                product_id=line["product_id"], product_name=line["name"],
                image_url=line["image_url"], quantity=line["quantity"],
                unit_price=line["unit_price"], line_total=line["line_total"], currency=line["currency"],
            ) for line in lines],
        )
        await self.repository.create_order(order)
        message = self._message(order_number, store.name, data, lines, totals)
        whatsapp_url = None
        if store.whatsapp_number and store.whatsapp_orders_opt_in:
            destination = "".join(character for character in store.whatsapp_number if character.isdigit())
            whatsapp_url = f"https://wa.me/{destination}?text={quote(message, safe='')}"
        return PublicOrderReceipt(
            id=order_number,
            created_at=order.created_at or datetime.now(timezone.utc),
            catalog_name=store.name,
            buyer_name=data.buyer_name,
            buyer_phone=data.buyer_phone,
            buyer_email=str(data.buyer_email) if data.buyer_email else None,
            requires_shipping=data.requires_shipping,
            city=data.city if data.requires_shipping else None,
            neighborhood=data.neighborhood if data.requires_shipping else None,
            address=data.address if data.requires_shipping else None,
            items=lines,
            totals=totals,
            saved_for_seller=True,
            whatsapp_url=whatsapp_url,
        )

    @staticmethod
    def _message(order_id, store_name, buyer, lines, totals) -> str:
        details = [f"Nuevo pedido {order_id} · {store_name}", f"Comprador: {buyer.buyer_name}",
                   f"Contacto: {buyer.buyer_phone}"]
        if buyer.buyer_email:
            details.append(f"Correo: {buyer.buyer_email}")
        if buyer.requires_shipping:
            details.extend(["Envío solicitado:", f"Ciudad: {buyer.city}",
                            f"Barrio: {buyer.neighborhood}", f"Dirección: {buyer.address}"])
        else:
            details.append("Entrega: por coordinar")
        details.append("Productos:")
        details.extend(
            f"- {line['name']} x{line['quantity']} = {line['line_total']} {line['currency']}"
            for line in lines
        )
        details.append("Total productos: " + " / ".join(
            f"{amount} {currency}" for currency, amount in totals.items()
        ))
        details.append("El costo del envío se acuerda por separado.")
        return "\n".join(details)

