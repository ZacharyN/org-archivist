"""
Audit logging Pydantic models for Phase 5 compliance and security tracking
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuditLogQuery(BaseModel):
    """
    Query parameters for audit log retrieval
    """
    user_id: Optional[str] = Field(
        None,
        description="Filter by user ID"
    )
    event_type: Optional[str] = Field(
        None,
        description="Filter by event type (e.g., 'document.upload', 'output.create')"
    )
    entity_type: Optional[str] = Field(
        None,
        description="Filter by entity type (e.g., 'document', 'output', 'user')"
    )
    start_date: Optional[datetime] = Field(
        None,
        description="Filter logs after this timestamp"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Filter logs before this timestamp"
    )
    page: int = Field(
        1,
        ge=1,
        description="Page number for pagination"
    )
    per_page: int = Field(
        50,
        ge=1,
        le=100,
        description="Number of results per page (max 100)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user-550e8400-e29b-41d4-a716-446655440000",
                "event_type": "document.upload",
                "entity_type": "document",
                "start_date": "2024-11-01T00:00:00Z",
                "end_date": "2024-11-30T23:59:59Z",
                "page": 1,
                "per_page": 50
            }
        }


class AuditLogResponse(BaseModel):
    """
    Response model for individual audit log entry
    """
    log_id: str = Field(
        ...,
        description="Unique audit log entry identifier"
    )
    event_type: str = Field(
        ...,
        description="Type of event (e.g., 'document.upload', 'output.create')"
    )
    entity_type: str = Field(
        ...,
        description="Type of entity affected (e.g., 'document', 'output')"
    )
    entity_id: Optional[str] = Field(
        None,
        description="ID of the affected entity"
    )
    user_id: Optional[str] = Field(
        None,
        description="ID of the user who performed the action"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the action"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the event occurred"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "log_id": "log-550e8400-e29b-41d4-a716-446655440000",
                "event_type": "document.upload",
                "entity_type": "document",
                "entity_id": "doc-550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user-550e8400-e29b-41d4-a716-446655440000",
                "details": {
                    "ip_address": "192.168.1.100",
                    "user_agent": "Mozilla/5.0...",
                    "method": "POST",
                    "path": "/api/documents/upload",
                    "status_code": 200,
                    "filename": "annual_report_2024.pdf",
                    "file_size": 2457600,
                    "sensitivity_confirmed": True
                },
                "created_at": "2024-11-03T10:30:00Z"
            }
        }


class PaginatedAuditLogResponse(BaseModel):
    """
    Paginated response for audit log queries
    """
    logs: List[AuditLogResponse] = Field(
        ...,
        description="List of audit log entries for current page"
    )
    total_count: int = Field(
        ...,
        ge=0,
        description="Total number of matching log entries"
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number"
    )
    per_page: int = Field(
        ...,
        ge=1,
        le=100,
        description="Number of results per page"
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "logs": [
                    {
                        "log_id": "log-550e8400-e29b-41d4-a716-446655440000",
                        "event_type": "document.upload",
                        "entity_type": "document",
                        "entity_id": "doc-550e8400-e29b-41d4-a716-446655440000",
                        "user_id": "user-550e8400-e29b-41d4-a716-446655440000",
                        "details": {
                            "ip_address": "192.168.1.100",
                            "filename": "annual_report_2024.pdf"
                        },
                        "created_at": "2024-11-03T10:30:00Z"
                    }
                ],
                "total_count": 152,
                "page": 1,
                "per_page": 50,
                "total_pages": 4
            }
        }


class AuditEventTypes:
    """
    Constants for audit event types
    """
    # Document events
    DOCUMENT_UPLOAD = "document.upload"
    DOCUMENT_DELETE = "document.delete"

    # Output events
    OUTPUT_CREATE = "output.create"
    OUTPUT_UPDATE = "output.update"
    OUTPUT_DELETE = "output.delete"

    # Success tracking events
    SUCCESS_TRACKING_UPDATE = "success_tracking.update"

    # Writing style events
    WRITING_STYLE_CREATE = "writing_style.create"
    WRITING_STYLE_UPDATE = "writing_style.update"
    WRITING_STYLE_DELETE = "writing_style.delete"

    # User events
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_ROLE_CHANGE = "user.role_change"

    # Conversation events
    CONVERSATION_CREATE = "conversation.create"
    CONVERSATION_DELETE = "conversation.delete"


class AuditEntityTypes:
    """
    Constants for audit entity types
    """
    DOCUMENT = "document"
    OUTPUT = "output"
    SUCCESS_TRACKING = "success_tracking"
    WRITING_STYLE = "writing_style"
    USER = "user"
    CONVERSATION = "conversation"
