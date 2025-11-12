"""
Output related Pydantic models

Models for generated grant content outputs with success tracking
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from .common import PaginationMetadata


class OutputType(str, Enum):
    """Valid output types"""
    GRANT_PROPOSAL = "grant_proposal"
    BUDGET_NARRATIVE = "budget_narrative"
    PROGRAM_DESCRIPTION = "program_description"
    IMPACT_SUMMARY = "impact_summary"
    OTHER = "other"


class OutputStatus(str, Enum):
    """Valid output statuses"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PENDING = "pending"
    AWARDED = "awarded"
    NOT_AWARDED = "not_awarded"


class OutputBase(BaseModel):
    """
    Base output model with common fields
    """
    output_type: OutputType = Field(..., description="Type of output")
    title: str = Field(..., min_length=1, max_length=500, description="Output title")
    content: str = Field(..., min_length=1, description="Output content")
    word_count: Optional[int] = Field(None, description="Word count of content")
    status: OutputStatus = Field(default=OutputStatus.DRAFT, description="Output status")
    writing_style_id: Optional[str] = Field(None, description="Writing style ID (UUID)")
    funder_name: Optional[str] = Field(None, max_length=255, description="Name of funder")
    requested_amount: Optional[Decimal] = Field(None, ge=0, description="Requested grant amount")
    awarded_amount: Optional[Decimal] = Field(None, ge=0, description="Awarded grant amount")
    submission_date: Optional[date] = Field(None, description="Date submitted to funder")
    decision_date: Optional[date] = Field(None, description="Date decision received")
    success_notes: Optional[str] = Field(None, description="Notes about grant success/failure")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata (sources, confidence, etc.)")

    @field_validator('decision_date')
    @classmethod
    def validate_decision_date(cls, v: Optional[date], info) -> Optional[date]:
        """Validate that decision_date is not before submission_date"""
        if v is not None and 'submission_date' in info.data:
            submission_date = info.data.get('submission_date')
            if submission_date and v < submission_date:
                raise ValueError("decision_date cannot be before submission_date")
        return v

    @field_validator('awarded_amount')
    @classmethod
    def validate_awarded_amount(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        """Validate that awarded_amount doesn't exceed requested_amount"""
        if v is not None and 'requested_amount' in info.data:
            requested_amount = info.data.get('requested_amount')
            if requested_amount and v > requested_amount:
                raise ValueError("awarded_amount cannot exceed requested_amount")
        return v


class OutputCreateRequest(OutputBase):
    """
    Request model for creating a new output (POST /api/outputs)
    """
    conversation_id: Optional[str] = Field(None, description="Associated conversation ID (UUID)")


class OutputUpdateRequest(BaseModel):
    """
    Request model for updating an output (PUT /api/outputs/{id})
    All fields are optional for partial updates
    """
    output_type: Optional[OutputType] = Field(None, description="Type of output")
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="Output title")
    content: Optional[str] = Field(None, min_length=1, description="Output content")
    word_count: Optional[int] = Field(None, description="Word count of content")
    status: Optional[OutputStatus] = Field(None, description="Output status")
    writing_style_id: Optional[str] = Field(None, description="Writing style ID (UUID)")
    funder_name: Optional[str] = Field(None, max_length=255, description="Name of funder")
    requested_amount: Optional[Decimal] = Field(None, ge=0, description="Requested grant amount")
    awarded_amount: Optional[Decimal] = Field(None, ge=0, description="Awarded grant amount")
    submission_date: Optional[date] = Field(None, description="Date submitted to funder")
    decision_date: Optional[date] = Field(None, description="Date decision received")
    success_notes: Optional[str] = Field(None, description="Notes about grant success/failure")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator('decision_date')
    @classmethod
    def validate_decision_date(cls, v: Optional[date], info) -> Optional[date]:
        """Validate that decision_date is not before submission_date"""
        if v is not None and 'submission_date' in info.data:
            submission_date = info.data.get('submission_date')
            if submission_date and v < submission_date:
                raise ValueError("decision_date cannot be before submission_date")
        return v

    @field_validator('awarded_amount')
    @classmethod
    def validate_awarded_amount(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        """Validate that awarded_amount doesn't exceed requested_amount"""
        if v is not None and 'requested_amount' in info.data:
            requested_amount = info.data.get('requested_amount')
            if requested_amount and v > requested_amount:
                raise ValueError("awarded_amount cannot exceed requested_amount")
        return v


class OutputResponse(OutputBase):
    """
    Response model for output API responses
    Includes all fields from OutputBase plus ID and timestamps
    """
    output_id: str = Field(..., description="Output ID (UUID)")
    conversation_id: Optional[str] = Field(None, description="Associated conversation ID (UUID)")
    created_by: Optional[str] = Field(None, description="User who created the output")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class OutputListResponse(BaseModel):
    """
    Response model for listing outputs (GET /api/outputs)

    Includes comprehensive pagination metadata to simplify frontend pagination logic.
    """
    outputs: List[OutputResponse] = Field(..., description="List of outputs")
    pagination: PaginationMetadata = Field(..., description="Pagination metadata")


class OutputStatsResponse(BaseModel):
    """
    Response model for output statistics (GET /api/outputs/stats)
    """
    total_outputs: int = Field(..., description="Total number of outputs")
    by_type: Dict[str, int] = Field(..., description="Count by output type")
    by_status: Dict[str, int] = Field(..., description="Count by status")
    success_rate: float = Field(..., description="Success rate (awarded / submitted)")
    total_requested: Decimal = Field(..., description="Total amount requested")
    total_awarded: Decimal = Field(..., description="Total amount awarded")
    avg_requested: Optional[Decimal] = Field(None, description="Average requested amount")
    avg_awarded: Optional[Decimal] = Field(None, description="Average awarded amount")
