from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.support.models import SellerAdminMessage, SellerAdminReply
from app.modules.stores.models import Store
from app.modules.users.models import User


class SupportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, message: SellerAdminMessage) -> SellerAdminMessage:
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_owned_store(self, store_id: UUID, owner_id: UUID) -> Store | None:
        stmt = select(Store).where(Store.id == store_id, Store.owner_id == owner_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def first_store_name(self, owner_id: UUID) -> str | None:
        stmt = select(Store.name).where(Store.owner_id == owner_id).order_by(Store.created_at).limit(1)
        return await self.session.scalar(stmt)

    async def list_recipients(self):
        stmt = (select(User, Store).outerjoin(Store, Store.owner_id == User.id)
                .order_by(User.created_at.desc(), Store.created_at))
        rows = (await self.session.execute(stmt)).all()
        grouped: dict[UUID, dict] = {}
        for user, store in rows:
            recipient = grouped.setdefault(user.id, {
                "owner_id": user.id, "full_name": user.full_name,
                "email": user.email, "stores": [],
            })
            if store is not None:
                recipient["stores"].append({"id": store.id, "name": store.name})
        return list(grouped.values())

    async def list_for_owner(self, owner_id: UUID) -> list[SellerAdminMessage]:
        stmt = (select(SellerAdminMessage).where(SellerAdminMessage.owner_id == owner_id)
                .order_by(SellerAdminMessage.created_at.desc()))
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_owned(self, message_id: UUID, owner_id: UUID) -> SellerAdminMessage | None:
        stmt = select(SellerAdminMessage).where(
            SellerAdminMessage.id == message_id, SellerAdminMessage.owner_id == owner_id
        )
        message = (await self.session.execute(stmt)).scalar_one_or_none()
        return message

    async def list_for_admin(self) -> list[tuple[SellerAdminMessage, User]]:
        stmt = (select(SellerAdminMessage, User)
                .join(User, User.id == SellerAdminMessage.owner_id)
                .order_by(
                    (SellerAdminMessage.category == "catalog_request").desc(),
                    (SellerAdminMessage.status == "new").desc(),
                    SellerAdminMessage.created_at.desc(),
                ))
        return list((await self.session.execute(stmt)).all())

    async def get(self, message_id: UUID) -> SellerAdminMessage | None:
        return await self.session.get(SellerAdminMessage, message_id)

    async def unread_count(self) -> int:
        roots = select(func.count()).select_from(SellerAdminMessage).where(
            SellerAdminMessage.sender_role == "seller", SellerAdminMessage.admin_read_at.is_(None)
        )
        replies = select(func.count()).select_from(SellerAdminReply).where(
            SellerAdminReply.sender_role == "seller", SellerAdminReply.admin_read_at.is_(None)
        )
        return int((await self.session.scalar(roots) or 0) + (await self.session.scalar(replies) or 0))

    async def list_replies(self, message_id: UUID) -> list[tuple[SellerAdminReply, User]]:
        stmt = (select(SellerAdminReply, User)
                .outerjoin(User, User.id == SellerAdminReply.sender_id)
                .where(SellerAdminReply.message_id == message_id)
                .order_by(SellerAdminReply.created_at))
        return list((await self.session.execute(stmt)).all())

    async def add_reply(self, reply: SellerAdminReply) -> SellerAdminReply:
        self.session.add(reply)
        await self.session.flush()
        await self.session.refresh(reply)
        return reply

    async def mark_thread_read(self, message: SellerAdminMessage, role: str) -> None:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        if role == "admin" and message.sender_role == "seller" and message.admin_read_at is None:
            message.admin_read_at = now
        if role == "seller" and message.sender_role == "admin" and message.seller_read_at is None:
            message.seller_read_at = now
        for reply, _user in await self.list_replies(message.id):
            if role == "admin" and reply.sender_role == "seller" and reply.admin_read_at is None:
                reply.admin_read_at = now
            if role == "seller" and reply.sender_role == "admin" and reply.seller_read_at is None:
                reply.seller_read_at = now

    async def commit(self) -> None:
        await self.session.commit()

