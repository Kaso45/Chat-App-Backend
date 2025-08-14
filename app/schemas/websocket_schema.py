"""Pydantic schemas for websocket message payloads."""

from typing import Optional
from pydantic import BaseModel

from app.enums.websocket import PayloadType
from app.schemas.message_schema import MessageCreate
from app.schemas.chat_schema import ChatRoomResponse


class WebsocketReceivePayload(BaseModel):
    """Incoming websocket payload for client to server messages."""

    type: PayloadType
    chat_id: str
    data: Optional[MessageCreate] = None


class ChatRoomNotificationPayload(BaseModel):
    """Server to client payload notifying about new chat room creation."""

    type: str = "new_chat_room"
    chat_room: ChatRoomResponse
