"""Enums for user roles and presence status."""

from enum import Enum


class UserRole(str, Enum):
    """Role of a user within the system or a group chat."""

    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner"  # For group chats


class UserStatus(str, Enum):
    """Presence indicator for a user."""

    ONLINE = "online"
    INACTIVE = "inactive"
    OFFLINE = "offline"
