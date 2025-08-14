"""Pydantic schemas for chat creation and list responses."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

from app.enums.chat import ChatType


class ChatCreate(BaseModel):
    """Base schema for chat creation (personal or group)."""

    chat_type: ChatType
    participants: list[str]  # User IDs


class PersonalChatCreate(ChatCreate):
    """Schema for creating a personal chat between exactly two users."""


class GroupChatCreate(ChatCreate):
    """Schema for creating a group chat with a name and admins."""

    name: str
    admins: list[str] = []


class ChatRoomResponse(BaseModel):
    """Lightweight chat room representation for lists and notifications."""

    chat_id: str
    chat_name: Optional[str] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
