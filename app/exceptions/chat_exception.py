class ChatDatabaseError(Exception):
    pass

class ChatNotFoundError(ChatDatabaseError):
    pass
