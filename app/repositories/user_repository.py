"""Module providing user repository layer"""

from pydantic import EmailStr

from app.models.user import UserModel
from app.database.database import user_collection

class UserRepository:
    """User Repository
    """
    def __init__(self):
        self.collection = user_collection

    async def get_by_email(self, email: EmailStr) -> UserModel:
        """Get user by email

        Args:
            email (EmailStr): Email get from request body

        Returns:
            UserModel: User Pydantic model
        """
        user = await self.collection.find_one({"email": email})
        if user:
            return UserModel(**user)

    async def create(self, data: dict):
        return await user_collection.insert_one(data)
