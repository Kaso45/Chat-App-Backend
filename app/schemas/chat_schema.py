from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

from app.enums.chat import ChatType


class ChatCreate(BaseModel):
    chat_type: ChatType
    participants: list[str]  # User IDs


class PersonalChatCreate(ChatCreate):
    pass


class GroupChatCreate(ChatCreate):
    name: str
    admins: list[str] = []


class ChatRoomResponse(BaseModel):
    chat_id: str
    chat_name: Optional[str] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
