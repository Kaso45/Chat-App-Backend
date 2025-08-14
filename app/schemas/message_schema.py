"""Pydantic schemas for message creation, updates, and responses."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.enums.message import MessageStatus, MessageType


class MessageCreate(BaseModel):
    """Schema for creating a new message."""

    content: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "hello",
            }
        }
    )


class MessageUpdate(BaseModel):
    """Schema for updating an existing message's content."""

    content: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"content": "good morning"}}
    )


class MessageResponse(BaseModel):
    """Response schema for returning message data to clients."""

    id: str
    chat_id: str
    sender_id: str
    content: str
    timestamp: datetime
    message_type: MessageType = MessageType.TEXT
    message_status: MessageStatus = MessageStatus.SENDING
    is_edited: bool = False
