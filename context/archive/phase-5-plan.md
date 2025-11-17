# Phase 5: Context & Sensitivity - Implementation Plan

## Executive Summary

- **Phase:** 5 of 8
- **Focus:** Conversation Context Persistence, Document Sensitivity Validation, Comprehensive Audit Logging
- **Timeline:** 3-4 weeks
- **Status:** Planning Complete - Ready for Implementation
- **Dependencies:** Phase 4 (Outputs Dashboard) - ✅ Complete

---

## Phase Overview

### Goals

Phase 5 builds upon the Outputs Dashboard (Phase 4) to add three critical enterprise-ready features:

1. **Conversation Context Persistence** - Save and restore full conversation state (writing style, audience, section, tone, filters) across sessions
2. **Document Sensitivity Validation** - Enforce sensitivity checks and confirmation workflows before uploading documents
3. **Comprehensive Audit Logging** - Track all important system actions for security, compliance, and debugging

### Business Value

- **User Experience:** Context persists across sessions - users don't lose their work
- **Data Governance:** Sensitivity validation prevents accidental upload of confidential documents
- **Security & Compliance:** Full audit trail of all system actions
- **Production Readiness:** Critical features for enterprise deployment

---

## Current State Analysis

### What EXISTS (from Phase 4 and earlier):

**Database Schema:**
- ✅ `conversations` table with basic fields (conversation_id, name, user_id, metadata)
- ✅ `audit_log` table (fully defined but unused)
- ✅ `messages` table linked to conversations
- ✅ `outputs` table with success tracking
- ✅ `documents` table with basic metadata

**API Endpoints:**
- ✅ Chat API (`/api/chat`) - basic conversation management
- ✅ Documents API (`/api/documents`) - upload, list, delete
- ✅ Outputs API (`/api/outputs`) - full CRUD with analytics
- ✅ Auth API (`/api/auth`) - user authentication

**Infrastructure:**
- ✅ Alembic migrations system
- ✅ PostgreSQL database
- ✅ FastAPI backend with async support
- ✅ Role-based access control (Reader, Writer, Admin)
- ✅ Request logging middleware
- ✅ Metrics middleware

### What's MISSING (Phase 5 scope):

**Database:**
- ❌ `conversations.context` JSONB field for state persistence
- ❌ Document sensitivity fields (is_sensitive, sensitivity_level, etc.)
- ❌ No data in `audit_log` table (table exists but unused)

**API:**
- ❌ Conversation context management endpoints
- ❌ Artifact versioning endpoints
- ❌ Document sensitivity validation endpoints
- ❌ Audit log query/reporting endpoints

**Implementation:**
- ❌ Chat.py uses in-memory storage (not database-backed)
- ❌ No context persistence logic
- ❌ No sensitivity validation on uploads
- ❌ No audit logging middleware

**Models:**
- ❌ Pydantic models for context, artifacts, sensitivity checks
- ❌ SQLAlchemy model updates for new fields

**Tests:**
- ❌ Context persistence tests
- ❌ Sensitivity validation tests
- ❌ Audit logging tests

---

## Architecture Changes

### Database Schema Updates

#### 1. Conversations Table Enhancement

**New Field: `context` (JSONB)**

```sql
ALTER TABLE conversations
ADD COLUMN context JSONB DEFAULT '{}'::jsonb;

-- Index for common queries
CREATE INDEX idx_conversations_context_writing_style
ON conversations ((context->>'writing_style_id'));
```

**Context Structure:**
```json
{
  "writing_style_id": "uuid-string",
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
      "artifact_id": "uuid-string",
      "version": 1,
      "created_at": "2024-11-03T10:30:00Z",
      "content": "Generated text...",
      "word_count": 850,
      "metadata": {}
    }
  ],
  "last_query": "Write organizational capacity section",
  "session_metadata": {
    "started_at": "2024-11-03T10:00:00Z",
    "last_active": "2024-11-03T10:35:00Z"
  }
}
```

#### 2. Documents Table Enhancement

**New Fields for Sensitivity:**

```sql
ALTER TABLE documents
ADD COLUMN is_sensitive BOOLEAN DEFAULT false,
ADD COLUMN sensitivity_level VARCHAR(20) CHECK (sensitivity_level IN ('low', 'medium', 'high')),
ADD COLUMN sensitivity_notes TEXT,
ADD COLUMN sensitivity_confirmed_at TIMESTAMP,
ADD COLUMN sensitivity_confirmed_by VARCHAR(100);

-- Index for sensitivity queries
CREATE INDEX idx_documents_sensitivity
ON documents (is_sensitive, sensitivity_level);
```

**Sensitivity Levels:**
- **Low:** Public-facing documents (published annual reports, public proposals)
- **Medium:** Internal operational documents (board minutes, staff reports)
- **High:** Confidential documents (financial details, personnel records, donor information)

#### 3. Audit Logs Table (Already Exists)

**Existing Schema (from baseline migration `2e0140e533a8`):**

```sql
CREATE TABLE audit_log (
    log_id UUID PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,  -- 'document.upload', 'output.create', etc.
    entity_type VARCHAR(50) NOT NULL,  -- 'document', 'output', 'user', etc.
    entity_id UUID,
    user_id VARCHAR(100),
    details JSONB,  -- Flexible metadata about the action
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_audit_log_event_type ON audit_log (event_type);
CREATE INDEX idx_audit_log_entity_type ON audit_log (entity_type);
CREATE INDEX idx_audit_log_created_at ON audit_log (created_at DESC);
```

**No migration needed** - just need to populate it with audit middleware.

---

### API Endpoints

#### New Conversation Context Endpoints

```python
# Save/Update conversation context
POST /api/conversations/{conversation_id}/context
Request Body: ConversationContext
Response: ConversationContextResponse

# Get conversation context
GET /api/conversations/{conversation_id}/context
Response: ConversationContextResponse

# Conversation context is automatically saved on each chat interaction
# via updated chat endpoint integration
```

#### New Artifact Versioning Endpoints (Optional - Phase 5D)

```python
# Create artifact version
POST /api/conversations/{conversation_id}/artifacts
Request Body: ArtifactCreate
Response: ArtifactVersion

# List artifacts for conversation
GET /api/conversations/{conversation_id}/artifacts
Response: List[ArtifactVersion]

# Get artifact version history
GET /api/artifacts/{artifact_id}/versions
Response: List[ArtifactVersion]
```

#### Updated Document Upload Endpoint

```python
# Modified to require sensitivity confirmation
POST /api/documents/upload
Request Body: DocumentUploadRequest (with sensitivity_confirmed: bool)
Response: DocumentUploadResponse

# Validation: Returns 400 if sensitivity_confirmed != true
```

#### New Audit Log Endpoints

```python
# Query audit logs (Admin only)
GET /api/audit/logs
Query Params:
  - user_id: Optional[str]
  - event_type: Optional[str]
  - entity_type: Optional[str]
  - start_date: Optional[datetime]
  - end_date: Optional[datetime]
  - page: int = 1
  - per_page: int = 50
Response: PaginatedAuditLogResponse

# Get audit logs for specific entity
GET /api/audit/logs/entity/{entity_type}/{entity_id}
Response: List[AuditLogResponse]
```

---

### Middleware Architecture

#### Audit Logging Middleware

**Implementation Pattern:**

```python
# backend/app/middleware/audit.py

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all important actions to audit_log table

    Logs:
    - Document uploads/deletions
    - Output creations/updates
    - Writing style changes
    - User authentication events
    - Success tracking updates
    - Role changes
    """

    async def dispatch(self, request: Request, call_next):
        # Extract user info from request
        user_id = get_user_from_request(request)

        # Call endpoint
        response = await call_next(request)

        # Determine if this is an auditable action
        if self.is_auditable(request, response):
            await self.log_action(
                event_type=self.get_event_type(request),
                entity_type=self.get_entity_type(request),
                entity_id=self.extract_entity_id(request, response),
                user_id=user_id,
                details=self.extract_details(request, response)
            )

        return response
```

**Auditable Events:**

| Event Type | Entity Type | Trigger |
|------------|-------------|---------|
| `document.upload` | `document` | POST /api/documents/upload |
| `document.delete` | `document` | DELETE /api/documents/{id} |
| `output.create` | `output` | POST /api/outputs |
| `output.update` | `output` | PUT /api/outputs/{id} |
| `output.delete` | `output` | DELETE /api/outputs/{id} |
| `success_tracking.update` | `success_tracking` | PUT /api/success-tracking/{id} |
| `writing_style.create` | `writing_style` | POST /api/writing-styles |
| `writing_style.update` | `writing_style` | PUT /api/writing-styles/{id} |
| `writing_style.delete` | `writing_style` | DELETE /api/writing-styles/{id} |
| `user.login` | `user` | POST /api/auth/login |
| `user.logout` | `user` | POST /api/auth/logout |
| `user.role_change` | `user` | PUT /api/users/{id}/role |
| `conversation.create` | `conversation` | POST /api/chat |
| `conversation.delete` | `conversation` | DELETE /api/chat/{id} |

---

## Implementation Tasks

### Phase 5A: Database Foundation (Week 1)

#### Task A: Create Alembic migration for conversations.context field
**Priority:** HIGH
**Estimated Time:** 2-3 hours
**Blocking:** Tasks 1, E, F, G

**Acceptance Criteria:**
- ✅ New migration file created
- ✅ Adds `context` JSONB column to `conversations` table
- ✅ Sets default value to empty JSON object `'{}'::jsonb`
- ✅ Creates index on `context->>'writing_style_id'`
- ✅ Migration runs successfully on test database
- ✅ Rollback (downgrade) works correctly

**Implementation Notes:**
```bash
# Create migration
cd backend
alembic revision -m "add_conversations_context_field"

# Edit migration to add field and index
# Run migration
alembic upgrade head

# Test rollback
alembic downgrade -1
alembic upgrade head
```

---

#### Task B: Create Alembic migration for document sensitivity fields
**Priority:** HIGH
**Estimated Time:** 2-3 hours
**Blocking:** Tasks 2, 3

**Acceptance Criteria:**
- ✅ New migration file created
- ✅ Adds 5 new columns to `documents` table:
  - `is_sensitive` (Boolean, default false)
  - `sensitivity_level` (Enum: low, medium, high)
  - `sensitivity_notes` (Text, nullable)
  - `sensitivity_confirmed_at` (Timestamp, nullable)
  - `sensitivity_confirmed_by` (String, nullable)
- ✅ Creates index on `(is_sensitive, sensitivity_level)`
- ✅ Migration runs successfully
- ✅ Rollback works correctly
- ✅ Existing documents default to `is_sensitive=false`

**Implementation Notes:**
```sql
-- Migration should handle existing documents gracefully
-- All existing documents get is_sensitive=false by default
-- sensitivity_level can be NULL initially
```

---

#### Task C: Update SQLAlchemy models for Phase 5
**Priority:** HIGH
**Estimated Time:** 1-2 hours
**Blocking:** All API implementation tasks

**Acceptance Criteria:**
- ✅ `Conversation` model updated with `context` field
- ✅ `Document` model updated with all 5 sensitivity fields
- ✅ Proper type hints for all new fields
- ✅ Default values match migration defaults
- ✅ Relationships preserved
- ✅ Models serialize/deserialize correctly
- ✅ No breaking changes to existing code

**Files to Update:**
- `backend/app/db/models.py`

**Implementation Notes:**
```python
class Conversation(Base):
    # ... existing fields ...
    context = Column(JSONB, default={}, nullable=False)

class Document(Base):
    # ... existing fields ...
    is_sensitive = Column(Boolean, default=False, nullable=False)
    sensitivity_level = Column(String(20), nullable=True)
    sensitivity_notes = Column(Text, nullable=True)
    sensitivity_confirmed_at = Column(DateTime, nullable=True)
    sensitivity_confirmed_by = Column(String(100), nullable=True)
```

---

#### Task D: Create Pydantic models for Phase 5 features
**Priority:** HIGH
**Estimated Time:** 3-4 hours
**Blocking:** All API implementation tasks

**Acceptance Criteria:**
- ✅ `ConversationContext` model created
- ✅ `ConversationContextResponse` model created
- ✅ `ArtifactVersion` model created
- ✅ `DocumentSensitivityCheck` model created
- ✅ `AuditLogQuery` model created
- ✅ `AuditLogResponse` model created
- ✅ All models have proper validation
- ✅ Example values provided for API docs
- ✅ Type hints are complete and accurate

**Files to Create/Update:**
- `backend/app/models/conversation.py` (new)
- `backend/app/models/document.py` (update)
- `backend/app/models/audit.py` (new)

**Key Models:**

```python
# backend/app/models/conversation.py

class DocumentFilters(BaseModel):
    doc_types: Optional[List[str]] = None
    years: Optional[List[int]] = None
    programs: Optional[List[str]] = None
    outcome: Optional[str] = None

class ArtifactVersion(BaseModel):
    artifact_id: str
    version: int
    created_at: datetime
    content: str
    word_count: int
    metadata: Dict[str, Any] = {}

class SessionMetadata(BaseModel):
    started_at: datetime
    last_active: datetime

class ConversationContext(BaseModel):
    writing_style_id: Optional[str] = None
    audience: Optional[str] = None
    section: Optional[str] = None
    tone: Optional[str] = None
    filters: Optional[DocumentFilters] = None
    artifacts: List[ArtifactVersion] = []
    last_query: Optional[str] = None
    session_metadata: Optional[SessionMetadata] = None

class ConversationContextResponse(BaseModel):
    conversation_id: str
    context: ConversationContext
    updated_at: datetime

# backend/app/models/document.py (additions)

class DocumentSensitivityCheck(BaseModel):
    is_sensitive: bool = False
    sensitivity_level: Optional[Literal["low", "medium", "high"]] = None
    sensitivity_notes: Optional[str] = None

class DocumentUploadRequest(BaseModel):
    # ... existing fields ...
    sensitivity_confirmed: bool = Field(..., description="Must confirm document sensitivity")

# backend/app/models/audit.py (new file)

class AuditLogQuery(BaseModel):
    user_id: Optional[str] = None
    event_type: Optional[str] = None
    entity_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(50, ge=1, le=100)

class AuditLogResponse(BaseModel):
    log_id: str
    event_type: str
    entity_type: str
    entity_id: Optional[str]
    user_id: Optional[str]
    details: Dict[str, Any]
    created_at: datetime
```

