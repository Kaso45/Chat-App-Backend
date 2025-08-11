"""Module providing user service layer"""

import logging
from fastapi import HTTPException, status, BackgroundTasks, Query, Response
from fastapi.responses import JSONResponse
from fastapi_mail import MessageSchema, MessageType, FastMail

from app.schemas.user_schema import (
    UserLoginRequest,
    UserRegisterRequest,
    UserRegisterResponse,
)
from app.repositories.user_repository import UserRepository
from app.util.password_hashing_util import verify_password, hash_password
from app.util.jwt_util import (
    create_access_token,
    create_reset_password_token,
    verify_reset_password_token,
    ACCESS_TOKEN_EXPIRE_MINUTE,
)
from app.config.mail_config import mail_conf
from app.schemas.user_schema import ForgotPasswordRequest, ResetPasswordRequest
from app.config.config import settings
from app.exceptions.auth_exception import UserNotFoundError

logger = logging.getLogger(__name__)


def get_mail():
    """FastMail injection"""
    return FastMail(mail_conf)


class UserService:
    """User service class"""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def login_user(self, request: UserLoginRequest, response: JSONResponse):
        try:
            user = await self.user_repo.get_by_email(request.email)
        except UserNotFoundError:
            logger.error("User not found")
            raise
        except Exception as e:
            logger.exception("Login failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server error"
            ) from e

        try:
            # Verify password
            if not verify_password(request.password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong password"
                )

            # Generate access token
            access_token = create_access_token(data={"sub": str(user.id)})

            response = JSONResponse(content={"message": "Login successfully"})
            response.set_cookie(
                key="access_token",
                value=f"Bearer {access_token}",
                httponly=True,
                max_age=ACCESS_TOKEN_EXPIRE_MINUTE,
                secure=True,
                samesite="none",
                path="/",
            )

            return response
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
        existing_user = await self.user_repo.exist_email(request.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User already exists"
            )

        try:
            # Hash password
            hashed_password = hash_password(request.password)
            request.password = hashed_password

            # Insert into database
            user_data = request.model_dump(by_alias=True, exclude={"id"})
            result = await self.user_repo.create(user_data)

            return UserRegisterResponse(msg="User created", user_id=result)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e

    async def forgot_password(
        self,
        request: ForgotPasswordRequest,
        bg: BackgroundTasks,
    ):
        try:
            user = await self.user_repo.get_by_email(request.email)
        except UserNotFoundError:
            return {"message": "If email exists, reset link sent"}
        except Exception as e:
            logger.exception("Password reset failed")
            raise HTTPException(500, "Server error") from e

        reset_token = create_reset_password_token(request.email)
        url = f"http://localhost:3000/reset/password/{reset_token}"

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
        fm = get_mail()
        bg.add_task(fm.send_message, message, template_name="reset_password_email.html")
        return {"msg": "Email sent"}

    async def reset_password(
        self, request: ResetPasswordRequest, token: str = Query(...)
    ):
        """Reset password

        Args:
            request (ResetPasswordRequest): New password and confirm new password
            token (str, optional): Reset password token query from parameter

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
        result = await self.user_repo.update_password(email, new_password)

        if result.modified_count != 1:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Change password failed",
            )

        return {"msg": "Password updated successfully"}

    async def logout(self, response: Response):
        """
        Logout user by deleting HTTP cookie token

        Args:
            response (Response): Customize response by delete access token

        Returns:
            JSON: {"message": "Successfully logged out"}
        """
        response.delete_cookie(key="access_token")

        return {"message": "Successfully logged out"}
