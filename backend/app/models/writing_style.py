"""
Writing Style related Pydantic models

Models for writing style analysis, creation, and management
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class WritingStyleType(str):
    """Valid writing style types"""
    GRANT = "grant"
    PROPOSAL = "proposal"
    REPORT = "report"
    GENERAL = "general"


class StyleAnalysisRequest(BaseModel):
    """
    Request model for analyzing writing samples to create style prompt
    """
    samples: List[str] = Field(
        ...,
        min_length=3,
        max_length=7,
        description="Writing samples to analyze (3-7 samples)"
    )
    style_type: str = Field(
        default="general",
        description="Type of writing style (grant, proposal, report, general)"
    )
    style_name: Optional[str] = Field(
        None,
        description="Optional name for the writing style"
    )

    @field_validator('samples')
    @classmethod
    def validate_samples(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one sample is required")
        if len(v) < 3:
            raise ValueError("Minimum 3 samples required")
        if len(v) > 7:
            raise ValueError("Maximum 7 samples allowed")

        # Check each sample has minimum words
        for i, sample in enumerate(v, 1):
            word_count = len(sample.split())
            if word_count < 200:
                raise ValueError(
                    f"Sample {i} has {word_count} words, minimum 200 required"
                )

        return v

    @field_validator('style_type')
    @classmethod
    def validate_style_type(cls, v: str) -> str:
        allowed = ['grant', 'proposal', 'report', 'general']
        if v.lower() not in allowed:
            raise ValueError(f"style_type must be one of: {', '.join(allowed)}")
        return v.lower()


class StyleAnalysisResponse(BaseModel):
    """
    Response model for style analysis
    """
    success: bool = Field(..., description="Whether analysis succeeded")
    style_prompt: Optional[str] = Field(None, description="Generated style prompt")
    style_name: Optional[str] = Field(None, description="Name of the style")
    style_type: Optional[str] = Field(None, description="Type of style")
    analysis_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadata about style elements analyzed"
    )
    sample_stats: Optional[Dict[str, Any]] = Field(
        None,
        description="Statistics about the analyzed samples"
    )
    word_count: Optional[int] = Field(None, description="Word count of generated prompt")
    generation_time: Optional[float] = Field(None, description="Time taken in seconds")
    tokens_used: Optional[int] = Field(None, description="Total tokens used")
    model: Optional[str] = Field(None, description="Model used for analysis")
    warnings: List[str] = Field(default_factory=list, description="Any warnings")
    errors: List[str] = Field(default_factory=list, description="Any errors")


class StyleRefinementRequest(BaseModel):
    """
    Request model for refining an existing style prompt
    """
    original_prompt: str = Field(..., min_length=100, description="Original style prompt")
    operation: str = Field(
        ...,
        description="Refinement operation (make_concise, make_specific, add_examples, emphasize_aspect)"
    )
    aspect: Optional[str] = Field(
        None,
        description="Specific aspect to emphasize (required for emphasize_aspect operation)"
    )
    custom_instructions: Optional[str] = Field(
        None,
        description="Additional custom refinement instructions"
    )

    @field_validator('operation')
    @classmethod
    def validate_operation(cls, v: str) -> str:
        allowed = ['make_concise', 'make_specific', 'add_examples', 'emphasize_aspect']
        if v not in allowed:
            raise ValueError(f"operation must be one of: {', '.join(allowed)}")
        return v


class StyleRefinementResponse(BaseModel):
    """
    Response model for style refinement
    """
    success: bool = Field(..., description="Whether refinement succeeded")
    refined_prompt: Optional[str] = Field(None, description="Refined style prompt")
    original_word_count: Optional[int] = Field(None, description="Original prompt word count")
    refined_word_count: Optional[int] = Field(None, description="Refined prompt word count")
    operation: Optional[str] = Field(None, description="Operation performed")
    aspect: Optional[str] = Field(None, description="Aspect that was emphasized")
    generation_time: Optional[float] = Field(None, description="Time taken in seconds")
    tokens_used: Optional[int] = Field(None, description="Total tokens used")
    model: Optional[str] = Field(None, description="Model used")
    errors: List[str] = Field(default_factory=list, description="Any errors")


class WritingStyle(BaseModel):
    """
    Writing style model (for database storage and retrieval)
    """
    style_id: Optional[str] = Field(None, description="Style ID (UUID)")
    name: str = Field(..., min_length=1, max_length=100, description="Style name")
    type: str = Field(
        ...,
        description="Style type (grant, proposal, report, general)"
    )
    description: Optional[str] = Field(None, description="Style description")
    prompt_content: str = Field(
        ...,
        min_length=100,
        description="The actual style prompt content"
    )
    samples: Optional[List[str]] = Field(
        default_factory=list,
        description="Original writing samples used"
    )
    analysis_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Analysis metadata (style elements analyzed)"
    )
    sample_count: int = Field(default=0, description="Number of samples used")
    active: bool = Field(default=True, description="Whether style is active")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="User ID who created it")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = ['grant', 'proposal', 'report', 'general']
        if v.lower() not in allowed:
            raise ValueError(f"type must be one of: {', '.join(allowed)}")
        return v.lower()


class WritingStyleCreateRequest(BaseModel):
    """
    Request model for creating a new writing style
    """
    name: str = Field(..., min_length=1, max_length=100, description="Style name")
    type: str = Field(..., description="Style type")
    description: Optional[str] = Field(None, description="Style description")
    prompt_content: str = Field(..., min_length=100, description="Style prompt content")
    samples: Optional[List[str]] = Field(default_factory=list, description="Writing samples")
    analysis_metadata: Optional[Dict[str, Any]] = Field(None, description="Analysis metadata")


class WritingStyleUpdateRequest(BaseModel):
    """
    Request model for updating a writing style
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Updated name")
    description: Optional[str] = Field(None, description="Updated description")
    prompt_content: Optional[str] = Field(None, min_length=100, description="Updated prompt")
    active: Optional[bool] = Field(None, description="Active status")


class WritingStyleListResponse(BaseModel):
    """
    Response model for listing writing styles
    """
    styles: List[WritingStyle] = Field(..., description="List of writing styles")
    total: int = Field(..., description="Total count")
    active_count: int = Field(..., description="Number of active styles")


class WritingStyleResponse(BaseModel):
    """
    Response model for single writing style
    """
    style: WritingStyle = Field(..., description="Writing style")
    success: bool = Field(True, description="Operation success")
    message: str = Field(..., description="Status message")


class StyleMetricsRequest(BaseModel):
    """
    Request model for calculating style metrics on text
    """
    text: str = Field(..., min_length=1, description="Text to analyze")


class StyleMetricsResponse(BaseModel):
    """
    Response model for style metrics
    """
    word_count: int = Field(..., description="Total word count")
    sentence_count: int = Field(..., description="Estimated sentence count")
    avg_sentence_length: float = Field(..., description="Average words per sentence")
    paragraph_count: int = Field(..., description="Number of paragraphs")
