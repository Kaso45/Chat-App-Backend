from pydantic import BaseModel

from app.enums.chat import ChatType


class ChatCreate(BaseModel):
    chat_type: ChatType
    participants: list[str]  # User IDs

class PersonalChatCreate(ChatCreate):
    pass

class GroupChatCreate(ChatCreate):
    name: str
    admins: list[str] = []
