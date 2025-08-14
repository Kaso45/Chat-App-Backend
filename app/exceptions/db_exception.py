"""Generic database exception types for repository layer."""


class DatabaseOperationError(Exception):
    """Generic database operation error wrapper for infrastructure layer."""


class DuplicateKeyError(Exception):
    """Raised when attempting to insert a duplicate unique key."""


class DatabaseConnectionError(Exception):
    """Raised when a database connection cannot be established or maintained."""
