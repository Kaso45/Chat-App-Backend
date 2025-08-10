from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.enums.message import MessageStatus, MessageType


class MessageCreate(BaseModel):
    sender_id: str
    content: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sender_id": "68805dc7bf5491c521b0d31a",
                "content": "hello",
            }
        }
    )


class MessageUpdate(BaseModel):
    content: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"content": "good morning"}}
    )


class MessageResponse(BaseModel):
    id: str
    chat_id: str
    sender_id: str
    content: str
    timestamp: datetime
    message_type: MessageType = MessageType.TEXT
    message_status: MessageStatus = MessageStatus.SENDING
    is_edited: bool = False
