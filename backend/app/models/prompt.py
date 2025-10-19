"""
Prompt template-related Pydantic models
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class PromptTemplate(BaseModel):
    """
    Prompt template for content generation
    """
    id: Optional[str] = Field(None, description="Template ID (auto-generated)")
    name: str = Field(..., min_length=1, description="Template name")
    category: str = Field(..., description="Template category")
    content: str = Field(..., min_length=1, description="Prompt template content")
    variables: List[str] = Field(
        default_factory=list,
        description="Variables that can be substituted (e.g., {audience}, {query})"
    )
    active: bool = Field(default=True, description="Whether template is active")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    version: int = Field(default=1, description="Template version")

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        allowed = ['audience', 'section', 'brand_voice', 'custom']
        if v not in allowed:
            raise ValueError(f"category must be one of: {', '.join(allowed)}")
        return v


class PromptCreateRequest(BaseModel):
    """
    Request model for creating a prompt template
    """
    name: str = Field(..., min_length=1, description="Template name")
    category: str = Field(..., description="Template category")
    content: str = Field(..., min_length=1, description="Prompt content")
    variables: List[str] = Field(default_factory=list, description="Template variables")


class PromptUpdateRequest(BaseModel):
    """
    Request model for updating a prompt template
    """
    name: Optional[str] = Field(None, description="Updated name")
    content: Optional[str] = Field(None, description="Updated content")
    variables: Optional[List[str]] = Field(None, description="Updated variables")
    active: Optional[bool] = Field(None, description="Active status")


class PromptListResponse(BaseModel):
    """
    Response model for listing prompt templates
    """
    prompts: List[PromptTemplate] = Field(..., description="List of prompt templates")
    total: int = Field(..., description="Total count")


class PromptResponse(BaseModel):
    """
    Response model for single prompt template
    """
    prompt: PromptTemplate = Field(..., description="Prompt template")
    success: bool = Field(True, description="Operation success")
    message: str = Field(..., description="Status message")
