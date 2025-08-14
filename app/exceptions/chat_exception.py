"""Exception classes related to chat database operations."""


class ChatDatabaseError(Exception):
    """Base class for chat database-related errors."""


class ChatNotFoundError(ChatDatabaseError):
    """Raised when a chat room cannot be located in the database."""
