from typing import Optional
from pydantic import BaseModel

from app.enums.websocket import PayloadType
from app.schemas.message_schema import MessageCreate
from app.schemas.chat_schema import ChatRoomResponse


class WebsocketReceivePayload(BaseModel):
    type: PayloadType
    chat_id: str
    data: Optional[MessageCreate] = None


class ChatRoomNotificationPayload(BaseModel):
    type: str = "new_chat_room"
    chat_room: ChatRoomResponse
