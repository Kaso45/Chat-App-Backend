"""Module providing user repository layer"""

import logging
from typing import Optional, Iterable
from bson.errors import InvalidId
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
        """Create necessary indexes (email uniqueness)."""
        try:
            await self.collection.create_index("email", unique=True)
        except DuplicateKeyError:
            logger.warning("Email index already exists")
        except Exception as e:
            logger.exception("Index creation failed")
            raise DatabaseOperationError from e

    async def get_by_email(self, email: EmailStr):
        """Fetch a user by email or raise `UserNotFoundError`."""
        user = await self.collection.find_one({"email": email})
        if not user:
            raise UserNotFoundError("User not found")
        return UserModel(**user)

    # Removed duplicate early definition of get_usernames_by_ids

    async def exist_email(self, email: EmailStr) -> bool:
        """Return True if a user with the given email exists."""
        user = await self.collection.find_one({"email": email})
        if user:
            return True
        return False

    async def get_by_id(self, user_id: str):
        """Fetch a user by id and return `UserModel` or None if not found."""
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

    async def get_basic_profiles_by_ids(self, user_ids: Iterable[str]) -> list[dict]:
        """Fetch basic profiles (id, username, email) for a list of user IDs in one query.

        Preserves the input order and skips IDs not found.
        """
        try:
            # Preserve order while deduplicating
            ordered_unique_ids: list[str] = []
            seen: set[str] = set()
            for uid in user_ids:
                if uid and uid not in seen:
                    seen.add(uid)
                    ordered_unique_ids.append(uid)

            if not ordered_unique_ids:
                return []

            object_ids = [PyObjectId(uid) for uid in ordered_unique_ids]
            projection = {"username": 1, "email": 1}
            cursor = self.collection.find({"_id": {"$in": object_ids}}, projection)
            docs = await cursor.to_list(length=None)

            by_id = {str(doc.get("_id")): doc for doc in docs}
            return [
                {
                    "id": uid,
                    "username": by_id[uid].get("username"),
                    "email": by_id[uid].get("email"),
                }
                for uid in ordered_unique_ids
                if uid in by_id
            ]
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to fetch user profiles by IDs: {str(e)}"
            ) from e

    async def create(self, data: dict):
        """Insert a new user and return its inserted id."""
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
        """Update a user's password by email and return the update result."""
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
                except InvalidId as e:  # pragma: no cover - defensive
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
