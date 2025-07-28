"""Module providing user repository layer"""

import logging
from pydantic import EmailStr
from motor.motor_asyncio import AsyncIOMotorCollection

from app.models.user import UserModel
from app.database.database import user_collection
from app.exceptions.auth_exception import UserNotFoundError
from app.exceptions.db_exception import DatabaseOperationError, DuplicateKeyError
from app.custom_classes.pyobjectid import PyObjectId


logger = logging.getLogger(__name__)


class UserRepository:
    """User Repository"""

    def __init__(self, collection: AsyncIOMotorCollection = user_collection):
        self.collection = collection

    async def ensure_indexes(self):
        try:
            await self.collection.create_index("email", unique=True)
        except DuplicateKeyError:
            logger.warning("Email index already exists")
        except Exception as e:
            logger.exception("Index creation failed")
            raise DatabaseOperationError from e

    async def get_by_email(self, email: EmailStr):
        user = await self.collection.find_one({"email": email})
        if not user:
            raise UserNotFoundError("User not found")
        return UserModel(**user)

    async def exist_email(self, email: EmailStr) -> bool:
        user = await self.collection.find_one({"email": email})
        if user:
            return True
        return False

    async def get_by_id(self, user_id: str):
        try:
            object_user_id = PyObjectId(user_id)
            user = await self.collection.find_one({"_id": object_user_id})
            return UserModel(**user) if user else None
        except Exception as e:
            raise DatabaseOperationError(f"Failed to fetch user by ID: {str(e)}") from e

    async def create(self, data: dict):
        try:
            result = await self.collection.insert_one(data)
            return str(result.inserted_id)
        except DuplicateKeyError:
            logger.error("Duplicate email: %s", {data.get("email")})
            raise
        except Exception as e:
            logger.exception("User creation failed")
            raise DatabaseOperationError from e

    async def update(self, user_id: str, update_data: dict):
        """Update user data

        Args:
            user_id: Hex string of ObjectId
            update_data: Dictionary of fields to update

        Returns:
            True if update was successful

        Raises:
            UserNotFoundError: If user not found
            DatabaseOperationError: For other errors
        """
        try:
            object_id = PyObjectId(user_id)
            result = await self.collection.update_one(
                {"_id": object_id}, {"$set": update_data}
            )

            return result
        except Exception as e:
            raise DatabaseOperationError(f"Failed to update user: {str(e)}") from e

    async def update_password(self, email: EmailStr, password: str):
        result = await self.collection.update_one(
            {"email": email}, {"$set": {"password": password}}
        )
        return result
