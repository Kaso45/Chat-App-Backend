"""Enums related to chat domain (e.g., chat types)."""

from enum import Enum


class ChatType(str, Enum):
    """Type of chat room: personal (1:1) or group."""

    PERSONAL = "personal"
    GROUP = "group"
