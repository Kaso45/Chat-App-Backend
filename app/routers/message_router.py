"""HTTP routes for message history retrieval with DI wiring."""

from fastapi import APIRouter, Depends
from fastapi_pagination.cursor import CursorParams
from redis.asyncio import Redis

from app.dependencies import get_current_user, get_redis_client
from app.models.user import UserModel
from app.repositories.message_repository import (
    MessageRedisRepository,
    MessageRepository,
)
from app.repositories.chat_repository import ChatRepository
from app.services.message_service import MessageService


router = APIRouter(prefix="/api/message", tags=["Messages"])


def get_message_repository():
    """Dependency provider for `MessageRepository`."""
    return MessageRepository()


def get_message_cache(redis: Redis = Depends(get_redis_client)):
    """Dependency provider for `MessageRedisRepository`."""
    return MessageRedisRepository(redis)


def get_message_service(
    message_repo: MessageRepository = Depends(get_message_repository),
    message_cache: MessageRedisRepository = Depends(get_message_cache),
):
    """Construct a `MessageService` with repositories and cache dependencies."""

    return MessageService(ChatRepository(), message_repo, message_cache)


@router.get("/history")
async def get_message_history(
    chat_id: str,
    params: CursorParams = Depends(),
    message_service: MessageService = Depends(get_message_service),
    current_user: UserModel = Depends(get_current_user),
    redis: Redis = Depends(get_redis_client),
):
    """Get paginated message history for a chat the user participates in."""
    user_id = str(current_user.id)
    return await message_service.get_old_messages(user_id, chat_id, redis, params)