---

### Phase 5B: Core Implementation (Week 2)

#### Task G: Migrate chat.py to database-backed conversation storage
**Priority:** CRITICAL
**Estimated Time:** 4-6 hours
**Blocking:** Task 1, E

**Current Issue:** `backend/app/api/chat.py` uses in-memory dictionary for conversation storage. This is not persistent.

**Acceptance Criteria:**
- ✅ Remove in-memory `conversations_store`
- ✅ All conversation operations use database
- ✅ Create conversation: INSERT into conversations table
- ✅ Get conversation: SELECT from conversations + messages
- ✅ List conversations: SELECT with pagination
- ✅ Delete conversation: DELETE with cascade
- ✅ Add message: INSERT into messages table
- ✅ Context is initialized on conversation creation
- ✅ Backward compatibility maintained
- ✅ All existing chat tests pass
- ✅ New tests for database persistence

**Implementation Steps:**
1. Add database service dependency to chat endpoints
2. Replace in-memory operations with database queries
3. Ensure transactions handle failures correctly
4. Add proper error handling for database errors
5. Update tests to use database fixtures

---

#### Task 1: Update conversation context handling (EXISTING - Modified)
**Original Task ID:** `3b667845-89ad-4feb-8d83-286662e7373a`
**Priority:** HIGH
**Estimated Time:** 3-4 hours
**Dependencies:** Tasks A, C, D, G

**Original Description (needs update):**
> Update backend/app/api/chat.py to save/restore conversation context (writing_style_id, audience, section, tone, filters) in conversations.context JSONB field. Store artifacts array for version tracking. Link conversation to final output via output_id FK. Ensure context persists across sessions.

**Updated Description:**
> Implement conversation context persistence in chat.py. On each chat interaction, save current context (writing_style_id, audience, section, tone, filters) to conversations.context JSONB field. On conversation load, restore context from database. Ensure context updates are atomic and handle concurrent updates gracefully.

**Acceptance Criteria:**
- ✅ Context is saved to database on every chat interaction
- ✅ Context includes: writing_style_id, audience, section, tone, filters
- ✅ Context is restored when loading existing conversation
- ✅ Artifacts array is initialized and maintained
- ✅ Session metadata tracks start time and last activity
- ✅ Context updates are atomic (use database transactions)
- ✅ Handle missing/corrupt context gracefully (fallback to defaults)
- ✅ No performance degradation from context operations
- ✅ Context is included in conversation response payloads

**Implementation Notes:**
```python
# Pseudo-code for context handling

async def chat_endpoint(
    conversation_id: str,
    message: ChatMessage,
    context: ConversationContext,
    db: DatabaseService
):
    # Get existing conversation
    conversation = await db.get_conversation(conversation_id)

    # Update context
    conversation.context = {
        "writing_style_id": context.writing_style_id,
        "audience": context.audience,
        "section": context.section,
        "tone": context.tone,
        "filters": context.filters.dict() if context.filters else {},
        "artifacts": conversation.context.get("artifacts", []),
        "last_query": message.content,
        "session_metadata": {
            "started_at": conversation.created_at.isoformat(),
            "last_active": datetime.now().isoformat()
        }
    }

    # Save to database atomically
    await db.update_conversation(conversation_id, context=conversation.context)

    # Continue with chat logic...
```

---

#### Task E: Create conversation context management endpoints (NEW)
**Priority:** MEDIUM
**Estimated Time:** 3-4 hours
**Dependencies:** Tasks A, C, D, G

**Acceptance Criteria:**
- ✅ POST `/api/conversations/{id}/context` endpoint created
- ✅ GET `/api/conversations/{id}/context` endpoint created
- ✅ Endpoints require authentication
- ✅ Validation ensures context structure is valid
- ✅ Error handling for missing conversations
- ✅ Returns 404 if conversation doesn't exist
- ✅ Returns 403 if user doesn't own conversation
- ✅ Proper OpenAPI documentation
- ✅ Response includes updated_at timestamp

**Implementation:**
```python
# backend/app/api/chat.py (additions)

@router.post("/conversations/{conversation_id}/context")
async def update_conversation_context(
    conversation_id: str,
    context: ConversationContext,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_database)
) -> ConversationContextResponse:
    """Update conversation context"""
    conversation = await db.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Update context
    await db.update_conversation(
        conversation_id,
        context=context.dict()
    )

    return ConversationContextResponse(
        conversation_id=conversation_id,
        context=context,
        updated_at=datetime.now()
    )

@router.get("/conversations/{conversation_id}/context")
async def get_conversation_context(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_database)
) -> ConversationContextResponse:
    """Get conversation context"""
    conversation = await db.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    context = ConversationContext(**conversation.context)

    return ConversationContextResponse(
        conversation_id=conversation_id,
        context=context,
        updated_at=conversation.updated_at
    )
```

---

#### Task 2: Add document sensitivity validation (EXISTING - Modified)
**Original Task ID:** `8d5683cb-ec53-4b12-94d8-ec98c8077533`
**Priority:** HIGH
**Estimated Time:** 2-3 hours
**Dependencies:** Tasks B, C, D

**Original Description:**
> Update document upload to require sensitivity confirmation (MVP). Add validation: sensitivity_confirmed must be true. Display warning: "Only upload public-facing documents. Do not upload confidential, financial, or sensitive operational documents." Checkbox: "I confirm this document is public-facing." Reject uploads without confirmation.

**Updated Description:**
> Implement document sensitivity validation logic. Create validation function that checks DocumentUploadRequest.sensitivity_confirmed field. If false, return 400 error with warning message. Update DocumentUploadRequest Pydantic model to include sensitivity_confirmed field (required).

**Acceptance Criteria:**
- ✅ `DocumentUploadRequest` model includes `sensitivity_confirmed: bool` field
- ✅ Field is required (no default value)
- ✅ Validation function checks `sensitivity_confirmed == true`
- ✅ Returns 400 error if confirmation is false/missing
- ✅ Error message includes clear warning about sensitive documents
- ✅ Warning text: "Only upload public-facing documents. Do not upload confidential, financial, or sensitive operational documents."
- ✅ Document metadata includes sensitivity fields after upload
- ✅ Sensitivity confirmation logged to audit_log

**Implementation:**
```python
# backend/app/models/document.py (update)

class DocumentUploadRequest(BaseModel):
    # ... existing fields ...
    sensitivity_confirmed: bool = Field(
        ...,
        description="Confirmation that document is public-facing and not sensitive"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "annual_report_2024.pdf",
                "doc_type": "Annual Report",
                "year": 2024,
                "sensitivity_confirmed": True
            }
        }

# backend/app/api/documents.py (update)

@router.post("/upload")
async def upload_document(
    request: DocumentUploadRequest,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    # Validate sensitivity confirmation
    if not request.sensitivity_confirmed:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Sensitivity confirmation required",
                "message": "Only upload public-facing documents. Do not upload confidential, financial, or sensitive operational documents.",
                "action": "Please confirm that this document is appropriate for upload."
            }
        )

    # Continue with upload...
```

