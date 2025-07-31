from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from app.custom_classes.pyobjectid import PyObjectId
from app.enums.message import MessageType, MessageStatus
from app.schemas.message_schema import MessageCreate


class MessageModel(BaseModel):
    """
    Pydantic model for message
    """

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    chat_id: Optional[PyObjectId] = None
    sender_id: Optional[PyObjectId] = None
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_edited: bool = Field(default=False)
    message_type: MessageType = Field(default=MessageType.TEXT)
    message_status: MessageStatus = Field(default=MessageStatus.SENDING)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "chat_id": "687330d93db7fd55e4dfbd98",
                "sender_id": "687330d93db7fd55e4dfbd99",
                "content": "hello",
            }
        },
    )

    @classmethod
    def from_create(cls, message: MessageCreate, sender_id: str):
        data = message.model_dump()
        data.pop("sender_id", None)
        return cls(**data, sender_id=sender_id)
