"""Exception wrapper for Redis-related failures."""


class RedisError(Exception):
    """Raised for Redis client and operation-level errors."""
