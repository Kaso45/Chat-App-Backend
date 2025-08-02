import logging
from fastapi import APIRouter, Depends

from app.repositories.chat_repository import ChatRepository
from app.schemas.chat_schema import GroupChatCreate, PersonalChatCreate
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat")


def get_chat_repository():
    return ChatRepository()


def get_chat_service(
    chat_repo: ChatRepository = Depends(get_chat_repository),
):
    return ChatService(chat_repo)


@router.post("/create/personal")
async def create_personal_chat(
    request_schema: PersonalChatCreate,
    chat_service: ChatService = Depends(get_chat_service),
):
    await chat_service.create_personal_chat(request_schema)
    return {"message: Successfully create personal chat"}


@router.post("/create/group")
async def create_group_chat(
    request_schema: GroupChatCreate,
    chat_service: ChatService = Depends(get_chat_service),
):
    await chat_service.create_group_chat(request_schema)
    return {"message: Successfully create group chat"}
