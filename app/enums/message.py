"""Enums for message types and delivery statuses."""

from enum import Enum


class MessageType(str, Enum):
    """Supported message content types."""

    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VIDEO = "video"


class MessageStatus(str, Enum):
    """Lifecycle status of a message as seen by clients."""

    SENT = "sent"
    SEEN = "seen"
    FAILED = "failed"
    SENDING = "sending"
