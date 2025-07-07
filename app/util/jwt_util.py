"""Module providing function to manage JWT token"""

from datetime import timedelta, datetime, timezone
from jose import jwt

from app.config import settings

ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET
RESET_PASSWORD_TOKEN_SECRET = settings.RESET_PASSWORD_TOKEN_SECRET
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTE = 30

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Function for creating access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, ACCESS_TOKEN_SECRET, algorithm=ALGORITHM)

def create_reset_password_token(email: str):
    """Function for creating reset password token"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    data = {"sub": email, "exp": expire}
    return jwt.encode(data, RESET_PASSWORD_TOKEN_SECRET, algorithm=ALGORITHM)
