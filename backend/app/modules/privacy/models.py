from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PrivacyConsent(Base):
    __tablename__ = "privacy_consents"

    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    policy_version: Mapped[str] = mapped_column(String(80), primary_key=True)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
