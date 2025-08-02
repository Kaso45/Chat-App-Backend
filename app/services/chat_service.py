"""Module handles chat service layer"""

import logging
from fastapi import HTTPException, status

from app.models.chat import ChatModel
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat_schema import GroupChatCreate, PersonalChatCreate

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, chat_repo: ChatRepository):
        self.chat_repo = chat_repo

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
