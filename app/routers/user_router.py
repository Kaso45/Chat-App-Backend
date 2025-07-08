"""Module providing functions for authentication endpoint"""

from fastapi import APIRouter, status, BackgroundTasks, Query

from app.schemas.user_schema import (
    UserLoginRequest,
    UserLoginResponse,
    UserRegisterRequest,
    UserRegisterResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/api/auth", tags=["Users"])


@router.post(
    "/login",
    response_description="Login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
    response_model_by_alias=False,
)
async def login(request: UserLoginRequest):
    """Login endpoint

    Args:
        request (UserLoginRequest): Email and password

    Returns:
        UserLoginResponse: Access token
    """
    service = UserService()
    return await service.login_user(request)


@router.post(
    "/register",
    response_description="Register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False,
)
async def register(request: UserRegisterRequest):
    """Register endpoint

    Args:
        request (UserRegisterRequest): Email, username and password

    Returns:
        UserRegisterResponse: Message and user Id
    """
    service = UserService()
    return await service.register_user(request)


@router.post(
    "/forgot-password",
    response_description="Forget password",
    status_code=status.HTTP_200_OK,
    response_model_by_alias=False,
)
async def forgot_password(request: ForgotPasswordRequest, bg: BackgroundTasks):
    service = UserService()
    return await service.forgot_password(request, bg)


@router.post(
    "/reset-password",
    response_description="Reset password",
    status_code=status.HTTP_200_OK,
    response_model_by_alias=False,
)
async def reset_password(data: ResetPasswordRequest, token: str = Query(...)):
    service = UserService()
    return await service.reset_password(data, token)
