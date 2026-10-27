from uuid import UUID

from app.core.exceptions import ResourceNotFoundException
from app.core.security import AuthenticatedUser
from app.modules.support.models import SellerAdminMessage
from app.modules.support.models import SellerAdminReply
from app.modules.support.repository import SupportRepository


class SupportService:
    def __init__(self, repository: SupportRepository) -> None:
        self.repository = repository

    async def submit(self, owner: AuthenticatedUser, category: str, subject: str,
                     body: str, store_id: UUID | None = None) -> SellerAdminMessage:
        store = await self.repository.get_owned_store(store_id, owner.id) if store_id else None
        if store_id and store is None:
            raise ResourceNotFoundException("El negocio seleccionado no pertenece a tu cuenta.")
        user = await self.repository.get_user(owner.id)
        message = SellerAdminMessage(
            owner_id=owner.id, store_id=store.id if store else None,
            business_name=store.name if store else await self.repository.first_store_name(owner.id),
            sender_name=owner.full_name or (user.full_name if user else None) or "Vendedor",
            category=category, subject=subject, body=body, status="new", sender_role="seller",
        )
        await self.repository.add(message)
        await self.repository.commit()
        return message

    @staticmethod
    def _reply_data(reply: SellerAdminReply, user) -> dict:
        return {"id": reply.id, "message_id": reply.message_id,
                "sender_role": reply.sender_role,
                "sender_name": reply.sender_name or ("Administrador" if reply.sender_role == "admin" else ((user.full_name if user else None) or "Vendedor")),
                "body": reply.body, "created_at": reply.created_at}

    async def _thread_data(self, message: SellerAdminMessage, user=None) -> dict:
        replies = await self.repository.list_replies(message.id)
        return {
            "id": message.id, "owner_id": message.owner_id,
            "seller_name": (user.full_name if user else None) or (message.sender_name if message.sender_role == "seller" else None),
            "seller_email": user.email if user else None,
            "business_name": message.business_name or await self.repository.first_store_name(message.owner_id),
            "sender_name": message.sender_name,
            "category": message.category, "subject": message.subject,
            "body": message.body, "status": message.status,
            "sender_role": message.sender_role,
            "admin_read_at": message.admin_read_at,
            "created_at": message.created_at, "updated_at": message.updated_at,
            "replies": [self._reply_data(reply, reply_user) for reply, reply_user in replies],
        }

    async def list_for_owner(self, owner: AuthenticatedUser) -> list[dict]:
        messages = await self.repository.list_for_owner(owner.id)
        user = await self.repository.get_user(owner.id)
        result = []
        for message in messages:
            await self.repository.mark_thread_read(message, "seller")
            result.append(await self._thread_data(message, user))
        if messages:
            await self.repository.commit()
        return result

    async def list_for_admin(self):
        rows = await self.repository.list_for_admin()
        result = []
        for message, user in rows:
            await self.repository.mark_thread_read(message, "admin")
            thread = await self._thread_data(message, user)
            thread["seller_name"] = user.full_name or message.sender_name or "Vendedor"
            thread["seller_email"] = user.email
            result.append(thread)
        if rows:
            await self.repository.commit()
        return result

    async def unread_count(self) -> int:
        return await self.repository.unread_count()

    async def create_for_seller(self, admin: AuthenticatedUser, owner_id: UUID,
                                category: str, subject: str, body: str,
                                store_id: UUID | None = None) -> dict:
        user = await self.repository.get_user(owner_id)
        if user is None:
            raise ResourceNotFoundException("No se encontró la cuenta del vendedor.")
        store = await self.repository.get_owned_store(store_id, owner_id) if store_id else None
        if store_id and store is None:
            raise ResourceNotFoundException("El negocio seleccionado no pertenece a esa cuenta.")
        admin_user = await self.repository.get_user(admin.id)
        message = SellerAdminMessage(
            owner_id=owner_id, store_id=store.id if store else None,
            business_name=store.name if store else await self.repository.first_store_name(owner_id),
            sender_name=admin.full_name or (admin_user.full_name if admin_user else None) or "Administrador",
            category=category, subject=subject, body=body,
            status="in_progress", sender_role="admin",
        )
        await self.repository.add(message)
        await self.repository.commit()
        return await self._thread_data(message, user)

    async def reply(self, message_id: UUID, sender: AuthenticatedUser, role: str,
                    body: str) -> dict:
        message = (await self.repository.get(message_id) if role == "admin"
                   else await self.repository.get_owned(message_id, sender.id))
        if message is None:
            raise ResourceNotFoundException("La conversación no existe.")
        reply = SellerAdminReply(
            message_id=message.id, sender_id=sender.id, sender_role=role,
            sender_name=sender.full_name or ("Administrador" if role == "admin" else "Vendedor"),
            body=body,
        )
        await self.repository.add_reply(reply)
        message.status = "in_progress"
        await self.repository.commit()
        user = await self.repository.get_user(sender.id)
        return self._reply_data(reply, user)

    async def update_status(self, message_id: UUID, status: str) -> dict:
        message = await self.repository.get(message_id)
        if message is None:
            raise ResourceNotFoundException("El mensaje no existe.")
        message.status = status
        await self.repository.mark_thread_read(message, "admin")
        await self.repository.commit()
        user = await self.repository.get_user(message.owner_id)
        return await self._thread_data(message, user)