---

#### Task 3: Update document upload endpoint with sensitivity check (EXISTING)
**Original Task ID:** `85329282-900c-4745-b4a5-6a61bd5e0cf0`
**Priority:** MEDIUM
**Estimated Time:** 1-2 hours
**Dependencies:** Task 2

**Description:**
> Modify POST /api/documents/upload in backend/app/api/documents.py to require sensitivity_confirmed=true in request. Return 400 error if not confirmed. Update DocumentUploadRequest model to include sensitivity_confirmed field. Update documentation with sensitivity requirements.

**Acceptance Criteria:**
- ✅ Upload endpoint validates sensitivity_confirmed before processing file
- ✅ Returns 400 with descriptive error if not confirmed
- ✅ OpenAPI docs updated with sensitivity requirements
- ✅ Example requests show sensitivity_confirmed=true
- ✅ Existing upload tests updated to include confirmation
- ✅ New tests for sensitivity validation rejection

**Implementation Notes:**
This task is mostly complete with Task 2. Just need to ensure documentation and tests are comprehensive.

---

### Phase 5C: Audit & Testing (Week 3)

#### Task 5: Implement comprehensive audit logging middleware (EXISTING - Modified)
**Original Task ID:** `8acc5555-4a88-4def-944f-c6ef7628712e`
**Priority:** HIGH
**Estimated Time:** 6-8 hours
**Dependencies:** None (audit_log table already exists)

**Original Description:**
> Create backend/app/middleware/audit.py to log all important actions: user login/logout, role changes, document upload/delete, writing style create/edit/delete, output generation/save, success tracking updates, settings changes. Capture user_id, action, resource_type, resource_id, details JSONB, ip_address, user_agent, timestamp. Add to all protected endpoints.

**Updated Description:**
> Create audit logging middleware that intercepts all requests and logs auditable actions to the existing audit_log table. Middleware determines if action is auditable based on HTTP method and endpoint pattern. Extracts entity information from request/response and writes to database asynchronously. Register middleware in main.py.

