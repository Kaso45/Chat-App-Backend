from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from app.custom_classes.pyobjectid import PyObjectId
from app.enums.chat import ChatType
from app.schemas.chat_schema import ChatCreate


class ChatModel(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    chat_type: ChatType
    participants: list[str]  # User IDs
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    admins: list[str] = []  # For group chat

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "created_at": "2025-07-11T16:44:00Z",
                "last_message_id": "...",
                "last_message_at": "2025-07-11T16:44:00Z",
            }
        },
    )

    @classmethod
    def from_create(cls, chat: ChatCreate):
        return cls(**chat.model_dump())
