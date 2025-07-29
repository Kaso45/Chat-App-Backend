import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from app.dependencies import get_current_user_ws
from app.schemas.websocket_schema import WebsocketReceivePayload
from app.websocket.websocket_manager import manager
from app.services.chat_service import ChatService
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import MessageRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws")


def get_chat_repository() -> ChatRepository:
    return ChatRepository()


def get_message_repository() -> MessageRepository:
    return MessageRepository()


def get_chat_service(
    chat_repo: ChatRepository = Depends(get_chat_repository),
    message_repo: MessageRepository = Depends(get_message_repository),
) -> ChatService:
    return ChatService(chat_repo, message_repo)


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str = Depends(get_current_user_ws),
    chat_service: ChatService = Depends(get_chat_service),
):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Listen for incoming message
            payload = await websocket.receive_json()
            payload_obj = WebsocketReceivePayload(**payload)
            event_type = payload_obj.type

            if event_type == "load_chat":
                chat_id = payload_obj.chat_id
                history = await chat_service.get_cache_messages(chat_id)
                await websocket.send_json(history)
            elif event_type == "new_message":
                message_data = payload_obj.data
                chat_id = payload_obj.chat_id
                await chat_service.handle_new_message(
                    message=message_data, chat_id=chat_id, sender_id=user_id
                )
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error("Websocket error: %s", str(e))
        await manager.disconnect(websocket, user_id)
        raise
