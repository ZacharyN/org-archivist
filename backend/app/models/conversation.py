"""
Conversation-related Pydantic models for Phase 5 context persistence
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SessionMetadata(BaseModel):
    """
    Session metadata tracking conversation activity
    """
    started_at: datetime = Field(
        ...,
        description="Timestamp when conversation session started"
    )
    last_active: datetime = Field(
        ...,
        description="Timestamp of last activity in the conversation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "started_at": "2024-11-03T09:00:00Z",
                "last_active": "2024-11-03T10:30:00Z"
            }
        }


class ArtifactVersion(BaseModel):
    """
    Version of a generated artifact (text output) within a conversation
    """
    artifact_id: str = Field(
        ...,
        description="Unique identifier for the artifact"
    )
    version: int = Field(
        ...,
        ge=1,
        description="Version number (1-indexed)"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when this version was created"
    )
    content: str = Field(
        ...,
        description="The generated text content"
    )
    word_count: int = Field(
        ...,
        ge=0,
        description="Word count of the content"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the artifact"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "artifact_id": "art-550e8400-e29b-41d4-a716-446655440000",
                "version": 1,
                "created_at": "2024-11-03T10:30:00Z",
                "content": "Our organization has demonstrated strong capacity through...",
                "word_count": 850,
                "metadata": {
                    "prompt": "Write organizational capacity section",
                    "model": "claude-sonnet-4"
                }
            }
        }


class DocumentFilters(BaseModel):
    """
    Document filters for context-aware retrieval
    """
    doc_types: Optional[List[str]] = Field(
        None,
        description="Filter by document types (Grant Proposal, Annual Report, etc.)"
    )
    years: Optional[List[int]] = Field(
        None,
        description="Filter by years"
    )
    programs: Optional[List[str]] = Field(
        None,
        description="Filter by programs (Early Childhood, Youth Development, etc.)"
    )
    outcome: Optional[str] = Field(
        None,
        description="Filter by outcome status (Funded, Not Funded, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "doc_types": ["Grant Proposal", "Annual Report"],
                "years": [2023, 2024],
                "programs": ["Early Childhood"],
                "outcome": "Funded"
            }
        }


class ConversationContext(BaseModel):
    """
    Complete conversation context state for persistence
    """
    writing_style_id: Optional[str] = Field(
        None,
        description="ID of the writing style being used"
    )
    audience: Optional[str] = Field(
        None,
        description="Target audience (Federal RFP, Foundation Grant, etc.)"
    )
    section: Optional[str] = Field(
        None,
        description="Current section being worked on"
    )
    tone: Optional[str] = Field(
        None,
        description="Desired tone (formal, warm, conversational, etc.)"
    )
    filters: Optional[DocumentFilters] = Field(
        None,
        description="Document filters for context-aware retrieval"
    )
    artifacts: List[ArtifactVersion] = Field(
        default_factory=list,
        description="History of generated artifacts with versions"
    )
    last_query: Optional[str] = Field(
        None,
        description="Last user query/request in the conversation"
    )
    session_metadata: Optional[SessionMetadata] = Field(
        None,
        description="Session tracking metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "writing_style_id": "style-550e8400-e29b-41d4-a716-446655440000",
                "audience": "Federal RFP",
                "section": "Organizational Capacity",
                "tone": "formal",
                "filters": {
                    "doc_types": ["Grant Proposal", "Annual Report"],
                    "years": [2023, 2024],
                    "programs": ["Early Childhood"],
                    "outcome": "Funded"
                },
                "artifacts": [
                    {
                        "artifact_id": "art-550e8400-e29b-41d4-a716-446655440000",
                        "version": 1,
                        "created_at": "2024-11-03T10:30:00Z",
                        "content": "Generated text...",
                        "word_count": 850,
                        "metadata": {}
                    }
                ],
                "last_query": "Write organizational capacity section",
                "session_metadata": {
                    "started_at": "2024-11-03T09:00:00Z",
                    "last_active": "2024-11-03T10:35:00Z"
                }
            }
        }


class ConversationContextResponse(BaseModel):
    """
    Response model for conversation context retrieval
    """
    conversation_id: str = Field(
        ...,
        description="Unique conversation identifier"
    )
    context: ConversationContext = Field(
        ...,
        description="The conversation context state"
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when context was last updated"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv-550e8400-e29b-41d4-a716-446655440000",
                "context": {
                    "writing_style_id": "style-550e8400-e29b-41d4-a716-446655440000",
                    "audience": "Federal RFP",
                    "section": "Organizational Capacity",
                    "tone": "formal",
                    "filters": {
                        "doc_types": ["Grant Proposal"],
                        "years": [2024]
                    },
                    "artifacts": [],
                    "last_query": "Write organizational capacity section",
                    "session_metadata": {
                        "started_at": "2024-11-03T09:00:00Z",
                        "last_active": "2024-11-03T10:35:00Z"
                    }
                },
                "updated_at": "2024-11-03T10:35:00Z"
            }
        }
