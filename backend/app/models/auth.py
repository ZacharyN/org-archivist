"""
Authentication Pydantic models

This module defines request and response models for authentication endpoints:
- User registration and login
- Session management
- User profile information
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator


class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password (min 8 characters)")
    full_name: Optional[str] = Field(None, description="User's full name")
    role: str = Field(default="writer", description="User role: admin, editor, or writer")

    @validator("role")
    def validate_role(cls, v):
        """Validate role is one of the allowed values"""
        allowed_roles = ["admin", "editor", "writer"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "full_name": "John Doe",
                "role": "writer"
            }
        }


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class RefreshRequest(BaseModel):
    """Session refresh request"""
    refresh_token: str = Field(..., description="JWT refresh token")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class UserResponse(BaseModel):
    """User profile response"""
    user_id: UUID = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user account is active")
    is_superuser: bool = Field(..., description="Whether user is a superuser")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "role": "writer",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2025-10-30T12:00:00",
                "updated_at": "2025-10-30T12:00:00"
            }
        }


class LoginResponse(BaseModel):
    """Login response with tokens and user info"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_at: str = Field(..., description="Token expiration timestamp (ISO format)")
    user: UserResponse = Field(..., description="User profile information")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_at": "2025-10-30T13:00:00",
                "user": {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "role": "writer",
                    "is_active": True,
                    "is_superuser": False,
                    "created_at": "2025-10-30T12:00:00",
                    "updated_at": "2025-10-30T12:00:00"
                }
            }
        }


class SessionResponse(BaseModel):
    """Session validation response"""
    valid: bool = Field(..., description="Whether session is valid")
    user: Optional[UserResponse] = Field(None, description="User profile if session is valid")
    message: Optional[str] = Field(None, description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "user": {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "role": "writer",
                    "is_active": True,
                    "is_superuser": False,
                    "created_at": "2025-10-30T12:00:00",
                    "updated_at": "2025-10-30T12:00:00"
                },
                "message": "Session is valid"
            }
        }


class LogoutResponse(BaseModel):
    """Logout response"""
    success: bool = Field(..., description="Whether logout was successful")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully logged out"
            }
        }
