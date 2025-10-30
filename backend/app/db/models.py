"""
SQLAlchemy models for Org Archivist database

These models define the database schema for use with Alembic migrations.
They reflect the current state of the database as defined in docker/postgres/init/01-init-database.sql
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UUID,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    EDITOR = "editor"
    WRITER = "writer"


class Document(Base):
    """Documents table - stores metadata for all uploaded documents"""

    __tablename__ = "documents"

    doc_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    filename = Column(String(255), nullable=False)
    doc_type = Column(String(50), nullable=False)
    year = Column(Integer)
    outcome = Column(String(50))
    notes = Column(Text)
    upload_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    file_size = Column(Integer)
    chunks_count = Column(Integer, default=0)
    created_by = Column(String(100))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    programs = relationship("DocumentProgram", back_populates="document", cascade="all, delete-orphan")
    tags = relationship("DocumentTag", back_populates="document", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "year >= 2000 AND year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1",
            name="valid_year"
        ),
        CheckConstraint(
            "doc_type IN ('Grant Proposal', 'Annual Report', 'Program Description', 'Impact Report', 'Strategic Plan', 'Other')",
            name="valid_doc_type"
        ),
        CheckConstraint(
            "outcome IN ('N/A', 'Funded', 'Not Funded', 'Pending', 'Final Report')",
            name="valid_outcome"
        ),
        Index("idx_documents_filename", "filename"),
        Index("idx_documents_doc_type", "doc_type"),
        Index("idx_documents_year", "year"),
        Index("idx_documents_upload_date", "upload_date"),
    )


class DocumentProgram(Base):
    """Document Programs junction table - associates documents with programs"""

    __tablename__ = "document_programs"

    doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.doc_id", ondelete="CASCADE"), primary_key=True)
    program = Column(String(100), nullable=False, primary_key=True)

    # Relationship
    document = relationship("Document", back_populates="programs")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "program IN ('Early Childhood', 'Youth Development', 'Family Support', 'Education', 'Health', 'General')",
            name="valid_program"
        ),
        Index("idx_document_programs_program", "program"),
    )


class DocumentTag(Base):
    """Document Tags junction table - associates documents with tags"""

    __tablename__ = "document_tags"

    doc_id = Column(UUID(as_uuid=True), ForeignKey("documents.doc_id", ondelete="CASCADE"), primary_key=True)
    tag = Column(String(100), nullable=False, primary_key=True)

    # Relationship
    document = relationship("Document", back_populates="tags")

    __table_args__ = (
        Index("idx_document_tags_tag", "tag"),
    )


class PromptTemplate(Base):
    """Prompt Templates table - stores reusable prompt templates"""

    __tablename__ = "prompt_templates"

    prompt_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    variables = Column(JSONB)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(Integer, default=1)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "category IN ('Brand Voice', 'Audience-Specific', 'Section-Specific', 'General')",
            name="valid_category"
        ),
        Index("idx_prompt_templates_category", "category"),
        Index("idx_prompt_templates_active", "active"),
    )


class Conversation(Base):
    """Conversations table - stores conversation sessions"""

    __tablename__ = "conversations"

    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(String(100))
    conversation_metadata = Column("metadata", JSONB)  # Renamed in model, maps to 'metadata' column

    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_conversations_user_id", "user_id"),
        Index("idx_conversations_updated_at", "updated_at"),
    )


class Message(Base):
    """Messages table - stores individual messages within conversations"""

    __tablename__ = "messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(JSONB)
    message_metadata = Column("metadata", JSONB)  # Renamed in model, maps to 'metadata' column
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    conversation = relationship("Conversation", back_populates="messages")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="valid_role"
        ),
        Index("idx_messages_conversation_id", "conversation_id"),
        Index("idx_messages_created_at", "created_at"),
    )


class SystemConfig(Base):
    """System Configuration table - stores system-wide settings"""

    __tablename__ = "system_config"

    key = Column(String(100), primary_key=True)
    value = Column(JSONB, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """Audit Log table - tracks important system events"""

    __tablename__ = "audit_log"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type = Column(String(50), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    user_id = Column(String(100))
    details = Column(JSONB)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_audit_log_event_type", "event_type"),
        Index("idx_audit_log_entity_type", "entity_type"),
        Index("idx_audit_log_created_at", "created_at"),
    )


class User(Base):
    """Users table - stores user accounts for authentication"""

    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.WRITER)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_is_active", "is_active"),
    )


class UserSession(Base):
    """User Sessions table - tracks active user sessions"""

    __tablename__ = "user_sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    access_token = Column(String(500), nullable=False)
    refresh_token = Column(String(500))
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ip_address = Column(String(45))  # Supports IPv6
    user_agent = Column(Text)

    # Relationship
    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index("idx_user_sessions_user_id", "user_id"),
        Index("idx_user_sessions_access_token", "access_token"),
        Index("idx_user_sessions_expires_at", "expires_at"),
    )


class WritingStyle(Base):
    """Writing Styles table - stores AI-generated writing style prompts"""

    __tablename__ = "writing_styles"

    style_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False, unique=True)
    type = Column(String(50), nullable=False)
    description = Column(Text)
    prompt_content = Column(Text, nullable=False)
    samples = Column(JSONB)  # Array of original writing samples
    analysis_metadata = Column(JSONB)  # AI analysis results (style elements analyzed)
    sample_count = Column(Integer, default=0)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "type IN ('grant', 'proposal', 'report', 'general')",
            name="valid_style_type"
        ),
        Index("idx_writing_styles_type", "type"),
        Index("idx_writing_styles_active", "active"),
        Index("idx_writing_styles_created_by", "created_by"),
    )
