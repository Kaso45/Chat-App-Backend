"""Redis config"""

import redis.asyncio as redis

from app.config.config import settings

r = redis.Redis(
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
