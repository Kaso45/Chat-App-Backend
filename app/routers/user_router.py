"""HTTP routes for authentication, password reset, and user listing."""

from fastapi import APIRouter, status, BackgroundTasks, Query, Depends, Response
from fastapi.responses import JSONResponse

from app.schemas.user_schema import (
    UserLoginRequest,
    UserLoginResponse,
    UserRegisterRequest,
    UserRegisterResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.user_service import UserService
from app.repositories.user_repository import UserRepository
from app.dependencies import get_current_user
from app.models.user import UserModel

router = APIRouter(prefix="/api/auth", tags=["Users"])


def get_user_repository() -> UserRepository:
    """Dependency provider for `UserRepository`."""
    return UserRepository()


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    """Construct a `UserService` with a repository dependency."""
    return UserService(user_repo)


@router.post(
    "/login",
    response_description="Login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
    response_model_by_alias=False,
)
async def login(
    request: UserLoginRequest,
    response: JSONResponse,
    user_service: UserService = Depends(get_user_service),
):
    """Authenticate user and set access token cookie."""
    return await user_service.login_user(request=request, response=response)


@router.post(
    "/register",
    response_description="Register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False,
)
async def register(
    request: UserRegisterRequest, user_service: UserService = Depends(get_user_service)
):
    """Register a new user account."""
    return await user_service.register_user(request)


@router.post(
    "/forgot-password",
    response_description="Forget password",
    status_code=status.HTTP_200_OK,
    response_model_by_alias=False,
)
async def forgot_password(
    request: ForgotPasswordRequest,
    bg: BackgroundTasks,
    user_service: UserService = Depends(get_user_service),
):
    """
    Forgot password route to send forgot password email

    Args:
        request (ForgotPasswordRequest): Request schema
        bg (BackgroundTasks): Handle background tasks
        user_service (UserService, optional): Inject UserService class

    Raises:
        HTTPException: 500 Internal Server Error

    Returns:
        JSON: {"msg": "Email sent"}
    """
    return await user_service.forgot_password(request, bg)


@router.post(
    "/reset-password",
    response_description="Reset password",
    status_code=status.HTTP_200_OK,
    response_model_by_alias=False,
)
async def reset_password(
    data: ResetPasswordRequest,
    token: str = Query(...),
    user_service: UserService = Depends(get_user_service),
):
    """
    Reset password route

    Args:
        data (ResetPasswordRequest): Reset password schema
        token (str, optional): Forgot password JWT token. Defaults to Query(...).
        user_service (UserService, optional): Inject UserService class

    Raises:
        HTTPException: 500 Internal Server Error

    Returns:
        JSON: {"msg": "Password updated successfully"}
    """
    return await user_service.reset_password(data, token)


@router.post("/logout")
async def logout(
    response: Response, user_service: UserService = Depends(get_user_service)
):
    """
    Logout user route

    Args:
        response (Response): Used to store JWT token in to HTTP cookie
        user_service (UserService, optional): Inject UserService class

    Raises:
        HTTPException: 500 Internal Server Error

    Returns:
        JSON: {"message": "Successfully logged out"}
    """
    return await user_service.logout(response)


@router.get(
    "/me",
    response_description="Get current user's username",
    status_code=status.HTTP_200_OK,
)
async def get_username(current_user: UserModel = Depends(get_current_user)):
    """Return the current user's username (auth required)."""
    return {"user_id": current_user.id, "username": current_user.username}


@router.get(
    "/users",
    response_description="List/search users",
    status_code=status.HTTP_200_OK,
)
async def list_users(
    q: str | None = Query(default=None, description="Search text for username/email"),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: UserModel = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Return a list of users for 'Find people' feature, excluding the caller."""
    current_user_id = str(current_user.id)
    results = await user_repo.search_users(
        q, exclude_user_id=current_user_id, limit=limit
    )
    return {"items": results}
