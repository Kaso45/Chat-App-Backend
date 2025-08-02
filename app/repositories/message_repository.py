import json
import logging
from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.database import message_collection
from app.exceptions.db_exception import DatabaseOperationError
from app.custom_classes.pyobjectid import PyObjectId
from app.exceptions.message_exception import MessageNotFoundError
from app.models.message import MessageModel
from app.redis_client import redis_chat_key, r

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

    async def cache_messages(
        self, chat_id: str, message: MessageModel, limit: int = 50
    ):
        key = redis_chat_key(chat_id)
        message_dict = message.model_dump(mode="json")
        await r.lpush(key, json.dumps(message_dict))  # type: ignore
        await r.ltrim(key, 0, limit - 1)  # type: ignore

    # async def get_recent_messages(self, chat_id: str, limit: int) -> list[MessageModel]:
    #     cursor = (
    #         self.collection.find({"chat_id": chat_id})
    #         .sort("created_at", -1)
    #         .limit(limit)
    #     )
    #     results = await cursor.to_list(length=limit)
    #     results.reverse()
    #     return [MessageModel(**message) for message in results]
