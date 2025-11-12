"""
Common Pydantic models shared across the application
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
    checks: dict = Field(default_factory=dict, description="Individual component health checks")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[dict] = Field(None, description="Response data")


class PaginationMetadata(BaseModel):
    """
    Pagination metadata for list responses

    Provides comprehensive pagination information to simplify frontend pagination logic.
    """
    total: int = Field(..., description="Total number of items (unfiltered)")
    page: int = Field(..., description="Current page number (1-indexed)")
    per_page: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")

    @staticmethod
    def calculate(total: int, skip: int, limit: int) -> "PaginationMetadata":
        """
        Calculate pagination metadata from total count and pagination parameters

        Args:
            total: Total number of items
            skip: Number of items to skip (offset)
            limit: Maximum number of items per page

        Returns:
            PaginationMetadata with all fields calculated
        """
        import math

        # Handle edge cases
        if limit <= 0:
            limit = 1
        if skip < 0:
            skip = 0

        # Calculate pagination values
        total_pages = math.ceil(total / limit) if total > 0 else 1
        current_page = (skip // limit) + 1
        has_next = (skip + limit) < total
        has_previous = skip > 0

        return PaginationMetadata(
            total=total,
            page=current_page,
            per_page=limit,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )
