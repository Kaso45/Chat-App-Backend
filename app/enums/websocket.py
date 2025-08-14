"""Enums for websocket payload types used in realtime events."""

from enum import Enum


class PayloadType(str, Enum):
    """Event type identifiers for websocket messages."""

    LOAD_CHAT = "load_chat"
    NEW_MESSAGE = "new_message"
    NEW_CHAT_ROOM = "new_chat_room"
