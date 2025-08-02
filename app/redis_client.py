"""Redis config"""

from redis.asyncio import Redis

from app.config.config import settings

r = Redis(
    host="redis-17220.c295.ap-southeast-1-1.ec2.redns.redis-cloud.com",
    port=17220,
    decode_responses=True,
    username="default",
    password=settings.REDIS_PASSWORD,
)


def redis_chat_key(chat_id: str) -> str:
    """
    Redis key for chat room
    """
    return f"chat_id:{chat_id}:messages"


def redis_user_chat_key(user_id: str) -> str:
    return f"chat_list:user_id:{user_id}"
