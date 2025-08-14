"""Exception classes related to authentication and authorization."""


class UserNotFoundError(Exception):
    """Raised when a requested user cannot be found."""


class CredentialException(Exception):
    """Raised when credentials are missing or invalid."""


class HeaderParsingError(Exception):
    """Raised for malformed or missing authentication headers/cookies."""


class JWTDecodeError(Exception):
    """Raised when a JWT cannot be decoded or validated."""
