"""Module contains dependency injection functions"""

from fastapi import (
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from jose import jwt, JWTError

from app.repositories.user_repository import UserRepository
from app.util.jwt_util import verify_token
from app.config.config import settings
from app.exceptions.auth_exception import (
    CredentialException,
    HeaderParsingError,
    UserNotFoundError,
)


def get_user_repository() -> UserRepository:
    """
    User repository injection
    """
    return UserRepository()


async def get_current_user_ws(websocket: WebSocket) -> str:
    try:
        token = websocket.cookies.get("access_token")
        if not token:
            raise HeaderParsingError("Missing access_token cookie")

        if token.startswith("Bearer "):
            token = token[7:]

        user_id = verify_token(token)
        if not user_id:
            raise WebSocketDisconnect(code=1008, reason="Unauthorized user")

        return user_id
    except HeaderParsingError as e:
        raise WebSocketDisconnect(code=1008, reason="Failed to parse header") from e
    except Exception as e:
        raise WebSocketDisconnect(code=1011, reason="Internal server error") from e


async def get_current_user(
    request: Request, user_repo: UserRepository = Depends(get_user_repository)
):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    if token.startswith("Bearer "):
        token = token[7:]

    try:
        payload = jwt.decode(
            token, settings.ACCESS_TOKEN_SECRET, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise CredentialException
    except JWTError as e:
        raise CredentialException("Failed to validate token") from e

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise UserNotFoundError("User not found")
    return user
