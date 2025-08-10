import logging
from fastapi import APIRouter, Depends
from fastapi_pagination.cursor import CursorParams
from redis.asyncio import Redis

from app.dependencies import get_current_user, get_redis_client
from app.models.user import UserModel
from app.repositories.chat_repository import ChatRedisRepository, ChatRepository
from app.schemas.chat_schema import GroupChatCreate, PersonalChatCreate
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat")


def get_chat_repository():
    return ChatRepository()


def get_chat_cache(redis: Redis = Depends(get_redis_client)):
    return ChatRedisRepository(redis)


def get_chat_service(
    chat_repo: ChatRepository = Depends(get_chat_repository),
    chat_cache: ChatRedisRepository = Depends(get_chat_cache),
):
    return ChatService(chat_repo, chat_cache)


@router.post("/create/personal")
async def create_personal_chat(
    request_schema: PersonalChatCreate,
    current_user: UserModel = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    user_id = str(current_user.id)
    await chat_service.create_personal_chat(user_id=user_id, data=request_schema)
    return {"message": "Successfully create personal chat"}


@router.post("/create/group")
async def create_group_chat(
    request_schema: GroupChatCreate,
    current_user: UserModel = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    user_id = str(current_user.id)
    await chat_service.create_group_chat(user_id=user_id, data=request_schema)
    return {"message": "Successfully create group chat"}


@router.get("/me/view")
async def get_chat_list(
    chat_service: ChatService = Depends(get_chat_service),
    current_user: UserModel = Depends(get_current_user),
    redis: Redis = Depends(get_redis_client),
    params: CursorParams = Depends(),
):
    """Get user's chat rooms with pagination"""
    return await chat_service.get_user_chat_rooms(current_user, redis, params)
