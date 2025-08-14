"""Exception classes for message-related error conditions."""


class MessageNotFoundError(Exception):
    """Raised when a message cannot be found by the given identifier."""


class ChatRoomRoutingError(Exception):
    """Raised when routing a message to a chat room fails due to config/state."""


class SendingMessageError(Exception):
    """Raised when a realtime send operation fails."""
