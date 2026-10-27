from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class SellerAdminMessage(UUIDPrimaryKeyMixin, Base):
    """Internal seller-to-administrator support request."""

    __tablename__ = "seller_admin_messages"

    owner_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    store_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("stores.id", ondelete="SET NULL")
    )
    business_name: Mapped[str | None] = mapped_column(String(120))
    sender_name: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="new")
    sender_role: Mapped[str] = mapped_column(String(16), nullable=False, server_default="seller")
    admin_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seller_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "category in ('catalog_request', 'complaint', 'technical_issue', 'other')",
            name="seller_message_category",
        ),
        CheckConstraint("status in ('new', 'in_progress', 'resolved')", name="seller_message_status"),
        CheckConstraint("sender_role in ('seller', 'admin')", name="seller_message_sender_role"),
        Index("ix_seller_admin_messages_status_created", "status", "created_at"),
        Index("ix_seller_admin_messages_owner_created", "owner_id", "created_at"),
    )


class SellerAdminReply(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "seller_admin_replies"

    message_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("seller_admin_messages.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[UUID] = mapped_column(
        Uuid, nullable=False
    )
    sender_role: Mapped[str] = mapped_column(String(16), nullable=False)
    sender_name: Mapped[str | None] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    admin_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seller_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("sender_role in ('seller', 'admin')", name="seller_reply_sender_role"),
        Index("ix_seller_admin_replies_thread_created", "message_id", "created_at"),
    )
