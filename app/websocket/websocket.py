"""WebSocket router providing real-time chat endpoint."""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis

from app.dependencies import get_current_user_ws
from app.schemas.websocket_schema import WebsocketReceivePayload
from app.services.message_service import MessageService
from app.websocket.websocket_manager import manager
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import (
    MessageRedisRepository,
    MessageRepository,
)
from app.dependencies import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws")


def get_chat_repository() -> ChatRepository:
    """Dependency provider for `ChatRepository`."""
    return ChatRepository()


def get_message_repository() -> MessageRepository:
    """Dependency provider for `MessageRepository`."""
    return MessageRepository()


def get_message_cache(redis: Redis = Depends(get_redis_client)):
    """Dependency provider for `MessageRedisRepository`."""
    return MessageRedisRepository(redis)


def get_message_service(
    chat_repo: ChatRepository = Depends(get_chat_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
    message_cache: MessageRedisRepository = Depends(get_message_cache),
):
    """Construct a `MessageService` for websocket endpoint dependencies."""
    return MessageService(chat_repo, message_repo, message_cache)


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str = Depends(get_current_user_ws),
    message_service: MessageService = Depends(get_message_service),
    redis: Redis = Depends(get_redis_client),
):
    """WebSocket endpoint handling chat events: load history and new messages."""
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Listen for incoming message
            payload = await websocket.receive_json()
            payload_obj = WebsocketReceivePayload(**payload)
            event_type = payload_obj.type

            if event_type == "load_chat":
                chat_id = payload_obj.chat_id
                # Initial load from Redis (or DB fallback) using injected client
                history = await message_service.get_cache_messages(chat_id, redis)
                await websocket.send_json(jsonable_encoder(history))
            elif event_type == "new_message":
                message_data = payload_obj.data
                chat_id = payload_obj.chat_id

                if message_data is None:
                    await websocket.send_json({"error": "Missing message data"})
                    return

                await message_service.handle_new_message(
                    message=message_data, chat_id=chat_id, sender_id=user_id
                )
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error("Websocket error: %s", str(e))
        await manager.disconnect(websocket, user_id)
        raise
