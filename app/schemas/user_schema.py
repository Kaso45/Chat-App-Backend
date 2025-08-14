"""Pydantic schemas for user auth and account operations."""

from pydantic import BaseModel, EmailStr


class UserLoginRequest(BaseModel):
    """Request payload for user login."""

    email: EmailStr
    password: str


class UserLoginResponse(BaseModel):
    """Response containing the issued JWT access token after successful login."""

    access_token: str


class UserRegisterRequest(BaseModel):
    """Request payload to register a new user account."""

    email: EmailStr
    username: str
    password: str


class UserRegisterResponse(BaseModel):
    """Response returned after successful registration."""

    msg: str
    user_id: str


class ForgotPasswordRequest(BaseModel):
    """Request to initiate a password reset by email."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request to reset a user's password by providing new credentials."""

    new_password: str
    confirm_password: str
