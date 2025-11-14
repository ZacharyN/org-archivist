"""
Program related Pydantic models

Models for program management API endpoints with validation
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import re

from .common import PaginationMetadata


class ProgramBase(BaseModel):
    """
    Base program model with common fields
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Program name"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Program description"
    )
    display_order: int = Field(
        default=0,
        ge=0,
        le=1000,
        description="Display order for UI sorting (higher = appears first)"
    )
    active: bool = Field(
        default=True,
        description="Whether program is active"
    )


class ProgramCreate(ProgramBase):
    """
    Request model for creating a new program (POST /api/programs)
    """

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate program name:
        - Strip whitespace
        - Ensure not empty after stripping
        - Check for valid characters (letters, numbers, spaces, hyphens, apostrophes, ampersands)
        """
        # Strip whitespace
        v = v.strip()

        # Ensure not empty after stripping
        if not v:
            raise ValueError("Program name cannot be empty or whitespace")

        # Check for valid characters (letters, numbers, spaces, hyphens, apostrophes, ampersands)
        if not re.match(r"^[a-zA-Z0-9\s\-'&]+$", v):
            raise ValueError(
                "Program name contains invalid characters. "
                "Only letters, numbers, spaces, hyphens, apostrophes, and ampersands are allowed."
            )

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Youth Development",
                "description": "Programs focused on youth ages 13-18",
                "display_order": 10,
                "active": True
            }
        }


class ProgramUpdate(BaseModel):
    """
    Request model for updating a program (PUT/PATCH /api/programs/{id})
    All fields are optional for partial updates
    """
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Program name"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Program description"
    )
    display_order: Optional[int] = Field(
        None,
        ge=0,
        le=1000,
        description="Display order for UI sorting"
    )
    active: Optional[bool] = Field(
        None,
        description="Whether program is active"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate program name if provided"""
        if v is None:
            return v

        # Strip whitespace
        v = v.strip()

        # Ensure not empty after stripping
        if not v:
            raise ValueError("Program name cannot be empty or whitespace")

        # Check for valid characters
        if not re.match(r"^[a-zA-Z0-9\s\-'&]+$", v):
            raise ValueError(
                "Program name contains invalid characters. "
                "Only letters, numbers, spaces, hyphens, apostrophes, and ampersands are allowed."
            )

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Early Childhood Education",
                "description": "Updated description for early childhood programs",
                "active": True
            }
        }


class ProgramResponse(ProgramBase):
    """
    Response model for program details (GET /api/programs/{id})
    """
    program_id: str = Field(
        ...,
        description="Unique program identifier (UUID)"
    )
    created_at: datetime = Field(
        ...,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp"
    )
    created_by: Optional[str] = Field(
        None,
        description="User ID who created the program (UUID)"
    )

    class Config:
        from_attributes = True  # For SQLAlchemy ORM compatibility
        json_schema_extra = {
            "example": {
                "program_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Youth Development",
                "description": "Programs focused on youth ages 13-18",
                "display_order": 10,
                "active": True,
                "created_at": "2025-11-14T12:00:00Z",
                "updated_at": "2025-11-14T12:00:00Z",
                "created_by": "123e4567-e89b-12d3-a456-426614174000"
            }
        }


class ProgramListResponse(BaseModel):
    """
    Response model for listing programs (GET /api/programs)

    Includes counts and pagination metadata for UI display
    """
    programs: List[ProgramResponse] = Field(
        ...,
        description="List of programs"
    )
    total: int = Field(
        ...,
        description="Total number of programs"
    )
    active_count: int = Field(
        ...,
        description="Number of active programs"
    )
    inactive_count: int = Field(
        ...,
        description="Number of inactive programs"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "programs": [
                    {
                        "program_id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "Youth Development",
                        "description": "Programs for youth ages 13-18",
                        "display_order": 10,
                        "active": True,
                        "created_at": "2025-11-14T12:00:00Z",
                        "updated_at": "2025-11-14T12:00:00Z",
                        "created_by": "123e4567-e89b-12d3-a456-426614174000"
                    }
                ],
                "total": 6,
                "active_count": 5,
                "inactive_count": 1
            }
        }


class ProgramDeleteResponse(BaseModel):
    """
    Response model for program deletion (DELETE /api/programs/{id})

    Includes impact information about documents using this program
    """
    success: bool = Field(
        ...,
        description="Deletion success status"
    )
    message: str = Field(
        ...,
        description="Status message"
    )
    program_id: str = Field(
        ...,
        description="Deleted program ID (UUID)"
    )
    documents_affected: int = Field(
        ...,
        description="Number of documents that were using this program"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Program deleted successfully",
                "program_id": "550e8400-e29b-41d4-a716-446655440000",
                "documents_affected": 12
            }
        }


class ProgramStatsResponse(BaseModel):
    """
    Response model for program statistics (GET /api/programs/stats)

    Provides aggregate information about program usage
    """
    total_programs: int = Field(
        ...,
        description="Total number of programs"
    )
    active_programs: int = Field(
        ...,
        description="Number of active programs"
    )
    inactive_programs: int = Field(
        ...,
        description="Number of inactive programs"
    )
    program_document_counts: dict[str, int] = Field(
        ...,
        description="Document count by program name"
    )
    most_used_program: Optional[str] = Field(
        None,
        description="Name of most frequently used program"
    )
    least_used_program: Optional[str] = Field(
        None,
        description="Name of least frequently used program"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total_programs": 6,
                "active_programs": 5,
                "inactive_programs": 1,
                "program_document_counts": {
                    "Youth Development": 45,
                    "Early Childhood": 32,
                    "Family Support": 28,
                    "Education": 67,
                    "Health": 23,
                    "General": 15
                },
                "most_used_program": "Education",
                "least_used_program": "General"
            }
        }
