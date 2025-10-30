"""
Authentication request and response models

Defines Pydantic models for authentication-related API requests and responses.
"""

from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """
    Request model for user login

    Attributes:
        email: User's email address
        password: User's plain text password
    """
    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["user@example.com"]
    )
    password: str = Field(
        ...,
        min_length=8,
        description="User's password",
        examples=["SecurePassword123!"]
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "admin@orgarchive.org",
                "password": "AdminPass123!"
            }
        }
    }


class LoginResponse(BaseModel):
    """
    Response model for successful login

    Returns user information and authentication tokens
    """
    user_id: str = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    role: str = Field(..., description="User's role (admin, editor, writer)")
    access_token: str = Field(..., description="JWT access token for authentication")
    refresh_token: str = Field(..., description="JWT refresh token for obtaining new access tokens")
    expires_at: str = Field(..., description="ISO 8601 timestamp when access token expires")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "admin@orgarchive.org",
                "full_name": "System Administrator",
                "role": "admin",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "expires_at": "2025-10-30T04:30:00.000000",
                "token_type": "bearer"
            }
        }
    }


class RefreshRequest(BaseModel):
    """
    Request model for refreshing an access token

    Attributes:
        refresh_token: Valid JWT refresh token
    """
    refresh_token: str = Field(
        ...,
        description="JWT refresh token obtained during login"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    }


class RefreshResponse(BaseModel):
    """
    Response model for token refresh

    Returns new access and refresh tokens
    """
    access_token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="New JWT refresh token")
    expires_at: str = Field(..., description="ISO 8601 timestamp when new access token expires")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "expires_at": "2025-10-30T04:30:00.000000",
                "token_type": "bearer"
            }
        }
    }


class UserInfoResponse(BaseModel):
    """
    Response model for current user information

    Returns authenticated user's profile information
    """
    user_id: str = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    role: str = Field(..., description="User's role (admin, editor, writer)")
    is_active: bool = Field(..., description="Whether the user account is active")
    is_superuser: bool = Field(..., description="Whether the user has superuser privileges")
    created_at: datetime = Field(..., description="When the user account was created")

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "admin@orgarchive.org",
                "full_name": "System Administrator",
                "role": "admin",
                "is_active": True,
                "is_superuser": True,
                "created_at": "2025-10-15T10:30:00.000000"
            }
        }
    }


class LogoutResponse(BaseModel):
    """
    Response model for logout

    Confirms successful session termination
    """
    message: str = Field(
        default="Successfully logged out",
        description="Logout confirmation message"
    )
    logged_out_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of logout"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Successfully logged out",
                "logged_out_at": "2025-10-30T03:45:00.000000"
            }
        }
    }
