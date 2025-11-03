"""
Query and generation-related Pydantic models
"""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

from .document import DocumentFilters


class QueryRequest(BaseModel):
    """
    Request model for content generation query
    """
    query: str = Field(
        ...,
        min_length=10,
        description="User's content generation request"
    )
    audience: str = Field(
        ...,
        description="Target audience (Federal RFP, Foundation Grant, etc.)"
    )
    section: str = Field(
        ...,
        description="Document section (Organizational Capacity, Program Description, etc.)"
    )
    tone: str = Field(
        default="Professional",
        description="Tone/formality level"
    )
    max_sources: int = Field(
        default=5,
        ge=1,
        le=15,
        description="Maximum number of source documents to retrieve"
    )
    recency_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Weight for recent documents (0=no bias, 1=strong bias)"
    )
    include_citations: bool = Field(
        default=True,
        description="Include inline citations in response"
    )
    filters: Optional[DocumentFilters] = Field(
        None,
        description="Document filters for retrieval"
    )
    custom_instructions: Optional[str] = Field(
        None,
        description="Additional custom instructions for generation"
    )
    max_tokens: int = Field(
        default=4096,
        ge=512,
        le=8192,
        description="Maximum tokens for response"
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Generation temperature"
    )

    @field_validator('audience')
    @classmethod
    def validate_audience(cls, v: str) -> str:
        allowed = ["Federal RFP", "Foundation Grant", "Corporate Sponsor",
                   "Individual Donor", "General Public"]
        if v not in allowed:
            raise ValueError(f"audience must be one of: {', '.join(allowed)}")
        return v

    @field_validator('section')
    @classmethod
    def validate_section(cls, v: str) -> str:
        allowed = ["Organizational Capacity", "Program Description",
                   "Impact & Outcomes", "Budget Narrative",
                   "Sustainability Plan", "Evaluation Plan"]
        if v not in allowed:
            raise ValueError(f"section must be one of: {', '.join(allowed)}")
        return v


class Source(BaseModel):
    """
    Source document information for citations
    """
    id: int = Field(..., description="Source citation number")
    filename: str = Field(..., description="Source document filename")
    doc_type: str = Field(..., description="Document type")
    year: Optional[int] = Field(None, description="Document year")
    excerpt: str = Field(..., description="Text excerpt from source")
    relevance: float = Field(..., description="Relevance score (0-1)")
    chunk_index: Optional[int] = Field(None, description="Chunk index in document")


class ResponseMetadata(BaseModel):
    """
    Metadata about the generated response
    """
    model: str = Field(..., description="LLM model used")
    tokens_used: int = Field(..., description="Total tokens used")
    generation_time: float = Field(..., description="Generation time in seconds")
    temperature: float = Field(..., description="Temperature used")


class QualityIssue(BaseModel):
    """
    Quality validation issue
    """
    severity: str = Field(..., description="Issue severity (info, warning, error)")
    message: str = Field(..., description="Issue description")

    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in ['info', 'warning', 'error']:
            raise ValueError("severity must be one of: info, warning, error")
        return v


class ValidationResult(BaseModel):
    """
    Quality validation results
    """
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    groundedness: float = Field(..., ge=0.0, le=1.0, description="Source grounding score")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Query relevance score")
    issues: List[QualityIssue] = Field(default_factory=list, description="Quality issues found")
    needs_review: bool = Field(..., description="Whether response needs manual review")


class QueryResponse(BaseModel):
    """
    Response model for content generation
    """
    text: str = Field(..., description="Generated content")
    sources: List[Source] = Field(..., description="Source documents used")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    quality_issues: List[str] = Field(default_factory=list, description="Quality warnings")
    metadata: ResponseMetadata = Field(..., description="Response metadata")
    validation: Optional[ValidationResult] = Field(None, description="Quality validation results")


class ChatMessage(BaseModel):
    """
    Chat message in a conversation
    """
    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    sources: Optional[List[Source]] = Field(None, description="Sources (for assistant messages)")
    timestamp: Optional[str] = Field(None, description="Message timestamp")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ['user', 'assistant']:
            raise ValueError("role must be 'user' or 'assistant'")
        return v


class ChatRequest(BaseModel):
    """
    Request model for chat endpoint
    """
    message: str = Field(..., min_length=1, description="User message")
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation ID (UUID) - if None, creates new conversation"
    )
    conversation_history: List[ChatMessage] = Field(
        default_factory=list,
        description="Previous conversation messages"
    )
    context_window: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of previous messages to include in context"
    )
    parameters: Optional[QueryRequest] = Field(
        None,
        description="Query parameters if RAG is needed"
    )


class ChatResponse(BaseModel):
    """
    Response model for chat endpoint
    """
    message: str = Field(..., description="Assistant's response message text")
    sources: List[Source] = Field(default_factory=list, description="Source documents used (if RAG)")
    conversation_id: str = Field(..., description="Conversation ID (UUID)")
    message_count: int = Field(..., description="Total messages in conversation")
    requires_rag: bool = Field(..., description="Whether RAG was used for this response")
    metadata: dict = Field(default_factory=dict, description="Response metadata (model, tokens, etc.)")
