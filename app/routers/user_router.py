"""Module providing functions for authentication endpoint"""

from fastapi import APIRouter, status, HTTPException

from app.models.user import UserModel
from app.database.database import user_collection
from app.util.password_hashing_util import hash_password, verify_password
from app.util.jwt_util import create_access_token

router = APIRouter(
    prefix="/api/auth"
)

@router.post(
    "/login",
    response_description="Login",
    status_code=status.HTTP_200_OK,
    response_model_by_alias=False
)
async def login(request: UserModel):
    """Function for login"""
    # Verify user existence
    user_doc = await user_collection.find_one({"email": request.email})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    try:
        # Verify password
        user = UserModel(**user_doc)
        if not verify_password(request.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Wrong password"
            )
        
        # Verify email
        if request.email != user.email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Wrong email"
            )

        # Generate access token
        token = create_access_token(data={"sub": str(user.id)})

        return {"token": token}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) from e

@router.post(
    "/register",
    response_description="Register",
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def register(request: UserModel):
    """Function for registration"""
    # Check for existing user
    existing_user = await user_collection.find_one({"email": request.email})
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
        result = await user_collection.insert_one(user_data)
        user_data["_id"] = result.inserted_id

        return {"msg": "User created", "user_id": str(result.inserted_id)}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) from e