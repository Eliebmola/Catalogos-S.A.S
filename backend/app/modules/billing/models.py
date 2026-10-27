from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Subscription(TimestampMixin, Base):
    """Suscripción manual por propietario. El pago nunca se procesa en esta aplicación."""

    __tablename__ = "subscriptions"

    owner_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    paid_through: Mapped[date | None] = mapped_column(Date)
    trial_until: Mapped[date | None] = mapped_column(Date)
    extra_catalogs: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    whatsapp_number: Mapped[str | None] = mapped_column(String(16))
    # None = aplicar vencimiento automático; True = bloquear manualmente; False = excepción activa.
    access_override: Mapped[bool | None] = mapped_column(Boolean)
    legacy_grandfathered: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())


class BillingNotification(TimestampMixin, Base):
    """Registro idempotente de recordatorios por periodo, tipo y canal."""

    __tablename__ = "billing_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("owner_id", "period_end", "kind", "channel", name="uq_billing_notification_period"),
        Index("ix_billing_notifications_status", "status", "created_at"),
        CheckConstraint("kind in ('due', 'suspended')", name="billing_notification_kind"),
        CheckConstraint("channel in ('email', 'whatsapp')", name="billing_notification_channel"),
        CheckConstraint("status in ('sent', 'failed', 'skipped')", name="billing_notification_status"),
    )


class BillingPayment(Base):
    """Auditoría de cada pago registrado manualmente por un administrador."""

    __tablename__ = "billing_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recorded_by_email: Mapped[str] = mapped_column(String(320), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    paid_through: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (Index("ix_billing_payments_owner_paid_at", "owner_id", "paid_at"),)
