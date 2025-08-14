import logging
from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorCollection
from redis.asyncio import Redis

from app.database.database import message_collection
from app.exceptions.db_exception import DatabaseOperationError
from app.custom_classes.pyobjectid import PyObjectId
from app.exceptions.message_exception import MessageNotFoundError
from app.models.message import MessageModel
from app.redis_client import redis_chat_messages_key, redis_message_data_key

logger = logging.getLogger(__name__)


class MessageRepository:
    def __init__(self, collection: AsyncIOMotorCollection = message_collection):
        self.collection = collection

    async def get_by_id(self, message_id: str):
        try:
            obj_id = PyObjectId(message_id)
            message = await self.collection.find_one({"_id": obj_id})
            if not message:
                raise MessageNotFoundError(f"message with id {message_id} not found")

            return MessageModel(**message)
        except DatabaseOperationError:
            logger.error("Failed to fetch for message by ID")
            raise
        except Exception as e:
            logger.error("Server operation failed: %s", str(e))
            raise

    async def create(self, message: MessageModel):
        try:
            data = message.model_dump(by_alias=True, exclude={"id"})
            result = await self.collection.insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to create message: {str(e)}") from e

    async def update(self, message_id: str, data: dict) -> bool:
        try:
            obj_id = PyObjectId(message_id)
            result = await self.collection.update_one({"_id": obj_id}, {"$set": data})
            return result.modified_count > 0
        except Exception as e:
            raise DatabaseOperationError(f"Failed to update message: {str(e)}") from e

    async def remove(self, message_id: str):
        try:
            obj_id = PyObjectId(message_id)
            await self.collection.delete_one({"_id": obj_id})
        except Exception as e:
            raise DatabaseOperationError(f"Failed to delete message: {str(e)}") from e

    def get_messages_cursor(
        self, chat_id: str, limit: int, lt_timestamp: Optional[datetime] = None
    ):
        query: dict = {"chat_id": PyObjectId(chat_id)}
        if lt_timestamp is not None:
            query["timestamp"] = {"$lt": lt_timestamp}
        cursor = self.collection.find(query).sort("timestamp", -1).limit(limit)
        return cursor


class MessageRedisRepository:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def cache_message(self, chat_id: str, message: MessageModel):
        key = redis_chat_messages_key(chat_id)
        # Ensure message_id is a string for Redis keys. Support PyObjectId or str.
        mid = message.id
        message_id = str(mid) if mid is not None else ""
        score = float(message.timestamp.timestamp() * 1000)
        message_hash_key = redis_message_data_key(message_id)

        message_data = {
            "id": message_id,
            "content": message.content or "",
            "sender": str(message.sender_id) if message.sender_id is not None else "",
            "timestamp": message.timestamp.isoformat(),
            "chat_id": chat_id,
            "message_type": getattr(
                message.message_type, "value", str(message.message_type)
            ),
            "message_status": getattr(
                message.message_status, "value", str(message.message_status)
            ),
            "is_edited": int(bool(message.is_edited)),
        }

        pipe = self.redis.pipeline()
        pipe.zadd(key, {message_id: score})
        pipe.hset(message_hash_key, mapping=message_data)
        pipe.expire(key, 43200)
        pipe.expire(message_hash_key, 43200)
        await pipe.execute()
