from enum import Enum


class PayloadType(str, Enum):
    LOAD_CHAT = "load_chat"
    NEW_MESSAGE = "new_message"
    NEW_CHAT_ROOM = "new_chat_room"
