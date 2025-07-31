from enum import Enum


class PayloadType(str, Enum):
    LOAD_CHAT = "load_chat"
    NEW_MESSAGE = "new_message"
