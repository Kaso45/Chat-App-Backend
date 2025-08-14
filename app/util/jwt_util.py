"""Utilities for creating and verifying JWTs for access and password reset."""

import logging
from datetime import timedelta, datetime, timezone
from jose import jwt, JWTError

from app.config.config import settings
from app.exceptions.auth_exception import JWTDecodeError


ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET
RESET_PASSWORD_TOKEN_SECRET = settings.RESET_PASSWORD_TOKEN_SECRET
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTE = settings.ACCESS_TOKEN_EXPIRE_MINUTE
RESET_PASSWORD_TOKEN_EXPIRE_MINUTE = settings.RESET_PASSWORD_TOKEN_EXPIRE_MINUTE

logger = logging.getLogger(__name__)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create access token

    Args:
        data (dict): A dictionary with "sub" field
        expires_delta (timedelta | None, optional): Optional expires time. Defaults to None.

    Returns:
        str: Access token string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTE)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, ACCESS_TOKEN_SECRET, algorithm=ALGORITHM)


def create_reset_password_token(email: str):
    """Create reset password token

    Args:
        email (str): User email

    Returns:
        str: Reset password token string
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=RESET_PASSWORD_TOKEN_EXPIRE_MINUTE
    )
    data = {"sub": email, "exp": expire}
    return jwt.encode(data, RESET_PASSWORD_TOKEN_SECRET, algorithm=ALGORITHM)


def verify_reset_password_token(token: str) -> str:
    """Verify reset password token

    Args:
        token (str): reset password token

    Returns:
        str: User email
    """
    try:
        payload = jwt.decode(token, RESET_PASSWORD_TOKEN_SECRET, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            raise JWTDecodeError("Token payload missing 'sub' claim")

        return subject
    except JWTError as e:
        raise JWTDecodeError("Failed to decode reset password token") from e


def verify_token(token: str) -> str:
    """Verify access token and return subject (user id) on success."""
    try:
        payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=ALGORITHM)
        subject = payload.get("sub")
        if subject is None:
            raise JWTDecodeError("Token payload missing 'sub' claim")

        return subject
    except JWTError as e:
        raise JWTDecodeError("Failed to decode access token") from e
