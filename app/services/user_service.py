"""Module providing user service layer"""

from fastapi import HTTPException, status, BackgroundTasks, Query
from fastapi_mail import MessageSchema, MessageType, FastMail

from app.schemas.user_schema import (
    UserLoginRequest,
    UserLoginResponse,
    UserRegisterRequest,
    UserRegisterResponse,
)
from app.repositories.user_repository import UserRepository
from app.util.password_hashing_util import verify_password, hash_password
from app.util.jwt_util import (
    create_access_token,
    create_reset_password_token,
    verify_reset_password_token,
)
from app.config.mail_config import mail_conf
from app.schemas.user_schema import ForgotPasswordRequest, ResetPasswordRequest
from app.config.config import settings


class UserService:
    """User service class"""

    def __init__(self):
        self.repo = UserRepository()

    async def login_user(self, request: UserLoginRequest) -> UserLoginResponse:
        """Login logic

        Args:
            request (UserLoginRequest): Email and password

        Raises:
            HTTPException: 404 Not Found
            HTTPException: 401 Unauthorized
            HTTPException: 500 Internal Server Error

        Returns:
            UserLoginResponse: Access token
        """
        user = await self.repo.get_by_email(email=request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        try:
            # Verify password
            if not verify_password(request.password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong password"
                )

            # Generate access token
            token = create_access_token(data={"sub": str(user.id)})

            return UserLoginResponse(access_token=token)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e

    async def register_user(self, request: UserRegisterRequest) -> UserRegisterResponse:
        """Register logic

        Args:
            request (UserRegisterRequest): Email, username and password

        Raises:
            HTTPException: 409 Conflict
            HTTPException: 500 Internal Server Error

        Returns:
            UserRegisterResponse: Successful message and user Id
        """
        # Check for existing user
        existing_user = await self.repo.get_by_email(request.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User already exists"
            )

        try:
            # Hash password
            hashed_password = hash_password(request.password)
            request.password = hashed_password

            # Insert into database
            user_data = request.model_dump(by_alias=True, exclude="id")
            result = await self.repo.create(user_data)

            return UserRegisterResponse(
                msg="User created", user_id=str(result.inserted_id)
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e

    async def forgot_password(
        self, request: ForgotPasswordRequest, bg: BackgroundTasks
    ):
        """Send forgot password email

        Args:
            request (ForgotPasswordRequest): Email address
            bg (BackgroundTasks): BackgroundTasks class handles sending mail in the background

        Raises:
            HTTPException: 404 NOT FOUND, "User not found"

        Returns:
            dict[str, str]: Successful message
        """
        user = await self.repo.get_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        reset_token = create_reset_password_token(request.email)
        url = f"http://127.0.0.1:8000/api/auth/reset-password?token={reset_token}"

        message = MessageSchema(
            subject="Reset your password",
            recipients=[request.email],
            template_body={
                "url": url,
                "expire": settings.RESET_PASSWORD_TOKEN_EXPIRE_MINUTE,
                "username": user.username,
            },
            subtype=MessageType.html,
        )
        fm = FastMail(mail_conf)
        bg.add_task(fm.send_message, message, template_name="reset_password_email.html")
        return {"msg": "Email sent"}

    async def reset_password(
        self, request: ResetPasswordRequest, token: str = Query(...)
    ):
        """Reset password

        Args:
            request (ResetPasswordRequest): New password and confirm new password
            token (str, optional): Reset password token query from parameter. Defaults to Query(...).

        Raises:
            HTTPException: 400 BAD REQUEST, "Invalid or expired token"
            HTTPException: 409 CONFLICT, "Password not match"
            HTTPException: 500 INTERNAL SERVER ERROR, "Change password failed"

        Returns:
            dict[str, str]: Successful message
        """
        email = verify_reset_password_token(token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token",
            )

        if request.new_password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Password not match"
            )

        new_password = hash_password(request.new_password)
        result = await self.repo.collection.update_one(
            {"email": email}, {"$set": {"password": new_password}}
        )

        if result.modified_count != 1:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Change password failed",
            )

        return {"msg": "Password updated successfully"}
