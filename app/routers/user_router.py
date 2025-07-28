"""Module providing functions for authentication endpoint"""

from fastapi import APIRouter, status, BackgroundTasks, Query, Depends, Response

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

router = APIRouter(prefix="/api/auth", tags=["Users"])


def get_user_repository() -> UserRepository:
    return UserRepository()


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserService:
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
    response: Response,
    user_service: UserService = Depends(get_user_service),
):
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
