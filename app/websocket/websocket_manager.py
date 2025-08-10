import logging
import asyncio
from fastapi import WebSocket, WebSocketException

from app.models.message import MessageModel
from app.schemas.chat_schema import ChatRoomResponse

logger = logging.getLogger(__name__)


class WebsocketManager:
    def __init__(self):
        self.user_connections: dict[str, set[WebSocket]] = (
            {}
        )  # chat_id -> set of user_ids (presence)
        self._lock = asyncio.Lock()  # Ensure thread-safety

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        async with self._lock:
            self.user_connections.setdefault(user_id, set()).add(websocket)
        logger.info("User %s connected via websocket", user_id)

    async def disconnect(self, websocket: WebSocket, user_id: str):
        # remove websocket from user connections
        async with self._lock:
            conns = self.user_connections.get(user_id)
            if conns:
                conns.discard(websocket)
                if not self.user_connections[user_id]:
                    # drop user dict if no connections left
                    del self.user_connections[user_id]
        logger.info("User %s disconnected websocket", user_id)

    async def send_personal_message(self, message: MessageModel, recipient_id: str):
        """
        Send a personal message to a recipient's active connections.
        """
        data = message.model_dump(mode="json")
        async with self._lock:
            sockets = list(self.user_connections.get(recipient_id, set()))
        if not sockets:
            logger.warning("No active connections for user %s", recipient_id)
            return
        for ws in sockets:
            try:
                await ws.send_json({"type": "personal_message", "data": data})
            except WebSocketException as e:
                logger.error(
                    "Error sending personal message to %s: %s", recipient_id, e
                )

    async def broadcast_message(
        self, message: MessageModel, chat_participants: list[str], chat_id: str
    ):
        """
        Broadcast a message to all users registered in a given chat room.
        """
        data = message.model_dump(mode="json")
        async with self._lock:
            for user_id in chat_participants:
                for ws in self.user_connections.get(user_id, set()):
                    try:
                        await ws.send_json(
                            {"type": "group_message", "chat_id": chat_id, "data": data}
                        )
                    except WebSocketException as e:
                        logger.error("Error broadcasting to %s: %s", user_id, e)

    async def broadcast_new_chat_room(
        self, chat_room: ChatRoomResponse, participants: list[str]
    ):
        """
        Broadcast a new chat room creation to all participants.
        """
        data = {
            "type": "new_chat_room",
            "chat_room": {
                "chat_id": chat_room.chat_id,
                "chat_name": chat_room.chat_name,
                "last_updated": (
                    chat_room.last_updated.isoformat()
                    if chat_room.last_updated
                    else None
                ),
            },
        }

        async with self._lock:
            for user_id in participants:
                for ws in self.user_connections.get(user_id, set()):
                    try:
                        await ws.send_json(data)
                    except WebSocketException as e:
                        logger.error(
                            "Error broadcasting new chat room to %s: %s", user_id, e
                        )


manager = WebsocketManager()
