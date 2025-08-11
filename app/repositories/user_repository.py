"""Module providing user repository layer"""

import logging
from typing import Optional, Iterable
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

    # Removed duplicate early definition of get_usernames_by_ids

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

    async def get_usernames_by_ids(
        self, user_ids: Iterable[str]
    ) -> dict[str, Optional[str]]:
        """Fetch usernames for a set/list of user ids in one query.

        Returns a dict mapping user_id (str) -> username (str|None). Missing users
        will not be present in the result map.
        """
        try:
            unique_ids = list({uid for uid in user_ids if uid})
            if not unique_ids:
                return {}

            object_ids = [PyObjectId(uid) for uid in unique_ids]
            cursor = self.collection.find({"_id": {"$in": object_ids}}, {"username": 1})
            docs = await cursor.to_list(length=None)
            return {str(doc["_id"]): doc.get("username") for doc in docs}
        except Exception as e:
            raise DatabaseOperationError(f"Failed to fetch usernames: {str(e)}") from e

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

    async def search_users(
        self,
        search: Optional[str] = None,
        exclude_user_id: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Search users by username or email, optionally excluding one user.

        Returns a list of lightweight dicts: {"id", "username", "email"}
        """
        try:
            query: dict = {}
            if search:
                query["$or"] = [
                    {"username": {"$regex": search, "$options": "i"}},
                    {"email": {"$regex": search, "$options": "i"}},
                ]

            if exclude_user_id:
                try:
                    query["_id"] = {"$ne": PyObjectId(exclude_user_id)}
                except Exception as e:  # pragma: no cover - defensive
                    # Ignore invalid ObjectId string silently to avoid blocking search
                    logger.warning(
                        "Invalid exclude_user_id %s: %s", exclude_user_id, str(e)
                    )
                    query.pop("_id", None)

            projection = {"username": 1, "email": 1}
            cursor = self.collection.find(query, projection).limit(
                max(1, min(limit, 50))
            )
            docs = await cursor.to_list(length=None)
            return [
                {
                    "id": str(doc.get("_id")),
                    "username": doc.get("username"),
                    "email": doc.get("email"),
                }
                for doc in docs
            ]
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to search users from DB: {str(e)}"
            ) from e
