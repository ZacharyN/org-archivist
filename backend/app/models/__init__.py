"""
Pydantic models for request/response validation
"""

from .common import HealthCheckResponse, ErrorResponse, SuccessResponse
from .document import (
    DocumentMetadata,
    DocumentUploadRequest,
    DocumentUploadResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentFilters,
    DocumentStats,
)
from .query import (
    QueryRequest,
    QueryResponse,
    Source,
    ResponseMetadata,
    ValidationResult,
    QualityIssue,
    ChatMessage,
    ChatRequest,
    ChatResponse,
)
from .prompt import (
    PromptTemplate,
    PromptCreateRequest,
    PromptUpdateRequest,
    PromptListResponse,
    PromptResponse,
)
from .config import (
    LLMModelConfig,
    RAGConfig,
    UserPreferences,
    SystemConfiguration,
    ConfigUpdateRequest,
    ConfigResponse,
)

__all__ = [
    # Common
    "HealthCheckResponse",
    "ErrorResponse",
    "SuccessResponse",
    # Document
    "DocumentMetadata",
    "DocumentUploadRequest",
    "DocumentUploadResponse",
    "DocumentInfo",
    "DocumentListResponse",
    "DocumentFilters",
    "DocumentStats",
    # Query
    "QueryRequest",
    "QueryResponse",
    "Source",
    "ResponseMetadata",
    "ValidationResult",
    "QualityIssue",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    # Prompt
    "PromptTemplate",
    "PromptCreateRequest",
    "PromptUpdateRequest",
    "PromptListResponse",
    "PromptResponse",
    # Config
    "LLMModelConfig",
    "RAGConfig",
    "UserPreferences",
    "SystemConfiguration",
    "ConfigUpdateRequest",
    "ConfigResponse",
]
