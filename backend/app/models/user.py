"""
User management request and response models

Defines Pydantic models for user CRUD operations.
"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from backend.app.db.models import UserRole


class UserBase(BaseModel):
    """Base user model with common fields"""
    email: EmailStr = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    role: UserRole = Field(default=UserRole.WRITER, description="User's role")


class UserCreateRequest(UserBase):
    """
    Request model for creating a new user

    Requires password for initial account setup
    """
    password: str = Field(
        ...,
        min_length=8,
        description="User's password (min 8 characters)",
        examples=["SecurePassword123!"]
    )
    is_active: bool = Field(default=True, description="Whether the account is active")
    is_superuser: bool = Field(default=False, description="Grant superuser privileges")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "newuser@orgarchive.org",
                "full_name": "New User",
                "password": "SecurePassword123!",
                "role": "writer",
                "is_active": True,
                "is_superuser": False
            }
        }
    }


class UserUpdateRequest(BaseModel):
    """
    Request model for updating a user

    All fields are optional - only provided fields will be updated
    """
    email: Optional[EmailStr] = Field(None, description="Update email address")
    full_name: Optional[str] = Field(None, description="Update full name")
    password: Optional[str] = Field(
        None,
        min_length=8,
        description="Update password (min 8 characters)"
    )
    role: Optional[UserRole] = Field(None, description="Update user's role")
    is_active: Optional[bool] = Field(None, description="Update account active status")
    is_superuser: Optional[bool] = Field(None, description="Update superuser status")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        """Validate password strength if provided"""
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "Updated Name",
                "role": "editor",
                "is_active": True
            }
        }
    }


class UserResponse(BaseModel):
    """
    Response model for user information

    Returns user details without sensitive information like password
    """
    user_id: str = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    role: str = Field(..., description="User's role (admin, editor, writer)")
    is_active: bool = Field(..., description="Whether the account is active")
    is_superuser: bool = Field(..., description="Whether user has superuser privileges")
    created_at: datetime = Field(..., description="When the account was created")
    updated_at: datetime = Field(..., description="When the account was last updated")

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@orgarchive.org",
                "full_name": "John Doe",
                "role": "editor",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2025-10-15T10:30:00.000000",
                "updated_at": "2025-10-20T14:45:00.000000"
            }
        }
    }


class UserListResponse(BaseModel):
    """
    Response model for paginated user list

    Supports filtering and pagination
    """
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users matching filters")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of users per page")
    total_pages: int = Field(..., description="Total number of pages")

    model_config = {
        "json_schema_extra": {
            "example": {
                "users": [
                    {
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "email": "admin@orgarchive.org",
                        "full_name": "Admin User",
                        "role": "admin",
                        "is_active": True,
                        "is_superuser": True,
                        "created_at": "2025-10-01T10:00:00.000000",
                        "updated_at": "2025-10-01T10:00:00.000000"
                    }
                ],
                "total": 25,
                "page": 1,
                "page_size": 10,
                "total_pages": 3
            }
        }
    }


class UserDeleteResponse(BaseModel):
    """
    Response model for user deletion/deactivation

    Confirms successful deactivation
    """
    message: str = Field(
        ...,
        description="Confirmation message"
    )
    user_id: str = Field(..., description="ID of deactivated user")
    email: str = Field(..., description="Email of deactivated user")
    deactivated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of deactivation"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "User account deactivated successfully",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@orgarchive.org",
                "deactivated_at": "2025-10-30T04:20:00.000000"
            }
        }
    }
