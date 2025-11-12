"""
Document-related Pydantic models
"""
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

from .common import PaginationMetadata


class DocumentMetadata(BaseModel):
    """
    Metadata for uploaded documents
    """
    doc_type: str = Field(
        ...,
        description="Document type (Grant Proposal, Annual Report, Program Description, etc.)"
    )
    year: int = Field(
        ...,
        ge=2000,
        le=2030,
        description="Document year"
    )
    programs: List[str] = Field(
        default_factory=list,
        description="Related programs (Early Childhood, Youth Development, etc.)"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Custom tags for categorization"
    )
    outcome: str = Field(
        default="N/A",
        description="Outcome status (N/A, Funded, Not Funded, Pending, Final Report)"
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes about the document"
    )

    @field_validator('doc_type')
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        allowed_types = [
            "Grant Proposal",
            "Annual Report",
            "Program Description",
            "Impact Report",
            "Strategic Plan",
            "Other"
        ]
        if v not in allowed_types:
            raise ValueError(f"doc_type must be one of: {', '.join(allowed_types)}")
        return v

    @field_validator('outcome')
    @classmethod
    def validate_outcome(cls, v: str) -> str:
        allowed_outcomes = ["N/A", "Funded", "Not Funded", "Pending", "Final Report"]
        if v not in allowed_outcomes:
            raise ValueError(f"outcome must be one of: {', '.join(allowed_outcomes)}")
        return v


class DocumentSensitivityCheck(BaseModel):
    """
    Document sensitivity metadata for Phase 5 security validation
    """
    is_sensitive: bool = Field(
        False,
        description="Whether the document contains sensitive information"
    )
    sensitivity_level: Optional[Literal["low", "medium", "high"]] = Field(
        None,
        description="Sensitivity classification level"
    )
    sensitivity_notes: Optional[str] = Field(
        None,
        description="Additional notes about document sensitivity"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "is_sensitive": False,
                "sensitivity_level": "low",
                "sensitivity_notes": "Public-facing annual report"
            }
        }


class DocumentUploadRequest(BaseModel):
    """
    Request model for document upload
    Note: File is handled separately via FastAPI's UploadFile
    """
    metadata: DocumentMetadata = Field(
        ...,
        description="Document metadata"
    )
    sensitivity_confirmed: bool = Field(
        ...,
        description="Confirmation that document sensitivity has been reviewed and is appropriate for upload"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "doc_type": "Grant Proposal",
                    "year": 2024,
                    "programs": ["Early Childhood"],
                    "tags": ["federal", "education"],
                    "outcome": "Funded"
                },
                "sensitivity_confirmed": True
            }
        }


class DocumentUploadResponse(BaseModel):
    """
    Response model for document upload
    """
    success: bool = Field(..., description="Upload success status")
    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    chunks_created: int = Field(..., description="Number of chunks created")
    message: str = Field(..., description="Status message")


class DocumentInfo(BaseModel):
    """
    Document information for listing
    """
    doc_id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Filename")
    doc_type: str = Field(..., description="Document type")
    year: int = Field(..., description="Document year")
    programs: List[str] = Field(..., description="Related programs")
    tags: List[str] = Field(..., description="Tags")
    outcome: str = Field(..., description="Outcome status")
    chunks_count: int = Field(..., description="Number of chunks")
    upload_date: datetime = Field(..., description="Upload timestamp")
    file_size: Optional[int] = Field(None, description="File size in bytes")


class DocumentListResponse(BaseModel):
    """
    Response model for listing documents

    Includes comprehensive pagination metadata to simplify frontend pagination logic.
    """
    documents: List[DocumentInfo] = Field(..., description="List of documents")
    pagination: PaginationMetadata = Field(..., description="Pagination metadata")


class DocumentFilters(BaseModel):
    """
    Filters for document retrieval and search
    """
    doc_types: Optional[List[str]] = Field(None, description="Filter by document types")
    years: Optional[List[int]] = Field(None, description="Filter by years")
    programs: Optional[List[str]] = Field(None, description="Filter by programs")
    outcomes: Optional[List[str]] = Field(None, description="Filter by outcome status")
    exclude_docs: Optional[List[str]] = Field(None, description="Document IDs to exclude")
    date_range: Optional[tuple[int, int]] = Field(None, description="Year range (from, to)")


class DocumentStats(BaseModel):
    """
    Statistics about the document library
    """
    total_documents: int = Field(..., description="Total number of documents")
    total_chunks: int = Field(..., description="Total number of chunks")
    by_type: dict[str, int] = Field(..., description="Document count by type")
    by_year: dict[int, int] = Field(..., description="Document count by year")
    by_outcome: dict[str, int] = Field(..., description="Document count by outcome")
    avg_chunks_per_doc: float = Field(..., description="Average chunks per document")
