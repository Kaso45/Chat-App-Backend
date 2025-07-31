from enum import Enum


class UserRole(str, Enum):
    MEMBER = "member"
    ADMIN = "admin"
    OWNER = "owner"  # For group chats


class UserStatus(str, Enum):
    ONLINE = "online"
    INACTIVE = "inactive"
    OFFLINE = "offline"
