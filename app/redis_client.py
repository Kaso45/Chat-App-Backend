"""Redis config"""

from redis.asyncio import Redis, ConnectionPool

from app.config.config import settings

# Create connection pool for better performance
redis_pool = ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    username=settings.REDIS_USERNAME,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
    max_connections=20,
    retry_on_timeout=True,
    socket_keepalive=True,
)

r = Redis(connection_pool=redis_pool)


def redis_chat_messages_key(chat_id: str) -> str:
    """
    Redis key for chat room messages
    """
    return f"chat_messages:{chat_id}:messages"


def redis_message_data_key(message_id: str) -> str:
    """
    Redis key for message data
    """
    return f"message:{message_id}:data"


def redis_user_chat_rooms_key(user_id: str) -> str:
    """
    Redis key for user's chat rooms
    """
    return f"user_chats:{user_id}:chats"


def redis_chat_data_key(chat_id: str) -> str:
    """
    Redis key for chat room data
    """
    return f"chat:{chat_id}:data"


def redis_user_chat_rooms_complete_key(user_id: str) -> str:
    """
    Redis key indicating the user's chat rooms cache is complete/backfilled
    """
    return f"user_chats:{user_id}:complete"


async def close_redis_connections():
    """
    Close Redis connections on application shutdown
    """
    await r.close()
