from enum import Enum

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VIDEO = "video"

class MessageStatus(str, Enum):
    SENT = "sent"
    SEEN = "seen"
    FAILED = "failed"
    SENDING = "sending"