**Acceptance Criteria:**
- ✅ File `backend/app/middleware/audit.py` created
- ✅ `AuditLoggingMiddleware` class implements `BaseHTTPMiddleware`
- ✅ Middleware identifies auditable actions (see table in Architecture Changes)
- ✅ Extracts: event_type, entity_type, entity_id, user_id, details
- ✅ Writes to `audit_log` table asynchronously (non-blocking)
- ✅ Handles database errors gracefully (logs don't break requests)
- ✅ Details JSONB includes: ip_address, user_agent, request_body (sanitized)
- ✅ Middleware registered in `main.py`
- ✅ No performance degradation (<10ms overhead per request)
- ✅ Audit logs are queryable after actions complete

**Implementation:**

```python
# backend/app/middleware/audit.py

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import re
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all important actions to audit_log table
    """

    # Patterns for auditable endpoints
    AUDIT_PATTERNS = [
        (r"POST /api/documents/upload", "document.upload", "document"),
        (r"DELETE /api/documents/([^/]+)", "document.delete", "document"),
        (r"POST /api/outputs", "output.create", "output"),
        (r"PUT /api/outputs/([^/]+)", "output.update", "output"),
        (r"DELETE /api/outputs/([^/]+)", "output.delete", "output"),
        (r"PUT /api/success-tracking/([^/]+)", "success_tracking.update", "success_tracking"),
        (r"POST /api/writing-styles", "writing_style.create", "writing_style"),
        (r"PUT /api/writing-styles/([^/]+)", "writing_style.update", "writing_style"),
        (r"DELETE /api/writing-styles/([^/]+)", "writing_style.delete", "writing_style"),
        (r"POST /api/auth/login", "user.login", "user"),
        (r"POST /api/auth/logout", "user.logout", "user"),
        (r"POST /api/chat", "conversation.create", "conversation"),
        (r"DELETE /api/chat/([^/]+)", "conversation.delete", "conversation"),
    ]

    async def dispatch(self, request: Request, call_next):
        # Get user from request (if authenticated)
        user_id = self._extract_user_id(request)

        # Build request signature
        method = request.method
        path = request.url.path
        signature = f"{method} {path}"

        # Check if auditable
        audit_info = self._match_audit_pattern(signature)

        # Call endpoint
        response = await call_next(request)

        # Log if auditable and successful
        if audit_info and 200 <= response.status_code < 300:
            try:
                await self._log_audit(
                    request=request,
                    response=response,
                    event_type=audit_info["event_type"],
                    entity_type=audit_info["entity_type"],
                    entity_id=audit_info.get("entity_id"),
                    user_id=user_id
                )
            except Exception as e:
                # Don't break request if audit logging fails
                logger.error(f"Audit logging failed: {str(e)}")

        return response

    def _match_audit_pattern(self, signature: str) -> Optional[Dict[str, Any]]:
        """Match request signature against audit patterns"""
        for pattern, event_type, entity_type in self.AUDIT_PATTERNS:
            match = re.match(pattern, signature)
            if match:
                entity_id = match.group(1) if match.groups() else None
                return {
                    "event_type": event_type,
                    "entity_type": entity_type,
                    "entity_id": entity_id
                }
        return None

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request"""
        # Check if user is in request state (set by auth dependency)
        if hasattr(request.state, "user"):
            return request.state.user.user_id
        return None

    async def _log_audit(
        self,
        request: Request,
        response: Response,
        event_type: str,
        entity_type: str,
        entity_id: Optional[str],
        user_id: Optional[str]
    ):
        """Write audit log to database"""
        from app.db.database import get_database

        # Extract additional details
        details = {
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code
        }

        # Get database service
        db = get_database()

        # Insert audit log (non-blocking)
        await db.create_audit_log(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            details=details
        )

# backend/app/main.py (update)

from app.middleware.audit import AuditLoggingMiddleware

app = FastAPI(title="Org Archivist API")

# Add audit logging middleware
app.add_middleware(AuditLoggingMiddleware)
```

---

#### Task 6: Create audit log viewing API endpoint (EXISTING)
**Original Task ID:** `af9035b8-6da9-4388-ac32-e7f4dd2b795d`
**Priority:** MEDIUM
**Estimated Time:** 3-4 hours
**Dependencies:** Task 5

**Description:**
> Create GET /api/audit-log endpoint (Admin only) in backend/app/api/audit.py. Support filtering by: user_id, action, resource_type, date_range. Pagination required. Include search functionality. Return audit entries with full details. Useful for security monitoring and compliance.

**Acceptance Criteria:**
- ✅ File `backend/app/api/audit.py` created
- ✅ GET `/api/audit/logs` endpoint implemented
- ✅ Requires Admin role (returns 403 for non-admins)
- ✅ Query parameters: user_id, event_type, entity_type, start_date, end_date, page, per_page
- ✅ Returns paginated results (max 100 per page)
- ✅ Includes total count and page metadata
- ✅ Results sorted by created_at DESC (most recent first)
- ✅ GET `/api/audit/logs/entity/{entity_type}/{entity_id}` endpoint
- ✅ Proper OpenAPI documentation
- ✅ Error handling for invalid parameters

**Implementation:**

```python
# backend/app/api/audit.py (new file)

from fastapi import APIRouter, Depends, HTTPException, Query
from app.models.audit import AuditLogQuery, AuditLogResponse, PaginatedAuditLogResponse
from app.api.auth import get_current_user, require_role
from app.db.database import DatabaseService, get_database
from datetime import datetime
from typing import Optional, List

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.get("/logs", response_model=PaginatedAuditLogResponse)
async def query_audit_log(
    user_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    current_user = Depends(get_current_user),
    db: DatabaseService = Depends(get_database)
):
    """
    Query audit logs (Admin only)

    Supports filtering by:
    - user_id: Filter by user
    - event_type: Filter by event (e.g., 'document.upload')
    - entity_type: Filter by entity (e.g., 'document')
    - start_date: Filter logs after this date
    - end_date: Filter logs before this date
    """

    # Require admin role
    require_role(current_user, "Admin")

    # Build query
    query = AuditLogQuery(
        user_id=user_id,
        event_type=event_type,
        entity_type=entity_type,
        start_date=start_date,
        end_date=end_date,
        page=page,
        per_page=per_page
    )

    # Query database
    logs, total_count = await db.query_audit_log(query)

    # Calculate pagination
    total_pages = (total_count + per_page - 1) // per_page

    return PaginatedAuditLogResponse(
        logs=[AuditLogResponse.from_orm(log) for log in logs],
        total_count=total_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )

@router.get("/logs/entity/{entity_type}/{entity_id}", response_model=List[AuditLogResponse])
async def get_entity_audit_log(
    entity_type: str,
    entity_id: str,
    current_user = Depends(get_current_user),
    db: DatabaseService = Depends(get_database)
):
    """
    Get all audit logs for a specific entity (Admin only)
    """

    # Require admin role
    require_role(current_user, "Admin")

    # Query database
    logs = await db.get_entity_audit_log(entity_type, entity_id)

    return [AuditLogResponse.from_orm(log) for log in logs]

# backend/app/main.py (update)

from app.api import audit

app.include_router(audit.router)
```

**Database Service Methods:**

```python
# backend/app/db/database.py (additions)

async def query_audit_log(
    self,
    query: AuditLogQuery
) -> Tuple[List[AuditLog], int]:
    """Query audit logs with filters and pagination"""

    # Build WHERE clause
    conditions = []
    params = {}

    if query.user_id:
        conditions.append("user_id = :user_id")
        params["user_id"] = query.user_id

    if query.event_type:
        conditions.append("event_type = :event_type")
        params["event_type"] = query.event_type

    if query.entity_type:
        conditions.append("entity_type = :entity_type")
        params["entity_type"] = query.entity_type

    if query.start_date:
        conditions.append("created_at >= :start_date")
        params["start_date"] = query.start_date

    if query.end_date:
        conditions.append("created_at <= :end_date")
        params["end_date"] = query.end_date

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Count total
    count_query = f"SELECT COUNT(*) FROM audit_log WHERE {where_clause}"
    total_count = await self.fetch_val(count_query, params)

    # Get paginated results
    offset = (query.page - 1) * query.per_page
    data_query = f"""
        SELECT * FROM audit_log
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """
    params["limit"] = query.per_page
    params["offset"] = offset

    logs = await self.fetch_all(data_query, params)

    return logs, total_count

async def get_entity_audit_log(
    self,
    entity_type: str,
    entity_id: str
) -> List[AuditLog]:
    """Get all audit logs for a specific entity"""

    query = """
        SELECT * FROM audit_log
        WHERE entity_type = :entity_type AND entity_id = :entity_id
        ORDER BY created_at DESC
    """

    return await self.fetch_all(query, {
        "entity_type": entity_type,
        "entity_id": entity_id
    })
```

---

#### Task 4: Test conversation context persistence (EXISTING)
**Original Task ID:** `5b3ba706-a1b0-400a-a6d3-70e6c4dc45fe`
**Priority:** HIGH
**Estimated Time:** 4-5 hours
**Dependencies:** Tasks 1, E, G

**Description:**
> Create tests: test_context_save_on_chat, test_context_restore_on_load, test_context_includes_all_fields (style, audience, section, tone, filters), test_artifacts_version_tracking, test_context_update_mid_conversation. Verify context persists across page refreshes and sessions.

**Acceptance Criteria:**
- ✅ File `backend/tests/test_conversation_context.py` created
- ✅ Test: Context is saved when chat message is sent
- ✅ Test: Context is restored when conversation is loaded
- ✅ Test: Context includes all required fields (writing_style_id, audience, section, tone, filters)
- ✅ Test: Artifacts array is maintained correctly
- ✅ Test: Context updates correctly mid-conversation
- ✅ Test: Session metadata is updated on each interaction
- ✅ Test: Context handles missing/null fields gracefully
- ✅ Test: Context is preserved across database restarts (integration test)
- ✅ All tests pass
- ✅ Test coverage >80% for context-related code

**Test Cases:**

```python
# backend/tests/test_conversation_context.py

import pytest
from datetime import datetime

class TestConversationContext:

    async def test_context_save_on_chat(self, client, auth_headers, db_session):
        """Test that context is saved when sending a chat message"""
        # Create conversation
        response = await client.post(
            "/api/chat",
            json={"message": "Hello"},
            headers=auth_headers
        )
        conversation_id = response.json()["conversation_id"]

        # Send message with context
        context = {
            "writing_style_id": "style-123",
            "audience": "Federal RFP",
            "section": "Organizational Capacity",
            "tone": "formal",
            "filters": {
                "doc_types": ["Grant Proposal"],
                "years": [2024]
            }
        }

        response = await client.post(
            f"/api/chat/{conversation_id}",
            json={
                "message": "Write about our capacity",
                "context": context
            },
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify context was saved to database
        conversation = await db_session.get_conversation(conversation_id)
        assert conversation.context["writing_style_id"] == "style-123"
        assert conversation.context["audience"] == "Federal RFP"
        assert conversation.context["section"] == "Organizational Capacity"
        assert conversation.context["tone"] == "formal"
        assert conversation.context["filters"]["years"] == [2024]

    async def test_context_restore_on_load(self, client, auth_headers, db_session):
        """Test that context is restored when loading conversation"""
        # Create conversation with context
        context = {
            "writing_style_id": "style-456",
            "audience": "Foundation Grant",
            "section": "Program Description",
            "tone": "warm"
        }

        conversation_id = await db_session.create_conversation(
            user_id="test-user",
            name="Test Conversation",
            context=context
        )

        # Load conversation
        response = await client.get(
            f"/api/chat/{conversation_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify context was restored
        assert data["context"]["writing_style_id"] == "style-456"
        assert data["context"]["audience"] == "Foundation Grant"
        assert data["context"]["section"] == "Program Description"
        assert data["context"]["tone"] == "warm"

    async def test_context_includes_all_fields(self, client, auth_headers):
        """Test that context includes all required fields"""
        # Create conversation with full context
        full_context = {
            "writing_style_id": "style-789",
            "audience": "Individual Donor",
            "section": "Impact & Outcomes",
            "tone": "conversational",
            "filters": {
                "doc_types": ["Annual Report", "Impact Report"],
                "years": [2023, 2024],
                "programs": ["Early Childhood"],
                "outcome": "Funded"
            },
            "artifacts": [
                {
                    "artifact_id": "art-1",
                    "version": 1,
                    "created_at": "2024-11-03T10:00:00Z",
                    "content": "Generated text...",
                    "word_count": 500,
                    "metadata": {}
                }
            ],
            "last_query": "Write impact section",
            "session_metadata": {
                "started_at": "2024-11-03T09:00:00Z",
                "last_active": "2024-11-03T10:00:00Z"
            }
        }

        response = await client.post(
            "/api/chat",
            json={
                "message": "Start conversation",
                "context": full_context
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        conversation_id = response.json()["conversation_id"]

        # Get context
        response = await client.get(
            f"/api/conversations/{conversation_id}/context",
            headers=auth_headers
        )

        assert response.status_code == 200
        context = response.json()["context"]

        # Verify all fields present
        assert "writing_style_id" in context
        assert "audience" in context
        assert "section" in context
        assert "tone" in context
        assert "filters" in context
        assert "artifacts" in context
        assert "last_query" in context
        assert "session_metadata" in context

    async def test_artifacts_version_tracking(self, client, auth_headers):
        """Test that artifacts array tracks versions correctly"""
        # Create conversation
        response = await client.post(
            "/api/chat",
            json={"message": "Hello"},
            headers=auth_headers
        )
        conversation_id = response.json()["conversation_id"]

        # Add first artifact
        artifact_1 = {
            "artifact_id": "art-1",
            "version": 1,
            "created_at": datetime.now().isoformat(),
            "content": "First version",
            "word_count": 100,
            "metadata": {}
        }

        # Add second artifact
        artifact_2 = {
            "artifact_id": "art-2",
            "version": 1,
            "created_at": datetime.now().isoformat(),
            "content": "Second artifact",
            "word_count": 200,
            "metadata": {}
        }

        # Update context with artifacts
        response = await client.post(
            f"/api/conversations/{conversation_id}/context",
            json={
                "artifacts": [artifact_1, artifact_2]
            },
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify artifacts are tracked
        response = await client.get(
            f"/api/conversations/{conversation_id}/context",
            headers=auth_headers
        )

        artifacts = response.json()["context"]["artifacts"]
        assert len(artifacts) == 2
        assert artifacts[0]["artifact_id"] == "art-1"
        assert artifacts[1]["artifact_id"] == "art-2"

    async def test_context_update_mid_conversation(self, client, auth_headers):
        """Test that context can be updated mid-conversation"""
        # Create conversation with initial context
        response = await client.post(
            "/api/chat",
            json={
                "message": "Hello",
                "context": {
                    "audience": "Federal RFP",
                    "tone": "formal"
                }
            },
            headers=auth_headers
        )
        conversation_id = response.json()["conversation_id"]

        # Update context mid-conversation
        new_context = {
            "audience": "Foundation Grant",  # Changed
            "tone": "warm",  # Changed
            "section": "Program Description"  # Added
        }

        response = await client.post(
            f"/api/conversations/{conversation_id}/context",
            json=new_context,
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify context was updated
        response = await client.get(
            f"/api/conversations/{conversation_id}/context",
            headers=auth_headers
        )

        context = response.json()["context"]
        assert context["audience"] == "Foundation Grant"
        assert context["tone"] == "warm"
        assert context["section"] == "Program Description"

    async def test_session_metadata_updates(self, client, auth_headers, db_session):
        """Test that session metadata is updated on each interaction"""
        # Create conversation
        response = await client.post(
            "/api/chat",
            json={"message": "Hello"},
            headers=auth_headers
        )
        conversation_id = response.json()["conversation_id"]

        # Get initial last_active time
        conversation = await db_session.get_conversation(conversation_id)
        initial_last_active = conversation.context.get("session_metadata", {}).get("last_active")

        # Wait a bit
        import asyncio
        await asyncio.sleep(1)

        # Send another message
        response = await client.post(
            f"/api/chat/{conversation_id}",
            json={"message": "Second message"},
            headers=auth_headers
        )

        # Verify last_active was updated
        conversation = await db_session.get_conversation(conversation_id)
        updated_last_active = conversation.context.get("session_metadata", {}).get("last_active")

        assert updated_last_active > initial_last_active

    async def test_context_handles_missing_fields(self, client, auth_headers):
        """Test that context handles missing/null fields gracefully"""
        # Create conversation with partial context
        partial_context = {
            "audience": "Federal RFP"
            # Missing: writing_style_id, section, tone, filters
        }

        response = await client.post(
            "/api/chat",
            json={
                "message": "Hello",
                "context": partial_context
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        conversation_id = response.json()["conversation_id"]

        # Verify context is valid with defaults
        response = await client.get(
            f"/api/conversations/{conversation_id}/context",
            headers=auth_headers
        )

        assert response.status_code == 200
        context = response.json()["context"]

        assert context["audience"] == "Federal RFP"
        # Other fields should be None or have defaults
        assert "writing_style_id" in context
        assert "section" in context
```

---

#### Task H: Test document sensitivity validation (NEW)
**Priority:** HIGH
**Estimated Time:** 3-4 hours
**Dependencies:** Tasks 2, 3

**Acceptance Criteria:**
- ✅ File `backend/tests/test_document_sensitivity.py` created
- ✅ Test: Upload fails without sensitivity_confirmed
- ✅ Test: Upload succeeds with sensitivity_confirmed=true
- ✅ Test: Error message includes proper warning
- ✅ Test: Sensitivity fields are stored in database
- ✅ Test: Sensitivity confirmation is logged to audit
- ✅ Test: Admins can override sensitivity checks (if applicable)
- ✅ All tests pass
- ✅ Test coverage >80% for sensitivity code

**Test Cases:**

```python
# backend/tests/test_document_sensitivity.py

import pytest

class TestDocumentSensitivity:

    async def test_upload_fails_without_confirmation(self, client, auth_headers):
        """Test that upload fails without sensitivity confirmation"""
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
            data={
                "filename": "test.pdf",
                "doc_type": "Grant Proposal",
                "year": 2024,
                "sensitivity_confirmed": False  # Not confirmed
            },
            headers=auth_headers
        )

        assert response.status_code == 400
        error = response.json()["detail"]
        assert "Sensitivity confirmation required" in error["error"]
        assert "public-facing documents" in error["message"].lower()

    async def test_upload_succeeds_with_confirmation(self, client, auth_headers):
        """Test that upload succeeds with sensitivity confirmation"""
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
            data={
                "filename": "test.pdf",
                "doc_type": "Grant Proposal",
                "year": 2024,
                "sensitivity_confirmed": True  # Confirmed
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "doc_id" in data

    async def test_sensitivity_fields_stored(self, client, auth_headers, db_session):
        """Test that sensitivity fields are stored in database"""
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
            data={
                "filename": "test.pdf",
                "doc_type": "Annual Report",
                "year": 2024,
                "sensitivity_confirmed": True,
                "is_sensitive": False,
                "sensitivity_level": "low"
            },
            headers=auth_headers
        )

        doc_id = response.json()["doc_id"]

        # Verify fields in database
        document = await db_session.get_document(doc_id)
        assert document.is_sensitive == False
        assert document.sensitivity_level == "low"
        assert document.sensitivity_confirmed_at is not None
        assert document.sensitivity_confirmed_by is not None

    async def test_sensitivity_logged_to_audit(self, client, auth_headers, db_session):
        """Test that sensitivity confirmation is logged to audit"""
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
            data={
                "filename": "test.pdf",
                "doc_type": "Grant Proposal",
                "year": 2024,
                "sensitivity_confirmed": True
            },
            headers=auth_headers
        )

        doc_id = response.json()["doc_id"]

        # Check audit log
        audit_log = await db_session.query_audit_log(
            event_type="document.upload",
            entity_id=doc_id
        )

        assert len(audit_log) > 0
        log = audit_log[0]
        assert log.event_type == "document.upload"
        assert log.entity_id == doc_id
        assert "sensitivity_confirmed" in log.details
```

---

#### Task I: Test audit logging integration (NEW)
**Priority:** HIGH
**Estimated Time:** 4-5 hours
**Dependencies:** Tasks 5, 6

**Acceptance Criteria:**
- ✅ File `backend/tests/test_audit_logging.py` created
- ✅ Test: Audit log is created for document upload
- ✅ Test: Audit log is created for output creation
- ✅ Test: Audit log is created for writing style changes
- ✅ Test: Audit log includes correct event_type, entity_type, entity_id
- ✅ Test: Audit log includes user_id
- ✅ Test: Audit log query endpoint returns correct results
- ✅ Test: Audit log filtering works (by user, event, date)
- ✅ Test: Audit log requires Admin role
- ✅ Test: Audit logging doesn't break requests on database errors
- ✅ All tests pass
- ✅ Test coverage >80% for audit code

**Test Cases:**

```python
# backend/tests/test_audit_logging.py

import pytest
from datetime import datetime, timedelta

class TestAuditLogging:

    async def test_audit_log_document_upload(self, client, auth_headers, db_session):
        """Test that document upload creates audit log"""
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
            data={
                "filename": "test.pdf",
                "doc_type": "Grant Proposal",
                "year": 2024,
                "sensitivity_confirmed": True
            },
            headers=auth_headers
        )

        doc_id = response.json()["doc_id"]

        # Verify audit log was created
        logs = await db_session.query_audit_log(
            event_type="document.upload",
            entity_id=doc_id
        )

        assert len(logs) > 0
        log = logs[0]
        assert log.event_type == "document.upload"
        assert log.entity_type == "document"
        assert log.entity_id == doc_id
        assert log.user_id is not None
        assert log.details["method"] == "POST"
        assert log.details["status_code"] == 200

    async def test_audit_log_output_creation(self, client, auth_headers, db_session):
        """Test that output creation creates audit log"""
        response = await client.post(
            "/api/outputs",
            json={
                "title": "Test Output",
                "content": "Test content",
                "audience": "Federal RFP"
            },
            headers=auth_headers
        )

        output_id = response.json()["output_id"]

        # Verify audit log
        logs = await db_session.query_audit_log(
            event_type="output.create",
            entity_id=output_id
        )

        assert len(logs) > 0
        log = logs[0]
        assert log.event_type == "output.create"
        assert log.entity_type == "output"
        assert log.entity_id == output_id

    async def test_audit_query_endpoint(self, client, admin_headers, db_session):
        """Test audit log query endpoint"""
        # Create some audit logs
        await db_session.create_audit_log(
            event_type="document.upload",
            entity_type="document",
            entity_id="doc-123",
            user_id="user-1",
            details={}
        )

        # Query logs
        response = await client.get(
            "/api/audit/logs",
            params={
                "event_type": "document.upload",
                "page": 1,
                "per_page": 50
            },
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "logs" in data
        assert "total_count" in data
        assert "page" in data
        assert len(data["logs"]) > 0

    async def test_audit_filtering(self, client, admin_headers, db_session):
        """Test audit log filtering"""
        # Create logs for different users
        await db_session.create_audit_log(
            event_type="document.upload",
            entity_type="document",
            entity_id="doc-1",
            user_id="user-1",
            details={}
        )
        await db_session.create_audit_log(
            event_type="output.create",
            entity_type="output",
            entity_id="out-1",
            user_id="user-2",
            details={}
        )

        # Filter by user_id
        response = await client.get(
            "/api/audit/logs",
            params={"user_id": "user-1"},
            headers=admin_headers
        )

        data = response.json()
        assert all(log["user_id"] == "user-1" for log in data["logs"])

        # Filter by event_type
        response = await client.get(
            "/api/audit/logs",
            params={"event_type": "document.upload"},
            headers=admin_headers
        )

        data = response.json()
        assert all(log["event_type"] == "document.upload" for log in data["logs"])

    async def test_audit_requires_admin_role(self, client, writer_headers):
        """Test that audit endpoint requires Admin role"""
        response = await client.get(
            "/api/audit/logs",
            headers=writer_headers  # Not admin
        )

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    async def test_audit_logging_doesnt_break_requests(
        self,
        client,
        auth_headers,
        monkeypatch
    ):
        """Test that audit logging errors don't break requests"""
        # Mock database to raise error on audit log creation
        async def mock_create_audit_log(*args, **kwargs):
            raise Exception("Database error")

        monkeypatch.setattr(
            "app.db.database.DatabaseService.create_audit_log",
            mock_create_audit_log
        )

        # Upload document - should succeed despite audit error
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
            data={
                "filename": "test.pdf",
                "doc_type": "Grant Proposal",
                "year": 2024,
                "sensitivity_confirmed": True
            },
            headers=auth_headers
        )

        # Request should still succeed
        assert response.status_code == 200
```

---

### Phase 5D: Enhancements (Optional/Future)

#### Task F: Create artifact versioning endpoints (NEW)
**Priority:** LOW
**Estimated Time:** 4-6 hours
**Dependencies:** Tasks A, C, D, E

**Status:** Optional - can be deferred to future phase

**Acceptance Criteria:**
- ✅ POST `/api/conversations/{id}/artifacts` endpoint
- ✅ GET `/api/conversations/{id}/artifacts` endpoint
- ✅ GET `/api/artifacts/{id}/versions` endpoint
- ✅ Artifacts stored in conversations.context.artifacts array
- ✅ Version numbering is automatic
- ✅ Side-by-side comparison support
- ✅ Revert to previous version support
- ✅ Tests for artifact versioning

---

#### Task J: Frontend integration for context persistence (NEW)
**Priority:** LOW
**Estimated Time:** 6-8 hours
**Dependencies:** All backend Phase 5 tasks

**Status:** Deferred to frontend phase

**Acceptance Criteria:**
- ✅ Frontend sends context with each chat message
- ✅ Frontend restores context when loading conversation
- ✅ Context is displayed in UI (sidebar/panel)
- ✅ User can modify context mid-conversation
- ✅ Artifacts are displayed with version history
- ✅ Context persists across page refreshes

---

#### Task K: Audit log analytics dashboard (NEW)
**Priority:** LOW
**Estimated Time:** 8-10 hours
**Dependencies:** Task 6

**Status:** Deferred to future phase

**Acceptance Criteria:**
- ✅ Admin dashboard shows audit metrics
- ✅ Charts: Actions over time, actions by type, actions by user
- ✅ Alerts for suspicious activity
- ✅ Export audit logs to CSV
- ✅ Compliance reporting templates

---

## Testing Strategy

### Unit Tests

**Coverage Goals:**
- Conversation context: >80%
- Document sensitivity: >80%
- Audit logging: >80%

**Files:**
- `backend/tests/test_conversation_context.py`
- `backend/tests/test_document_sensitivity.py`
- `backend/tests/test_audit_logging.py`

### Integration Tests

**Scenarios:**
1. Full conversation lifecycle with context persistence
2. Document upload with sensitivity validation and audit logging
3. Output creation with audit logging
4. Audit log query and filtering

### End-to-End Tests

**User Flows:**
1. Create conversation → Send messages with context → Reload page → Verify context restored
2. Upload sensitive document → See validation error → Confirm → Upload succeeds → Check audit log
3. Admin queries audit logs → Filters by user → Filters by date range → Exports results

---

## Migration Strategy

### Database Migrations

**Order:**
1. `add_conversations_context_field.py` (Task A)
2. `add_document_sensitivity_fields.py` (Task B)

**Rollback Plan:**
- All migrations have downgrade functions
- Test rollback in development before production
- Backup database before running migrations in production

### Backward Compatibility

**Conversations:**
- Existing conversations get empty context `{}` by default
- Old code that doesn't send context will continue to work
- New code can populate context incrementally

**Documents:**
- Existing documents get `is_sensitive=false` by default
- Old uploads (without sensitivity_confirmed) will fail - **breaking change**
- Migration guide needed for API consumers

**Audit Logs:**
- No backward compatibility issues (new feature)
- Existing code doesn't depend on audit logs

---

## Risk Assessment

### High Risk

**Risk:** Chat.py in-memory storage migration breaks existing functionality
**Mitigation:**
- Comprehensive tests before migration
- Feature flag to toggle database storage
- Rollback plan ready

**Risk:** Sensitivity validation blocks legitimate uploads
**Mitigation:**
- Clear error messages
- Easy override for admins
- User education/documentation

### Medium Risk

**Risk:** Audit logging impacts performance
**Mitigation:**
- Async database writes
- Database indexes on audit_log table
- Performance testing

**Risk:** Context field grows too large (>1MB)
**Mitigation:**
- Limit artifacts array size (max 50 versions)
- Archive old artifacts
- Monitor context sizes

### Low Risk

**Risk:** Context structure changes break existing contexts
**Mitigation:**
- Version context structure
- Graceful handling of old formats
- Migration utilities if needed

---

## Success Metrics

### Functional Metrics
- ✅ Context persists across 100% of sessions
- ✅ Sensitivity validation rejects 100% of unconfirmed uploads
- ✅ Audit logging captures 100% of configured actions
- ✅ Zero data loss during context operations

### Performance Metrics
- ✅ Context save/restore < 50ms (p95)
- ✅ Audit logging overhead < 10ms per request (p95)
- ✅ Audit query endpoint < 500ms (p95)
- ✅ No degradation in chat response time

### Quality Metrics
- ✅ Test coverage >80% for all Phase 5 code
- ✅ Zero critical bugs in production
- ✅ All acceptance criteria met
- ✅ Documentation complete and accurate

---

## Documentation Updates

### API Documentation
- ✅ Update OpenAPI specs for new endpoints
- ✅ Add examples for context management
- ✅ Document sensitivity validation requirements
- ✅ Document audit log query parameters

### Developer Documentation
- ✅ Update `context/architecture.md` with Phase 5 changes
- ✅ Create migration guide for database changes
- ✅ Document audit logging patterns
- ✅ Update testing documentation

### User Documentation
- ✅ Guide: Understanding conversation context
- ✅ Guide: Document sensitivity best practices
- ✅ Admin guide: Using audit logs for compliance

---

## Timeline

### Week 1: Foundation (Tasks A-D)
**Days 1-2:** Database migrations
**Days 3-4:** Model updates (SQLAlchemy + Pydantic)
**Day 5:** Review and testing

### Week 2: Implementation (Tasks G, 1, E, 2, 3)
**Days 1-2:** Chat.py database migration + context handling
**Days 3-4:** Context endpoints + sensitivity validation
**Day 5:** Testing and bug fixes

### Week 3: Audit & Testing (Tasks 5, 6, 4, H, I)
**Days 1-2:** Audit logging middleware
**Day 3:** Audit query endpoints
**Days 4-5:** Comprehensive testing

### Week 4: Polish & Documentation (Optional)
**Days 1-2:** Bug fixes and refinements
**Days 3-4:** Documentation updates
**Day 5:** Final testing and deployment preparation

---

## Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Database migrations tested
- [ ] Rollback procedures documented
- [ ] Performance testing complete
- [ ] Documentation updated
- [ ] Code review complete

### Deployment
- [ ] Backup production database
- [ ] Run database migrations
- [ ] Deploy backend code
- [ ] Verify health checks
- [ ] Monitor error rates
- [ ] Verify audit logging is working

### Post-Deployment
- [ ] Smoke tests on production
- [ ] Monitor performance metrics
- [ ] Check audit log population
- [ ] Verify context persistence
- [ ] Review error logs
- [ ] Update stakeholders

---

## Appendix

### Existing Phase 5 Task IDs (for reference)

| Task ID | Title | Status |
|---------|-------|--------|
| `3b667845-89ad-4feb-8d83-286662e7373a` | Update conversation context handling | Modified |
| `8d5683cb-ec53-4b12-94d8-ec98c8077533` | Add document sensitivity validation | Modified |
| `85329282-900c-4745-b4a5-6a61bd5e0cf0` | Update document upload endpoint | Kept as-is |
| `5b3ba706-a1b0-400a-a6d3-70e6c4dc45fe` | Test conversation context persistence | Kept as-is |
| `8acc5555-4a88-4def-944f-c6ef7628712e` | Implement audit logging middleware | Modified |
| `af9035b8-6da9-4388-ac32-e7f4dd2b795d` | Create audit log viewing API endpoint | Kept as-is |

### Related Documents
- `/context/requirements.md` - Full application requirements
- `/context/project-context.md` - Project background and goals
- `/context/architecture.md` - System architecture
- `/context/phase-4-plan.md` - Previous phase (Outputs Dashboard)
- `/docs/testing-strategy.md` - Overall testing approach

### Contact
For questions about Phase 5 implementation, refer to project documentation or consult with the development team.

---

**Document Version:** 1.0
**Date Created:** 2024-11-03
**Last Updated:** 2024-11-03
**Status:** ✅ Planning Complete - Ready for Implementation
