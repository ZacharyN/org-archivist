"""
Pydantic models for request/response validation
"""

from .common import HealthCheckResponse, ErrorResponse, SuccessResponse
from .document import (
    DocumentMetadata,
    DocumentSensitivityCheck,
    DocumentUploadRequest,
    DocumentUploadResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentFilters,
    DocumentStats,
)
from .conversation import (
    SessionMetadata,
    ArtifactVersion,
    ConversationContext,
    ConversationContextResponse,
)
from .audit import (
    AuditLogQuery,
    AuditLogResponse,
    PaginatedAuditLogResponse,
    AuditEventTypes,
    AuditEntityTypes,
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
from .writing_style import (
    WritingStyleType,
    StyleAnalysisRequest,
    StyleAnalysisResponse,
    StyleRefinementRequest,
    StyleRefinementResponse,
    WritingStyle,
    WritingStyleCreateRequest,
    WritingStyleUpdateRequest,
    WritingStyleListResponse,
    WritingStyleResponse,
    StyleMetricsRequest,
    StyleMetricsResponse,
)

__all__ = [
    # Common
    "HealthCheckResponse",
    "ErrorResponse",
    "SuccessResponse",
    # Document
    "DocumentMetadata",
    "DocumentSensitivityCheck",
    "DocumentUploadRequest",
    "DocumentUploadResponse",
    "DocumentInfo",
    "DocumentListResponse",
    "DocumentFilters",
    "DocumentStats",
    # Conversation (Phase 5)
    "SessionMetadata",
    "ArtifactVersion",
    "ConversationContext",
    "ConversationContextResponse",
    # Audit (Phase 5)
    "AuditLogQuery",
    "AuditLogResponse",
    "PaginatedAuditLogResponse",
    "AuditEventTypes",
    "AuditEntityTypes",
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
    # Writing Style
    "WritingStyleType",
    "StyleAnalysisRequest",
    "StyleAnalysisResponse",
    "StyleRefinementRequest",
    "StyleRefinementResponse",
    "WritingStyle",
    "WritingStyleCreateRequest",
    "WritingStyleUpdateRequest",
    "WritingStyleListResponse",
    "WritingStyleResponse",
    "StyleMetricsRequest",
    "StyleMetricsResponse",
]
