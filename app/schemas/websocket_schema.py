from typing import Optional
from pydantic import BaseModel

from app.enums.websocket import PayloadType
from app.schemas.message_schema import MessageCreate


class WebsocketReceivePayload(BaseModel):
    type: PayloadType
    chat_id: str
    data: Optional[MessageCreate] = None
