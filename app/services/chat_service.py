"""Module handles chat service layer"""

import logging
import json

from fastapi import HTTPException, status

from app.models.chat import ChatModel
from app.redis_client import redis_chat_key
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import MessageRepository
from app.schemas.chat_schema import GroupChatCreate, PersonalChatCreate
from app.schemas.message_schema import MessageCreate
from app.websocket.websocket_manager import manager
from app.enums.message import MessageStatus
from app.models.message import MessageModel
from app.exceptions.chat_exception import ChatNotFoundError
from app.enums.chat import ChatType
from app.redis_client import r

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, chat_repo: ChatRepository, message_repo: MessageRepository):
        self.chat_repo = chat_repo
        self.message_repo = message_repo

    async def handle_new_message(
        self, message: MessageCreate, chat_id: str, sender_id: str
    ):
        # Validate and get chat room
        try:
            chat = await self.chat_repo.get_by_id(chat_id)
            chat_dict = chat.model_dump()
        except ChatNotFoundError as e:
            logger.error("Cannot get chat room: %s", str(e))

        if str(sender_id) not in chat_dict["participants"]:
            logger.warning("Sender is not part of the chat conversation")
            return

        # Save message
        try:
            # Save message to database
            message_doc = MessageModel.from_create(message, sender_id)
            result_id = await self.message_repo.create(message_doc)

            # Save message to redis
            await self.message_repo.cache_messages(chat_id=chat_id, message=message_doc)

            try:
                participants = chat_dict["participants"]
                if chat_dict["chat_type"] == ChatType.PERSONAL:
                    # send personal message
                    recipient_id = next(
                        (rec_id for rec_id in participants if rec_id != sender_id), None
                    )

                    print("User connections:", manager.user_connections)
                    await manager.send_personal_message(message_doc, recipient_id)
                elif chat_dict["chat_type"] == ChatType.GROUP:
                    # broadcast to chat participants for group chat
                    await manager.broadcast_message(message_doc, participants, chat_id)

                # Change message status
                await self.message_repo.update(
                    result_id, {"message_status": MessageStatus.SENT}
                )
            except Exception as e:
                logger.warning("Failed to send message: %s", str(e))
                await self.message_repo.update(
                    result_id, {"message_status": MessageStatus.FAILED}
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data input"
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to handle message: {str(e)}",
            ) from e

    async def create_personal_chat(
        self,
        data: PersonalChatCreate,
    ):
        try:
            chat_doc = ChatModel.from_create(data)
            await self.chat_repo.create(chat_doc)
            return {"message": "Chat room sucessfully created"}
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data input"
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create personal chat: {str(e)}",
            ) from e

    async def create_group_chat(self, data: GroupChatCreate):
        try:
            chat_doc = ChatModel.from_create(data)
            await self.chat_repo.create(chat_doc)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data input"
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create group chat: {str(e)}",
            ) from e

    async def get_cache_messages(self, chat_id: str, limit: int = 50):
        key = redis_chat_key(chat_id)
        messages = await r.lrange(key, 0, limit - 1)
        return [json.loads(m) for m in reversed(messages)]
