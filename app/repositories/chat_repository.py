import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorCollection
from redis.asyncio import Redis

from app.database.database import chat_collection
from app.exceptions.chat_exception import ChatNotFoundError
from app.exceptions.db_exception import DatabaseOperationError, DuplicateKeyError
from app.custom_classes.pyobjectid import PyObjectId
from app.models.chat import ChatModel
from app.redis_client import (
    redis_user_chat_rooms_key,
    redis_chat_data_key,
    redis_user_chat_rooms_complete_key,
)

logger = logging.getLogger(__name__)


class ChatRepository:
    def __init__(self, collection: AsyncIOMotorCollection = chat_collection):
        self.collection = collection

    async def ensure_indexes(self):
        try:
            await self.collection.create_index(
                [("last_updated", -1), ("participants", 1)]
            )
        except DuplicateKeyError:
            logger.warning("Index already exists")
        except Exception as e:
            logger.exception("Index creation failed")
            raise DatabaseOperationError from e

    async def get_by_id(self, chat_id: str) -> ChatModel:
        try:
            obj_id = PyObjectId(chat_id)
            result = await self.collection.find_one({"_id": obj_id})
            if not result:
                raise ChatNotFoundError(f"Chat with id {chat_id} not found")

            return ChatModel(**result)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to fetch for chat: {str(e)}") from e

    async def create(self, chat_doc: ChatModel):
        try:
            data = chat_doc.model_dump(by_alias=True, exclude={"id"})
            result = await self.collection.insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to create chat: {str(e)}") from e

    def get_chats_cursor(
        self, query: dict[str, dict], sort: dict[str, int], limit: int
    ):
        cursor = self.collection.find(query).sort(sort).limit(limit)
        return cursor

    async def find_personal_chat_between(
        self, user_a: str, user_b: str
    ) -> Optional[str]:
        """Return existing personal chat id for two users if exists.

        The query orders the participants pair to be independent of user order.
        """
        try:
            # participants contains exactly both user ids (size 2) and chat_type is personal
            query = {
                "chat_type": "personal",
                "$and": [
                    {"participants": {"$size": 2}},
                    {"participants": {"$all": [user_a, user_b]}},
                ],
            }
            # Limit projection to _id only
            doc = await self.collection.find_one(query, {"_id": 1})
            return str(doc.get("_id")) if doc else None
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to find existing personal chat: {str(e)}"
            ) from e


class ChatRedisRepository:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def cache_chat_room(
        self, user_id: str, chat_model: ChatModel, chat_id: Optional[str] = None
    ):
        key = redis_user_chat_rooms_key(user_id)
        effective_chat_id: Optional[str] = chat_id or (
            str(chat_model.id) if chat_model.id is not None else None
        )
        if not effective_chat_id:
            raise ValueError("cache_chat_room requires a valid chat_id")
        score = float(chat_model.last_updated.timestamp() * 1000)
        chat_hash_key = redis_chat_data_key(effective_chat_id)

        # Normalize values to Redis-compatible types (str / int / float)
        chat_data = {
            "name": chat_model.name or "",
            "last_updated": chat_model.last_updated.isoformat(),
            "type": getattr(chat_model.chat_type, "value", str(chat_model.chat_type)),
            # Store participants as CSV for later resolution in cache path
            "participants": ",".join(chat_model.participants or []),
        }

        pipe = self.redis.pipeline()
        pipe.zadd(key, {effective_chat_id: score})
        pipe.hset(chat_hash_key, mapping=chat_data)
        # Keep hash and sorted set in sync with TTL
        pipe.expire(key, 86400)
        pipe.expire(chat_hash_key, 86400)
        # Do not set completeness flag here; that is set when DB backfills a full page
        await pipe.execute()

    async def mark_user_chats_complete(self, user_id: str):
        """Mark user's chat rooms cache as complete/backfilled."""
        key = redis_user_chat_rooms_complete_key(user_id)
        await self.redis.set(key, "1", ex=86400)
