class UserNotFoundError(Exception):
    pass


class CredentialException(Exception):
    pass


class HeaderParsingError(Exception):
    pass


class JWTDecodeError(Exception):
    pass
