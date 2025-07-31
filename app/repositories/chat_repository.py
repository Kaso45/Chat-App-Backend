import logging
from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.database import chat_collection
from app.exceptions.db_exception import DatabaseOperationError
from app.custom_classes.pyobjectid import PyObjectId
from app.models.chat import ChatModel

logger = logging.getLogger(__name__)

class ChatRepository:
    def __init__(self, collection: AsyncIOMotorCollection = chat_collection):
        self.collection = collection

    async def get_by_id(self, chat_id: str) -> ChatModel:
        try:
            obj_id = PyObjectId(chat_id)
            result = await self.collection.find_one({"_id": obj_id})
            return ChatModel(**result)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to fetch for chat: {str(e)}") from e

    async def create(self, chat_doc: ChatModel):
        try:
            data = chat_doc.model_dump(by_alias=True, exclude="id")
            result = await self.collection.insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            raise DatabaseOperationError(f"Failed to create chat: {str(e)}") from e
