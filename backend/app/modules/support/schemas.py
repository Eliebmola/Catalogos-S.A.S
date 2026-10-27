from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MessageCategory = Literal["catalog_request", "complaint", "technical_issue", "other"]
MessageStatus = Literal["new", "in_progress", "resolved"]


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category: MessageCategory
    subject: Annotated[str, Field(min_length=3, max_length=160)]
    body: Annotated[str, Field(min_length=10, max_length=5000)]
    store_id: UUID | None = None


class MessageStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: MessageStatus


class ReplyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    body: Annotated[str, Field(min_length=1, max_length=5000)]


class AdminMessageCreate(MessageCreate):
    owner_id: UUID


class ReplyRead(BaseModel):
    id: UUID
    message_id: UUID
    sender_role: Literal["seller", "admin"]
    sender_name: str
    body: str
    created_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    seller_name: str | None = None
    seller_email: str | None = None
    business_name: str | None = None
    sender_name: str | None = None
    category: MessageCategory
    subject: str
    body: str
    status: MessageStatus
    sender_role: Literal["seller", "admin"] = "seller"
    replies: list[ReplyRead] = Field(default_factory=list)
    admin_read_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UnreadCount(BaseModel):
    count: int


class StoreChoice(BaseModel):
    id: UUID
    name: str


class MessageRecipient(BaseModel):
    owner_id: UUID
    full_name: str | None
    email: str | None
    stores: list[StoreChoice]
