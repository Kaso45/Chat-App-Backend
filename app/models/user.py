"""Module providing Pydantic model for user"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.util.pyobjectid import PyObjectId

class UserModel(BaseModel):
    """Pydantic model for user"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    email: str
    username: str
    password: str
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "email": "kaso45@gmail.com",
                "username": "Kaso45",
                "password": "1234"
            }
        },
    )
