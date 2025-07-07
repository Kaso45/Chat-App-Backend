"""Module providing user service layer"""

from fastapi import HTTPException, status

from app.schemas.user_schema import (
    UserLoginRequest,
    UserLoginResponse,
    UserRegisterRequest,
    UserRegisterResponse
)
from app.repositories.user_repository import UserRepository
from app.util.password_hashing_util import verify_password, hash_password
from app.util.jwt_util import create_access_token

class UserService:
    """User service class
    """
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        try:
            # Verify password
            if not verify_password(request.password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Wrong password"
                )

            # Generate access token
            token = create_access_token(data={"sub": str(user.id)})

            return UserLoginResponse(access_token=token)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
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
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists"
            )

        try:
            # Hash password
            hashed_password = hash_password(request.password)
            request.password = hashed_password

            # Insert into database
            user_data = request.model_dump(by_alias=True, exclude="id")
            result = await self.repo.create(user_data)

            return UserRegisterResponse(
                msg="User created",
                user_id=str(result.inserted_id)
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            ) from e
