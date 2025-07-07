"""Module providing schemas for user model request and response"""

from pydantic import BaseModel, EmailStr

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserLoginResponse(BaseModel):
    access_token: str

class UserRegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserRegisterResponse(BaseModel):
    msg: str
    user_id: str

class ForgetPasswordRequest(BaseModel):
    """Password reset request form"""
    email: EmailStr
