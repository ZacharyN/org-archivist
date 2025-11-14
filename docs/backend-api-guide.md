# Backend API Guide for Nuxt 4 Frontend Development

**Document Version:** 1.0
**Last Updated:** 2025-11-10
**Target Audience:** Frontend developers working on the Nuxt 4 migration

---

## Table of Contents

1. [Overview & Quick Start](#1-overview--quick-start)
2. [Authentication & Authorization](#2-authentication--authorization)
3. [API Reference](#3-api-reference)
4. [Core Services & Business Logic](#4-core-services--business-logic)
5. [Database Schema](#5-database-schema)
6. [Integration Patterns](#6-integration-patterns)
7. [Configuration & Deployment](#7-configuration--deployment)
8. [Known Issues & Limitations](#8-known-issues--limitations)
9. [Nuxt 4 Integration Guide](#9-nuxt-4-integration-guide)

---

## 1. Overview & Quick Start

### 1.1 Project Purpose

Org Archivist is a RAG (Retrieval-Augmented Generation) application designed to help nonprofit organizations generate high-quality grant proposals, reports, and other documents by leveraging their historical organizational knowledge stored in past documents.

**Core Capabilities:**
- Document upload and intelligent processing (PDF, DOCX, TXT)
- Semantic + keyword hybrid search across document library
- AI-powered content generation using Claude
- Writing style analysis and application
- Conversation-based document creation
- Output tracking with success metrics

### 1.2 Technology Stack

**Backend Framework:**
- **FastAPI** (v0.115+) - Modern async Python web framework
- **Python 3.11+**
- **Pydantic** v2 - Data validation and serialization
- **SQLAlchemy** 2.0+ (async) - ORM for PostgreSQL

**Databases:**
- **PostgreSQL** 16+ - Primary relational database
- **Qdrant** - Vector database for embeddings

**AI/ML Services:**
- **Anthropic Claude** (Sonnet 4.5) - Text generation
- **OpenAI** or **Voyage AI** - Text embeddings
- **LlamaIndex** - Semantic text chunking and document processing

**Authentication:**
- **JWT** (JSON Web Tokens) - Token-based auth
- **bcrypt** - Password hashing

### 1.3 Architecture Overview

```mermaid
graph TB
    Client[Nuxt 4 Frontend]
    API[FastAPI Backend]
    PG[(PostgreSQL)]
    QD[(Qdrant Vector DB)]
    Claude[Claude API]
    Embed[Embedding API]

    Client -->|HTTP/SSE| API
    API -->|SQL Queries| PG
    API -->|Vector Search| QD
    API -->|Text Generation| Claude
    API -->|Generate Embeddings| Embed
    QD -->|Store Vectors| Embed
```

**Request Flow:**
1. Client authenticates → Receives JWT token
2. Client makes API request with Bearer token
3. Backend validates token and user permissions
4. Backend processes request (retrieves data, calls AI services)
5. Backend returns response (JSON or SSE stream)

### 1.4 Environment Setup

**Required Environment Variables:**

```bash
# API Keys (Required)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...              # If using OpenAI embeddings
VOYAGE_API_KEY=pa-...               # If using Voyage embeddings

# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/org_archivist
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=org_archivist
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Qdrant Configuration
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=foundation_docs
QDRANT_API_KEY=                    # Optional, for Qdrant Cloud

# Embedding Configuration
EMBEDDING_PROVIDER=openai          # Options: openai, voyage
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536          # Must match model output

# Claude Configuration
CLAUDE_MODEL=claude-sonnet-4-5-20250929
CLAUDE_TEMPERATURE=0.3
CLAUDE_MAX_TOKENS=4096
CLAUDE_TIMEOUT_SECONDS=60
CLAUDE_MAX_RETRIES=3

# Security
SECRET_KEY=your-secret-key-change-me
ENABLE_AUTH=true                   # Set to true for production
SESSION_TIMEOUT_MINUTES=60

# File Upload
MAX_FILE_SIZE_MB=50
MAX_BATCH_UPLOAD=20
ALLOWED_EXTENSIONS=pdf,docx,txt,doc

# Application
ENVIRONMENT=development            # Options: development, production
DEBUG=false
```

### 1.5 Docker Configuration

**Services:**

```yaml
services:
  postgres:
    image: postgres:16
    ports: ["5432:5432"]
    volumes: ["postgres_data:/var/lib/postgresql/data"]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333", "6334:6334"]
    volumes: ["qdrant_data:/qdrant/storage"]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [postgres, qdrant]
    environment: [See .env file]
```

**Starting the Backend:**

```bash
# Using Docker Compose
docker-compose up -d backend

# Backend will be available at:
http://localhost:8000

# API Documentation (Swagger UI):
http://localhost:8000/docs

# Alternative API docs (ReDoc):
http://localhost:8000/redoc
```

### 1.6 API Base URL

**Development:** `http://localhost:8000`
**API Prefix:** `/api`

All endpoints are prefixed with `/api` (e.g., `/api/auth/login`)

---

## 2. Authentication & Authorization

### 2.1 Authentication Flow

Org Archivist uses **JWT-based authentication** with session management.

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant DB

    Client->>API: POST /api/auth/login {email, password}
    API->>DB: Verify credentials
    DB-->>API: User validated
    API->>DB: Create session record
    API-->>Client: {access_token, refresh_token, user}

    Note over Client: Store tokens securely

    Client->>API: GET /api/documents (Bearer token)
    API->>DB: Validate session
    DB-->>API: Session valid, return user
    API-->>Client: Document list
```

### 2.2 Token Structure

**Access Token:**
- Type: JWT
- Lifespan:300 minutes (configurable via `SESSION_TIMEOUT_MINUTES`)
- Contains: `user_id`, `email`, `role`, `exp` (expiration)
- Must be included in `Authorization` header for all protected endpoints

**Refresh Token:**
- Type: JWT
- Lifespan: 7 days
- Used to obtain new access tokens (endpoint not yet implemented - see Known Issues)

### 2.3 Authentication Endpoints

#### Register New User

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "full_name": "Jane Doe",
  "role": "writer"
}
```

**Response (201 Created):**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "role": "writer",
  "is_active": true,
  "created_at": "2025-11-10T12:00:00Z"
}
```

**Validation Rules:**
- Email: Must be valid email format, unique
- Password: Minimum 8 characters
- Role: Must be one of: `admin`, `editor`, `writer`

#### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_at": "2025-11-10T13:00:00Z",
  "user": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "full_name": "Jane Doe",
    "role": "writer",
    "is_active": true
  }
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid credentials
- `400 Bad Request` - Malformed request

#### Logout

```http
POST /api/auth/logout
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

**Behavior:**
- Deletes session record from database
- Client should discard tokens

#### Validate Session

```http
GET /api/auth/session
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "valid": true,
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "expires_at": "2025-11-10T13:00:00Z"
}
```

**Use Case:** Check if current token is still valid before making requests

#### Get Current User

```http
GET /api/auth/me
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "role": "writer",
  "is_active": true,
  "created_at": "2025-11-10T12:00:00Z"
}
```

### 2.4 Role-Based Access Control (RBAC)

**Role Hierarchy:**

| Role | Level | Permissions |
|------|-------|-------------|
| **Admin** | 3 | Full system access, user management, system configuration, all CRUD operations |
| **Editor** | 2 | Create/edit/delete documents, writing styles, prompts, outputs; manage library |
| **Writer** | 1 | Create content, use chat, generate outputs, view library (read-only on settings) |

**Permission Matrix:**

| Feature | Writer | Editor | Admin |
|---------|--------|--------|-------|
| View documents | ✅ | ✅ | ✅ |
| Upload documents | ❌ | ✅ | ✅ |
| Delete documents | ❌ | ✅ | ✅ |
| Generate content | ✅ | ✅ | ✅ |
| Save outputs | ✅ | ✅ | ✅ |
| Create writing styles | ❌ | ✅ | ✅ |
| Delete writing styles | ❌ | ❌ | ✅ |
| Create prompt templates | ❌ | ✅ | ✅ |
| Delete prompt templates | ❌ | ❌ | ✅ |
| View audit logs | ❌ | ❌ | ✅ |
| Manage users | ❌ | ❌ | ✅ |
| System configuration | ❌ | ❌ | ✅ |

### 2.5 Authorization Implementation

**Protected Endpoints** require the `Authorization` header:

```http
Authorization: Bearer {access_token}
```

**Backend Dependencies (FastAPI):**

```python
# Defined in /backend/app/middleware/auth.py

get_current_user          # Extract and validate user from token
get_current_active_user   # Ensure user is active
require_writer            # Minimum: Writer role
require_editor            # Minimum: Editor role
require_admin             # Admin role only
```

**Endpoint Role Requirements:**

| Endpoint Pattern | Role Required |
|-----------------|---------------|
| `POST /api/documents/upload` | Editor+ |
| `DELETE /api/documents/{id}` | Editor+ |
| `POST /api/writing-styles/analyze` | Editor+ |
| `DELETE /api/writing-styles/{id}` | Admin |
| `DELETE /api/prompts/{id}` | Admin |
| `GET /api/audit` | Admin |
| `PUT /api/config` | Admin |
| All other authenticated endpoints | Any authenticated user (Writer+) |

### 2.6 Security Considerations

**Password Security:**
- Hashed using bcrypt with salt
- Minimum 8 characters (frontend should enforce stronger requirements)
- No password reset flow implemented yet (see Known Issues)

**Token Security:**
- Tokens stored in database with session metadata
- Include IP address and user agent for audit trail
- Sessions can be invalidated by admin
- Expired sessions cleaned up automatically

**CORS Configuration:**
- Configure allowed origins in production
- Currently allows all origins in development (see Configuration section)

**Rate Limiting:**
- Not currently implemented (see Known Issues)
- Recommend implementing at reverse proxy level (nginx, etc.)

---

## 3. API Reference

### 3.1 Documents API

**Base Path:** `/api/documents`

#### Upload Document

Upload and process a single document through the full RAG pipeline.

```http
POST /api/documents/upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

Form Fields:
- file: (binary) - PDF, DOCX, or TXT file
- metadata: (string) - JSON-encoded DocumentMetadata object
- sensitivity_confirmed: (boolean) - Must be true
```

**Metadata JSON Structure:**
```json
{
  "doc_type": "Grant Proposal",
  "programs": ["Education", "Youth Development"],
  "outcome": "Awarded",
  "year": 2023,
  "tags": ["federal", "department-of-education"],
  "notes": "Successful K-12 literacy program proposal",
  "is_sensitive": false,
  "sensitivity_level": "low"
}
```

**Metadata Field Constraints:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `doc_type` | string | Yes | One of: "Grant Proposal", "Grant Report", "Case Study", "Annual Report", "Other" |
| `programs` | string[] | Yes | Each must be one of: "Education", "Health", "Environment", "Arts & Culture", "Youth Development", "Economic Development", "Housing", "Other" |
| `outcome` | string | Yes | One of: "Awarded", "Not Awarded", "Pending", "N/A" |
| `year` | integer | Yes | Between 1900 and 2100 |
| `tags` | string[] | No | Free-form tags for categorization |
| `notes` | string | No | Additional context or notes |
| `is_sensitive` | boolean | No | Whether document contains sensitive information |
| `sensitivity_level` | string | No | One of: "low", "medium", "high" |

**Processing Pipeline:**
1. Validate file type and size (max 50MB, configured in settings)
2. Extract text content (PDF/DOCX/TXT)
3. Chunk text semantically (500 char chunks, 50 char overlap)
4. Generate embeddings for each chunk
5. Store vectors in Qdrant with metadata
6. Save document record to PostgreSQL
7. Return document info with chunk count

**Response (200 OK):**
```json
{
  "doc_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "education-proposal-2023.pdf",
  "doc_type": "Grant Proposal",
  "programs": ["Education", "Youth Development"],
  "outcome": "Awarded",
  "year": 2023,
  "tags": ["federal", "department-of-education"],
  "notes": "Successful K-12 literacy program proposal",
  "file_size": 2457600,
  "chunks_count": 45,
  "upload_date": "2025-11-10T12:00:00Z",
  "created_by": "user@example.com",
  "is_sensitive": false,
  "sensitivity_level": "low"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid file type, size exceeded, or malformed metadata
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Insufficient permissions (requires Editor+)
- `413 Payload Too Large` - File exceeds size limit
- `422 Unprocessable Entity` - Validation errors in metadata

#### List Documents

Retrieve documents with optional filtering and pagination.

```http
GET /api/documents?doc_type={type}&year={year}&outcome={outcome}&programs={program}&skip={skip}&limit={limit}
Authorization: Bearer {access_token}
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `doc_type` | string | Filter by document type |
| `year` | integer | Filter by year |
| `outcome` | string | Filter by outcome |
| `programs` | string | Filter by program (note: currently filters in-memory) |
| `skip` | integer | Number of records to skip (default: 0) |
| `limit` | integer | Max records to return (default: 100) |

**Response (200 OK):**
```json
{
  "documents": [
    {
      "doc_id": "123e4567-e89b-12d3-a456-426614174000",
      "filename": "education-proposal-2023.pdf",
      "doc_type": "Grant Proposal",
      "programs": ["Education", "Youth Development"],
      "outcome": "Awarded",
      "year": 2023,
      "tags": ["federal"],
      "file_size": 2457600,
      "chunks_count": 45,
      "upload_date": "2025-11-10T12:00:00Z",
      "is_sensitive": false
    }
  ],
  "pagination": {
    "total": 150,
    "page": 1,
    "per_page": 100,
    "total_pages": 2,
    "has_next": true,
    "has_previous": false
  }
}
```

#### Get Document Details

Retrieve details for a specific document.

```http
GET /api/documents/{doc_id}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "doc_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "education-proposal-2023.pdf",
  "doc_type": "Grant Proposal",
  "programs": ["Education", "Youth Development"],
  "outcome": "Awarded",
  "year": 2023,
  "tags": ["federal", "department-of-education"],
  "notes": "Successful K-12 literacy program proposal",
  "file_size": 2457600,
  "chunks_count": 45,
  "upload_date": "2025-11-10T12:00:00Z",
  "created_by": "user@example.com",
  "updated_at": "2025-11-10T12:00:00Z",
  "is_sensitive": false,
  "sensitivity_level": "low",
  "sensitivity_confirmed_at": "2025-11-10T12:00:00Z"
}
```

**Error Responses:**
- `404 Not Found` - Document doesn't exist
- `401 Unauthorized` - Missing or invalid token

#### Get Library Statistics

Retrieve aggregate statistics about the document library.

```http
GET /api/documents/stats
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "total_documents": 150,
  "total_chunks": 6750,
  "by_type": {
    "Grant Proposal": 80,
    "Grant Report": 45,
    "Case Study": 15,
    "Annual Report": 10
  },
  "by_outcome": {
    "Awarded": 65,
    "Not Awarded": 10,
    "Pending": 5,
    "N/A": 70
  },
  "by_year": {
    "2023": 45,
    "2022": 40,
    "2021": 35,
    "2020": 30
  },
  "by_program": {
    "Education": 60,
    "Health": 45,
    "Youth Development": 30,
    "Environment": 15
  }
}
```

#### Delete Document

Delete a document and all associated vector embeddings.

```http
DELETE /api/documents/{doc_id}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "message": "Document deleted successfully",
  "doc_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Behavior:**
- Deletes document record from PostgreSQL
- Deletes all associated chunks from Qdrant
- Cascade deletes any references (outputs, etc.)

**Error Responses:**
- `404 Not Found` - Document doesn't exist
- `403 Forbidden` - Insufficient permissions (requires Editor+)
- `401 Unauthorized` - Missing or invalid token

### 3.2 Query & Generation API

**Base Path:** `/api/query`

#### Generate Content (Non-Streaming)

Generate content using RAG pipeline, returns complete response.

```http
POST /api/query
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "query": "Describe our organization's experience with K-12 literacy programs",
  "audience": "Federal RFP",
  "section": "Organizational Capacity",
  "tone": "professional",
  "max_sources": 5,
  "recency_weight": 0.7,
  "include_citations": true,
  "filters": {
    "doc_types": ["Grant Proposal", "Grant Report"],
    "programs": ["Education"],
    "outcomes": ["Awarded"],
    "years": [2022, 2023],
    "tags": ["literacy"]
  },
  "custom_instructions": "Focus on measurable outcomes and student impact",
  "max_tokens": 2048,
  "temperature": 0.3
}
```

**Request Fields:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `query` | string | Yes | User's content request | Min 10 characters |
| `audience` | string | Yes | Target audience | One of: "Federal RFP", "Foundation Grant", "Corporate Sponsor", "Annual Report", "Board Report", "Public Communication" |
| `section` | string | Yes | Document section type | One of: "Organizational Capacity", "Program Description", "Needs Statement", "Evaluation Plan", "Budget Narrative", "Sustainability Plan", "Executive Summary" |
| `tone` | string | No | Writing tone | Free-form (e.g., "professional", "compelling", "data-driven") |
| `max_sources` | integer | No | Max chunks to retrieve | 1-15 (default: 5) |
| `recency_weight` | float | No | Weight for recent docs | 0.0-1.0 (default: 0.7) |
| `include_citations` | boolean | No | Include source citations | Default: true |
| `filters` | object | No | Metadata filters | See DocumentFilters below |
| `custom_instructions` | string | No | Additional instructions | Max 500 characters |
| `max_tokens` | integer | No | Claude response limit | 512-8192 (default: 4096) |
| `temperature` | float | No | Claude creativity | 0.0-1.0 (default: 0.3) |

**DocumentFilters Object:**
```json
{
  "doc_types": ["Grant Proposal", "Grant Report"],
  "programs": ["Education", "Youth Development"],
  "outcomes": ["Awarded"],
  "years": [2022, 2023],
  "tags": ["literacy", "k-12"]
}
```

**Response (200 OK):**
```json
{
  "content": "Our organization has demonstrated strong capacity in K-12 literacy programming through multiple successful initiatives...",
  "sources": [
    {
      "doc_id": "123e4567-e89b-12d3-a456-426614174000",
      "filename": "education-proposal-2023.pdf",
      "chunk_id": "chunk_001",
      "relevance_score": 0.89,
      "text": "In our 2023 K-12 literacy program, we served 500 students...",
      "doc_type": "Grant Proposal",
      "year": 2023,
      "programs": ["Education"]
    }
  ],
  "metadata": {
    "total_sources": 5,
    "tokens_used": 1847,
    "model": "claude-sonnet-4-5-20250929",
    "temperature": 0.3,
    "retrieval_time_ms": 145,
    "generation_time_ms": 3240
  }
}
```

**Error Responses:**
- `400 Bad Request` - Validation errors
- `401 Unauthorized` - Missing or invalid token
- `500 Internal Server Error` - Claude API error or processing failure

#### Generate Content (Streaming)

Generate content with Server-Sent Events (SSE) streaming for real-time response.

```http
POST /api/query/stream
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "query": "Describe our K-12 literacy programs",
  "audience": "Federal RFP",
  "section": "Program Description",
  "max_sources": 5
}
```

**Request Body:** Same as non-streaming endpoint

**Response:** Server-Sent Events (SSE) stream

**Event Types:**

1. **sources** - Retrieved context sources
```
event: sources
data: {"sources": [...]}
```

2. **content** - Generated text chunks
```
event: content
data: {"content": "Our organization has "}

event: content
data: {"content": "demonstrated strong "}
```

3. **done** - Stream complete
```
event: done
data: {"metadata": {"tokens_used": 1847, ...}}
```

4. **error** - Processing error
```
event: error
data: {"error": "Failed to generate content", "detail": "..."}
```

**Client Implementation Example:**
```javascript
const eventSource = new EventSource('/api/query/stream', {
  headers: { 'Authorization': `Bearer ${token}` }
});

eventSource.addEventListener('sources', (e) => {
  const data = JSON.parse(e.data);
  // Display sources to user
});

eventSource.addEventListener('content', (e) => {
  const data = JSON.parse(e.data);
  // Append content chunk to display
});

eventSource.addEventListener('done', (e) => {
  const data = JSON.parse(e.data);
  eventSource.close();
  // Show completion, display metadata
});

eventSource.addEventListener('error', (e) => {
  const data = JSON.parse(e.data);
  eventSource.close();
  // Show error to user
});
```

### 3.3 Chat API

**Base Path:** `/api/chat`

#### Send Chat Message

Send a message in a conversation context (non-streaming).

```http
POST /api/chat
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "message": "What experience do we have with after-school programs?",
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "context": {
    "audience": "Foundation Grant",
    "section": "Program Description",
    "working_doc_id": "output_123"
  },
  "filters": {
    "programs": ["Education", "Youth Development"],
    "years": [2022, 2023]
  },
  "max_sources": 5
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | User's message/question |
| `conversation_id` | string (UUID) | No | Existing conversation ID (omit for new conversation) |
| `context` | object | No | Conversation context (persisted across messages) |
| `filters` | object | No | Document filters for retrieval |
| `max_sources` | integer | No | Max sources to retrieve (default: 5) |

**Response (200 OK):**
```json
{
  "message_id": "msg_123",
  "conversation_id": "conv_123",
  "role": "assistant",
  "content": "Based on our historical work, we have extensive experience with after-school programs...",
  "sources": [
    {
      "doc_id": "123e4567",
      "filename": "youth-dev-report-2023.pdf",
      "text": "Our after-school program served 200 students...",
      "relevance_score": 0.92
    }
  ],
  "created_at": "2025-11-10T12:00:00Z"
}
```

#### Stream Chat Response

Stream chat response using SSE.

```http
POST /api/chat/stream
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "message": "Tell me about our health programs",
  "conversation_id": "conv_123"
}
```

**Response:** SSE stream (same format as `/api/query/stream`)

#### List Conversations

Get all conversations for the current user.

```http
GET /api/chat/conversations
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "conversations": [
    {
      "conversation_id": "conv_123",
      "name": "Education Grant Discussion",
      "created_at": "2025-11-10T10:00:00Z",
      "updated_at": "2025-11-10T12:00:00Z",
      "message_count": 12,
      "context": {
        "audience": "Federal RFP",
        "section": "Program Description"
      }
    }
  ]
}
```

#### Get Conversation Details

Retrieve a conversation with all messages.

```http
GET /api/chat/conversations/{conversation_id}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "conversation_id": "conv_123",
  "name": "Education Grant Discussion",
  "created_at": "2025-11-10T10:00:00Z",
  "updated_at": "2025-11-10T12:00:00Z",
  "context": {
    "audience": "Federal RFP",
    "section": "Program Description"
  },
  "messages": [
    {
      "message_id": "msg_001",
      "role": "user",
      "content": "What's our experience with K-12 literacy?",
      "created_at": "2025-11-10T10:00:00Z"
    },
    {
      "message_id": "msg_002",
      "role": "assistant",
      "content": "Based on our records...",
      "sources": [...],
      "created_at": "2025-11-10T10:00:30Z"
    }
  ]
}
```

#### Delete Conversation

Delete a conversation and all messages.

```http
DELETE /api/chat/conversations/{conversation_id}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "message": "Conversation deleted successfully"
}
```

### 3.4 Writing Styles API

**Base Path:** `/api/writing-styles`

#### Analyze Writing Samples

Use AI to analyze writing samples and create a style profile.

```http
POST /api/writing-styles/analyze
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "samples": [
    "Sample text 1 demonstrating writing style...",
    "Sample text 2 with similar characteristics...",
    "Sample text 3 for pattern analysis..."
  ],
  "style_type": "grant"
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `samples` | string[] | Yes | 2-5 writing samples (min 100 chars each) |
| `style_type` | string | No | One of: "grant", "proposal", "report", "general" |

**Response (200 OK):**
```json
{
  "analysis": {
    "tone": "professional, data-driven",
    "sentence_structure": "mix of simple and complex sentences",
    "vocabulary_level": "sophisticated with technical terminology",
    "key_patterns": [
      "Uses evidence-based language",
      "Includes specific metrics and outcomes",
      "Employs active voice predominantly"
    ]
  },
  "suggested_prompt": "Write in a professional, data-driven tone using a mix of simple and complex sentences...",
  "sample_count": 3
}
```

#### Create Writing Style

Create a custom writing style for content generation.

```http
POST /api/writing-styles
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Federal Grant Style 2023",
  "type": "grant",
  "description": "Writing style based on successful 2023 federal grant proposals",
  "prompt_content": "Write in a professional, evidence-based tone using active voice...",
  "samples": ["sample1", "sample2"],
  "active": true
}
```

**Response (201 Created):**
```json
{
  "style_id": "style_123",
  "name": "Federal Grant Style 2023",
  "type": "grant",
  "description": "Writing style based on successful 2023 federal grant proposals",
  "prompt_content": "Write in a professional, evidence-based tone...",
  "sample_count": 2,
  "active": true,
  "created_at": "2025-11-10T12:00:00Z",
  "created_by": "user_123"
}
```

#### List Writing Styles

Retrieve all writing styles with optional filtering.

```http
GET /api/writing-styles?type={type}&active={true|false}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "styles": [
    {
      "style_id": "style_123",
      "name": "Federal Grant Style 2023",
      "type": "grant",
      "description": "Based on successful federal proposals",
      "sample_count": 3,
      "active": true,
      "created_at": "2025-11-10T12:00:00Z"
    }
  ]
}
```

#### Get Writing Style

Retrieve specific writing style details.

```http
GET /api/writing-styles/{style_id}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "style_id": "style_123",
  "name": "Federal Grant Style 2023",
  "type": "grant",
  "description": "Writing style based on successful 2023 federal grant proposals",
  "prompt_content": "Write in a professional, evidence-based tone using active voice...",
  "samples": ["Full sample text 1...", "Full sample text 2..."],
  "analysis_metadata": {
    "analyzed_at": "2025-11-10T12:00:00Z",
    "model_used": "claude-sonnet-4-5-20250929",
    "confidence": 0.92
  },
  "sample_count": 2,
  "active": true,
  "created_at": "2025-11-10T12:00:00Z",
  "updated_at": "2025-11-10T12:00:00Z",
  "created_by": "user_123"
}
```

#### Update Writing Style

Modify an existing writing style.

```http
PUT /api/writing-styles/{style_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Updated Style Name",
  "active": false
}
```

**Response (200 OK):**
```json
{
  "style_id": "style_123",
  "name": "Updated Style Name",
  "active": false,
  "updated_at": "2025-11-10T12:30:00Z"
}
```

#### Delete Writing Style

Delete a writing style (Admin only).

```http
DELETE /api/writing-styles/{style_id}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "message": "Writing style deleted successfully"
}
```

### 3.5 Outputs API

**Base Path:** `/api/outputs`

Outputs are saved/tracked generated content with success metrics.

#### List Outputs

Retrieve saved outputs with filtering.

```http
GET /api/outputs?output_type={type}&status={status}&skip={skip}&limit={limit}
Authorization: Bearer {access_token}
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `output_type` | string | Filter by type: "Grant Proposal", "Grant Report", etc. |
| `status` | string | Filter by status: "draft", "submitted", "pending", "awarded", "not_awarded" |
| `skip` | integer | Pagination offset (default: 0) |
| `limit` | integer | Max results (default: 50) |

**Response (200 OK):**
```json
{
  "outputs": [
    {
      "output_id": "output_123",
      "title": "2024 Education Grant Proposal - DOE",
      "output_type": "Grant Proposal",
      "status": "awarded",
      "word_count": 3500,
      "funder_name": "Department of Education",
      "requested_amount": 250000.00,
      "awarded_amount": 225000.00,
      "submission_date": "2024-03-15",
      "decision_date": "2024-05-20",
      "created_at": "2024-03-10T10:00:00Z",
      "updated_at": "2024-05-20T14:00:00Z"
    }
  ],
  "pagination": {
    "total": 45,
    "page": 1,
    "per_page": 10,
    "total_pages": 5,
    "has_next": true,
    "has_previous": false
  }
}
```

#### Create Output

Save generated content as an output.

```http
POST /api/outputs
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "conversation_id": "conv_123",
  "title": "2024 Education Grant Proposal - DOE",
  "output_type": "Grant Proposal",
  "content": "Full proposal text here...",
  "word_count": 3500,
  "status": "draft",
  "writing_style_id": "style_123",
  "funder_name": "Department of Education",
  "requested_amount": 250000.00,
  "metadata": {
    "program_focus": "K-12 Literacy",
    "grant_type": "Federal",
    "deadline": "2024-03-20"
  }
}
```

**Response (201 Created):**
```json
{
  "output_id": "output_123",
  "title": "2024 Education Grant Proposal - DOE",
  "output_type": "Grant Proposal",
  "content": "Full proposal text...",
  "word_count": 3500,
  "status": "draft",
  "created_at": "2024-03-10T10:00:00Z"
}
```

#### Get Output

Retrieve specific output with full content.

```http
GET /api/outputs/{output_id}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "output_id": "output_123",
  "conversation_id": "conv_123",
  "title": "2024 Education Grant Proposal - DOE",
  "output_type": "Grant Proposal",
  "content": "Full proposal text here...",
  "word_count": 3500,
  "status": "awarded",
  "writing_style_id": "style_123",
  "funder_name": "Department of Education",
  "requested_amount": 250000.00,
  "awarded_amount": 225000.00,
  "submission_date": "2024-03-15",
  "decision_date": "2024-05-20",
  "success_notes": "Funded at 90% of requested amount. Start date September 2024.",
  "metadata": {
    "program_focus": "K-12 Literacy",
    "grant_type": "Federal"
  },
  "created_by": "user@example.com",
  "created_at": "2024-03-10T10:00:00Z",
  "updated_at": "2024-05-20T14:00:00Z"
}
```

#### Update Output

Update output status, amounts, or other tracking information.

```http
PUT /api/outputs/{output_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "status": "awarded",
  "awarded_amount": 225000.00,
  "decision_date": "2024-05-20",
  "success_notes": "Funded at 90% of requested amount."
}
```

**Response (200 OK):**
```json
{
  "output_id": "output_123",
  "status": "awarded",
  "awarded_amount": 225000.00,
  "updated_at": "2024-05-20T14:00:00Z"
}
```

#### Delete Output

Delete an output.

```http
DELETE /api/outputs/{output_id}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "message": "Output deleted successfully"
}
```

### 3.6 Prompt Templates API

**Base Path:** `/api/prompts`

Prompt templates are reusable prompt structures for consistent content generation.

#### List Prompt Templates

```http
GET /api/prompts?category={category}&active={true|false}
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `category`: Filter by category (e.g., "needs_statement", "budget_narrative")
- `active`: Filter by active status

**Response (200 OK):**
```json
{
  "prompts": [
    {
      "prompt_id": "prompt_123",
      "name": "Needs Statement - Education",
      "category": "needs_statement",
      "active": true,
      "version": 1,
      "created_at": "2025-11-10T12:00:00Z"
    }
  ]
}
```

#### Create Prompt Template

```http
POST /api/prompts
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Needs Statement - Education",
  "category": "needs_statement",
  "content": "Write a compelling needs statement for an education program addressing {problem}. Focus on {population} and include relevant statistics from our historical work.",
  "variables": ["problem", "population"],
  "active": true
}
```

**Response (201 Created):**
```json
{
  "prompt_id": "prompt_123",
  "name": "Needs Statement - Education",
  "category": "needs_statement",
  "content": "Write a compelling needs statement...",
  "variables": ["problem", "population"],
  "active": true,
  "version": 1,
  "created_at": "2025-11-10T12:00:00Z"
}
```

#### Get Prompt Template

```http
GET /api/prompts/{prompt_id}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "prompt_id": "prompt_123",
  "name": "Needs Statement - Education",
  "category": "needs_statement",
  "content": "Write a compelling needs statement for an education program addressing {problem}...",
  "variables": ["problem", "population"],
  "active": true,
  "version": 1,
  "created_at": "2025-11-10T12:00:00Z",
  "updated_at": "2025-11-10T12:00:00Z"
}
```

#### Update Prompt Template

```http
PUT /api/prompts/{prompt_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "content": "Updated prompt content...",
  "active": false
}
```

**Response (200 OK):**
```json
{
  "prompt_id": "prompt_123",
  "name": "Needs Statement - Education",
  "content": "Updated prompt content...",
  "active": false,
  "version": 2,
  "updated_at": "2025-11-10T13:00:00Z"
}
```

#### Delete Prompt Template

```http
DELETE /api/prompts/{prompt_id}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "message": "Prompt template deleted successfully"
}
```

### 3.7 Programs API

**Base Path:** `/api/programs`

Programs are organizational categories used to tag and filter documents (e.g., "Education", "Health", "Youth Development"). The Programs API allows management of program definitions with proper access control.

#### List Programs

Retrieve all programs with optional filtering.

```http
GET /api/programs?active_only={true|false}&skip={skip}&limit={limit}
Authorization: Bearer {access_token}
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `active_only` | boolean | Only return active programs (default: false) |
| `skip` | integer | Pagination offset (default: 0) |
| `limit` | integer | Max results to return (default: 100) |

**Response (200 OK):**
```json
{
  "programs": [
    {
      "program_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Youth Development",
      "description": "Programs focused on youth ages 13-18",
      "display_order": 10,
      "active": true,
      "created_at": "2025-11-14T12:00:00Z",
      "updated_at": "2025-11-14T12:00:00Z",
      "created_by": "123e4567-e89b-12d3-a456-426614174000"
    },
    {
      "program_id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Education",
      "description": "Educational programs and initiatives",
      "display_order": 9,
      "active": true,
      "created_at": "2025-11-14T12:00:00Z",
      "updated_at": "2025-11-14T12:00:00Z",
      "created_by": "123e4567-e89b-12d3-a456-426614174000"
    }
  ],
  "total": 6,
  "active_count": 5,
  "inactive_count": 1
}
```

**Sorting:** Programs are sorted by `display_order` (descending) then by `name` (ascending).

#### Get Program

Retrieve a specific program by ID.

```http
GET /api/programs/{program_id}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "program_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Youth Development",
  "description": "Programs focused on youth ages 13-18",
  "display_order": 10,
  "active": true,
  "created_at": "2025-11-14T12:00:00Z",
  "updated_at": "2025-11-14T12:00:00Z",
  "created_by": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Error Responses:**
- `404 Not Found` - Program doesn't exist

#### Create Program

Create a new program (Editor+ role required).

```http
POST /api/programs
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Early Childhood Education",
  "description": "Programs for children ages 0-5",
  "display_order": 8,
  "active": true
}
```

**Request Fields:**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `name` | string | Yes | Program name | 1-100 chars, unique, letters/numbers/spaces/-/'& only |
| `description` | string | No | Program description | Max 500 characters |
| `display_order` | integer | No | Sort order (higher appears first) | 0-1000 (default: 0) |
| `active` | boolean | No | Whether program is active | Default: true |

**Response (201 Created):**
```json
{
  "program_id": "550e8400-e29b-41d4-a716-446655440002",
  "name": "Early Childhood Education",
  "description": "Programs for children ages 0-5",
  "display_order": 8,
  "active": true,
  "created_at": "2025-11-14T12:00:00Z",
  "updated_at": "2025-11-14T12:00:00Z",
  "created_by": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Error Responses:**
- `400 Bad Request` - Validation errors
- `403 Forbidden` - Insufficient permissions (requires Editor+)
- `409 Conflict` - Program name already exists

#### Update Program

Update an existing program (Admin role required).

```http
PUT /api/programs/{program_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "description": "Updated description for early childhood programs",
  "active": true,
  "display_order": 15
}
```

**Request Body:** All fields are optional. Only provided fields will be updated.

**Response (200 OK):**
```json
{
  "program_id": "550e8400-e29b-41d4-a716-446655440002",
  "name": "Early Childhood Education",
  "description": "Updated description for early childhood programs",
  "display_order": 15,
  "active": true,
  "created_at": "2025-11-14T12:00:00Z",
  "updated_at": "2025-11-14T14:30:00Z",
  "created_by": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Error Responses:**
- `404 Not Found` - Program doesn't exist
- `403 Forbidden` - Insufficient permissions (requires Admin)
- `409 Conflict` - New name conflicts with existing program

#### Delete Program

Delete a program (Admin role required).

```http
DELETE /api/programs/{program_id}?force={true|false}
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `force` (boolean, default: false) - If true, delete even if documents use this program

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Program deleted successfully",
  "program_id": "550e8400-e29b-41d4-a716-446655440002",
  "documents_affected": 12
}
```

**Behavior:**
- By default, prevents deletion if documents reference the program
- With `force=true`, deletes program and removes associations from documents
- Returns count of affected documents

**Error Responses:**
- `404 Not Found` - Program doesn't exist
- `403 Forbidden` - Insufficient permissions (requires Admin)
- `409 Conflict` - Program in use and force=false

#### Get Program Statistics

Get aggregate statistics about programs and their usage.

```http
GET /api/programs/stats
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "total_programs": 6,
  "active_programs": 5,
  "inactive_programs": 1,
  "program_document_counts": {
    "Education": 67,
    "Youth Development": 45,
    "Health": 38,
    "Early Childhood": 32,
    "Family Support": 28,
    "Environment": 15
  }
}
```

**Use Cases:**
- Dashboard statistics
- Program usage analysis
- Identifying underutilized programs
- Planning program cleanup or consolidation

### 3.8 System & Admin API

#### Health Check

Check API health status.

```http
GET /api/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-10T12:00:00Z"
}
```

#### Metrics

Get application metrics (no auth required currently).

```http
GET /api/metrics
```

**Response (200 OK):**
```json
{
  "uptime_seconds": 86400,
  "total_requests": 15234,
  "total_generations": 523,
  "avg_generation_time_ms": 3240
}
```

#### Get System Configuration

Get system configuration (Admin only).

```http
GET /api/config
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "embedding_provider": "openai",
  "embedding_model": "text-embedding-3-small",
  "claude_model": "claude-sonnet-4-5-20250929",
  "max_file_size_mb": 50,
  "session_timeout_minutes": 60
}
```

#### Update System Configuration

Update system settings (Admin only).

```http
PUT /api/config
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "session_timeout_minutes": 120
}
```

**Response (200 OK):**
```json
{
  "session_timeout_minutes": 120,
  "updated_at": "2025-11-10T12:00:00Z"
}
```

#### View Audit Log

View system audit log (Admin only).

```http
GET /api/audit?event_type={type}&entity_type={entity}&skip={skip}&limit={limit}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "logs": [
    {
      "log_id": "log_123",
      "event_type": "document_upload",
      "entity_type": "document",
      "entity_id": "doc_123",
      "user_id": "user_123",
      "details": {
        "filename": "proposal.pdf",
        "file_size": 2457600
      },
      "created_at": "2025-11-10T12:00:00Z"
    }
  ],
  "total": 1
}
```

---

## 4. Core Services & Business Logic

### 4.1 Document Processing Pipeline

**Service:** `DocumentProcessor` (`/backend/app/services/document_processor.py`)

**Pipeline Flow:**

```mermaid
graph LR
    A[Upload File] --> B[Extract Text]
    B --> C[Semantic Chunking]
    C --> D[Generate Embeddings]
    D --> E[Store in Qdrant]
    E --> F[Save Metadata]
    F --> G[Return Document Info]
```

**Components:**

1. **Text Extraction**
   - PDF: PyPDF2 or pdfplumber
   - DOCX: python-docx
   - TXT: Direct read
   - Handles encoding issues, extracts clean text

2. **Semantic Chunking** (LlamaIndex `SentenceSplitter`)
   - Chunks text based on semantic boundaries (sentences, paragraphs)
   - Default: 512 tokens per chunk (not characters)
   - Overlap: 50 tokens (~10%)
   - Preserves context across chunk boundaries
   - Three strategies available: SENTENCE (default), SEMANTIC, TOKEN
   - Configuration: `/backend/app/services/chunking_service.py`

3. **Embedding Generation**
   - OpenAI: `text-embedding-3-small` (1536 dims)
   - Voyage: `voyage-2` (1024 dims)
   - Batch processing for efficiency
   - Retry logic for API failures

4. **Vector Storage** (Qdrant)
   - Creates point per chunk with metadata
   - Metadata includes: doc_id, filename, chunk_index, doc_type, programs, year, outcome
   - Supports filtered search

5. **Metadata Persistence** (PostgreSQL)
   - Saves document record with all metadata
   - Tracks chunk count, file size, upload date
   - Links to user who uploaded

### 4.2 RAG Retrieval Engine

**Service:** `RetrievalEngine` (`/backend/app/services/retrieval_engine.py`)

**Hybrid Search Architecture:**

```mermaid
graph TB
    Query[User Query] --> VectorSearch[Vector Similarity]
    Query --> KeywordSearch[BM25 Keyword]
    VectorSearch --> Merge[Merge & Rank]
    KeywordSearch --> Merge
    Merge --> Filter[Apply Filters]
    Filter --> Recency[Apply Recency Weight]
    Recency --> Diversify[Diversify Sources]
    Diversify --> Rerank[Optional Reranking]
    Rerank --> Results[Top K Results]
```

**Search Process:**

1. **Vector Search** (Weight: 0.7)
   - Generate query embedding
   - Search Qdrant for similar chunks
   - Returns top N results with similarity scores

2. **Keyword Search** (Weight: 0.3)
   - BM25L algorithm for keyword matching
   - Handles exact phrase matching
   - Complements semantic search

3. **Merge & Rank**
   - Combines results from both searches
   - Weighted scoring: `final_score = 0.7 * vector_score + 0.3 * keyword_score`
   - Deduplicates results

4. **Metadata Filtering**
   - Applies user-specified filters (doc_type, programs, year, outcome, tags)
   - Efficient filtering at vector store level

5. **Recency Weighting**
   - Boosts scores for recent documents
   - Formula: `adjusted_score = base_score * (1 + recency_weight * recency_factor)`
   - `recency_factor` based on document year vs current year

6. **Source Diversification**
   - Ensures results come from multiple documents
   - Prevents single document domination
   - Maintains relevance while adding variety

7. **Optional Reranking**
   - Uses Cohere or similar reranking model
   - Re-scores results based on query-chunk relevance
   - Improves precision of top results

**Configuration:**
- `DEFAULT_TOP_K`: 5 (number of chunks to retrieve)
- `MIN_SIMILARITY_THRESHOLD`: 0.7 (minimum relevance score)
- `VECTOR_SEARCH_WEIGHT`: 0.7
- `KEYWORD_SEARCH_WEIGHT`: 0.3
- `DEFAULT_RECENCY_WEIGHT`: 0.7

### 4.3 Claude Generation Service

**Service:** `GenerationService` (`/backend/app/services/generation_service.py`)

**Generation Flow:**

```mermaid
graph LR
    A[Query + Context] --> B[Build Prompt]
    B --> C[Call Claude API]
    C --> D[Stream/Complete]
    D --> E[Validate Citations]
    E --> F[Return Response]
```

**Components:**

1. **Prompt Construction**
   - System prompt with guidelines
   - User query and requirements
   - Retrieved context chunks
   - Source attribution instructions
   - Audience and section-specific guidance

2. **Claude API Integration**
   - Model: `claude-sonnet-4-5-20250929`
   - Supports streaming (SSE) and non-streaming
   - Configurable temperature (0.0-1.0, default: 0.3)
   - Configurable max_tokens (512-8192, default: 4096)
   - Automatic retry on API errors (max 3 retries)

3. **Citation Validation**
   - Extracts citations from generated content
   - Validates citations reference actual source chunks
   - Removes hallucinated citations
   - Formats citations consistently

4. **Response Post-Processing**
   - Cleans up formatting
   - Ensures proper citation format
   - Tracks token usage
   - Records generation metadata

**Streaming Implementation:**
- Uses Server-Sent Events (SSE)
- Emits events: `sources`, `content`, `done`, `error`
- Client receives real-time content generation
- Enables responsive UX

### 4.4 Writing Style Analysis

**Service:** `StyleAnalysisService` (`/backend/app/services/style_analysis.py`)

**Analysis Process:**

1. **Sample Validation**
   - Minimum 2 samples, maximum 5
   - Each sample minimum 100 characters
   - Checks for sufficient variation

2. **AI Analysis**
   - Uses Claude to analyze writing samples
   - Identifies patterns in:
     - Tone and voice
     - Sentence structure
     - Vocabulary level
     - Rhetorical devices
     - Formatting conventions

3. **Prompt Generation**
   - Creates reusable prompt based on analysis
   - Encodes style characteristics
   - Designed for consistent application

4. **Style Application**
   - Injects style prompt into generation context
   - Guides Claude to match target style
   - Maintains content accuracy while matching tone

### 4.5 Vector Store Operations

**Service:** `VectorStore` (`/backend/app/services/vector_store.py`)

**Qdrant Operations:**

1. **Collection Management**
   - Creates collection with specified dimensions
   - Configures distance metric (cosine similarity)
   - Sets up indexes for metadata filtering

2. **Vector Operations**
   - **Insert**: Add vectors with metadata
   - **Search**: Query by vector similarity
   - **Filter**: Apply metadata filters during search
   - **Delete**: Remove vectors by doc_id or point_id
   - **Update**: Modify metadata without re-embedding

3. **Batch Operations**
   - Batch inserts for efficiency
   - Batch size: 100 points
   - Parallel processing for large documents

4. **Metadata Schema**
   ```python
   {
     "doc_id": "UUID",
     "filename": "string",
     "chunk_index": int,
     "doc_type": "string",
     "programs": ["string"],
     "year": int,
     "outcome": "string",
     "tags": ["string"],
     "chunk_text": "string"
   }
   ```

### 4.6 Database Service

**Service:** `DatabaseService` (`/backend/app/services/database.py`)

**PostgreSQL Operations:**

1. **Document CRUD**
   - Create document records
   - Query with filters (type, year, outcome, programs)
   - Update metadata
   - Delete documents (cascade to related records)

2. **User Management**
   - Create users with hashed passwords
   - Authenticate users
   - Update user profiles
   - Manage user roles

3. **Session Management**
   - Create sessions with tokens
   - Validate active sessions
   - Cleanup expired sessions
   - Track session metadata (IP, user agent)

4. **Query Builder**
   - Dynamic query construction based on filters
   - Handles JSONB column queries (programs, tags)
   - Efficient pagination
   - Aggregate statistics

5. **Transaction Management**
   - Atomic operations for data consistency
   - Rollback on errors
   - Connection pooling for performance

---

## 5. Database Schema

### 5.1 Overview

**Database:** PostgreSQL 16+
**ORM:** SQLAlchemy 2.0 (async)
**Migrations:** Alembic

**Total Tables:** 12

```mermaid
erDiagram
    users ||--o{ user_sessions : has
    users ||--o{ writing_styles : creates
    users ||--o{ outputs : creates
    users ||--o{ programs : creates
    documents ||--o{ document_programs : has
    documents ||--o{ document_tags : has
    conversations ||--o{ messages : contains
    conversations ||--o{ outputs : generates
    writing_styles ||--o{ outputs : styles

    users {
        UUID user_id PK
        string email UK
        string hashed_password
        string full_name
        enum role
        boolean is_active
        boolean is_superuser
        datetime created_at
        datetime updated_at
    }

    user_sessions {
        UUID session_id PK
        UUID user_id FK
        string access_token
        string refresh_token
        datetime expires_at
        datetime created_at
        string ip_address
        text user_agent
    }

    documents {
        UUID doc_id PK
        string filename
        string doc_type
        integer year
        string outcome
        text notes
        datetime upload_date
        integer file_size
        integer chunks_count
        string created_by
        datetime updated_at
        boolean is_sensitive
        string sensitivity_level
        text sensitivity_notes
        datetime sensitivity_confirmed_at
        string sensitivity_confirmed_by
    }

    programs {
        UUID program_id PK
        string name UK
        text description
        integer display_order
        boolean active
        datetime created_at
        datetime updated_at
        UUID created_by FK
    }

    document_programs {
        UUID doc_id PK_FK
        string program PK
    }

    document_tags {
        UUID doc_id PK_FK
        string tag PK
    }

    conversations {
        UUID conversation_id PK
        string name
        datetime created_at
        datetime updated_at
        string user_id
        jsonb metadata
        jsonb context
    }

    messages {
        UUID message_id PK
        UUID conversation_id FK
        string role
        text content
        jsonb sources
        jsonb metadata
        datetime created_at
    }

    writing_styles {
        UUID style_id PK
        string name UK
        string type
        text description
        text prompt_content
        jsonb samples
        jsonb analysis_metadata
        integer sample_count
        boolean active
        datetime created_at
        datetime updated_at
        UUID created_by FK
    }

    outputs {
        UUID output_id PK
        UUID conversation_id FK
        string output_type
        string title
        text content
        integer word_count
        string status
        UUID writing_style_id FK
        string funder_name
        numeric requested_amount
        numeric awarded_amount
        date submission_date
        date decision_date
        text success_notes
        jsonb metadata
        string created_by
        datetime created_at
        datetime updated_at
    }
```

### 5.2 Table Definitions

#### users

Primary user accounts table.

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'editor', 'writer')),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

**Key Points:**
- UUID primary key (auto-generated)
- Email must be unique
- Password stored as bcrypt hash
- Role enum enforced with CHECK constraint
- Soft delete via `is_active` flag

#### user_sessions

Active user sessions with JWT tokens.

```sql
CREATE TABLE user_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    access_token VARCHAR(512) NOT NULL,
    refresh_token VARCHAR(512) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_token ON user_sessions(access_token);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at);
```

**Key Points:**
- Cascade delete when user deleted
- Stores both access and refresh tokens
- Tracks IP and user agent for security audit
- Indexed on token for fast validation

#### documents

Document metadata records.

```sql
CREATE TABLE documents (
    doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    doc_type VARCHAR(50) NOT NULL CHECK (doc_type IN (
        'Grant Proposal', 'Grant Report', 'Case Study',
        'Annual Report', 'Other'
    )),
    year INTEGER NOT NULL CHECK (year >= 1900 AND year <= 2100),
    outcome VARCHAR(20) NOT NULL CHECK (outcome IN (
        'Awarded', 'Not Awarded', 'Pending', 'N/A'
    )),
    notes TEXT,
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    file_size INTEGER NOT NULL,
    chunks_count INTEGER NOT NULL DEFAULT 0,
    created_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Phase 5: Sensitivity tracking
    is_sensitive BOOLEAN DEFAULT FALSE,
    sensitivity_level VARCHAR(20) CHECK (sensitivity_level IN ('low', 'medium', 'high')),
    sensitivity_notes TEXT,
    sensitivity_confirmed_at TIMESTAMP WITH TIME ZONE,
    sensitivity_confirmed_by VARCHAR(255)
);

CREATE INDEX idx_documents_type ON documents(doc_type);
CREATE INDEX idx_documents_year ON documents(year);
CREATE INDEX idx_documents_outcome ON documents(outcome);
CREATE INDEX idx_documents_upload_date ON documents(upload_date);
```

**Key Points:**
- Stores metadata only (text stored in Qdrant)
- CHECK constraints enforce valid values
- `created_by` currently string (will be UUID FK after auth enforcement)
- Sensitivity fields for Phase 5 data governance

#### programs

Stores program definitions for dynamic program management. Replaces hardcoded CHECK constraints with a flexible, database-backed system.

```sql
CREATE TABLE programs (
    program_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    display_order INTEGER NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX idx_programs_name ON programs(name);
CREATE INDEX idx_programs_active ON programs(active);
CREATE INDEX idx_programs_display_order ON programs(display_order);

-- Trigger to auto-update updated_at
CREATE TRIGGER trigger_update_programs_updated_at
    BEFORE UPDATE ON programs
    FOR EACH ROW
    EXECUTE FUNCTION update_programs_updated_at();
```

**Key Points:**
- Enables dynamic program management without schema migrations
- Programs can be created, updated, and deactivated through the application
- `display_order` controls sorting (higher values = higher priority, 0-100 range)
- `active` flag allows soft deletion without removing programs from database
- Auto-updating `updated_at` timestamp via database trigger
- Seeded with initial programs: Early Childhood (60), Youth Development (50), Family Support (40), Education (30), Health (20), General (10)
- Referenced by `document_programs` table via foreign key for referential integrity

#### document_programs

Junction table for document-program many-to-many relationship. Uses foreign key constraint to ensure all program names exist in the `programs` table.

```sql
CREATE TABLE document_programs (
    doc_id UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    program VARCHAR(100) NOT NULL REFERENCES programs(name) ON DELETE RESTRICT,
    PRIMARY KEY (doc_id, program)
);

CREATE INDEX idx_doc_programs_program ON document_programs(program);
CREATE INDEX idx_document_programs_program_fk ON document_programs(program);
```

**Key Points:**
- Composite primary key
- Cascade delete when document deleted
- Foreign key to `programs.name` ensures referential integrity (prevents invalid program names)
- `ON DELETE RESTRICT` prevents deletion of programs that are in use
- Indexed on program for filtering and foreign key performance
- Migration: `d90d97ca4bbf` (removed hardcoded CHECK constraint, added FK)

#### document_tags

Junction table for document tags (free-form).

```sql
CREATE TABLE document_tags (
    doc_id UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    PRIMARY KEY (doc_id, tag)
);

CREATE INDEX idx_doc_tags_tag ON document_tags(tag);
```

**Key Points:**
- No enum constraint (tags are free-form)
- Useful for custom categorization

#### conversations

Chat conversation containers.

```sql
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    context JSONB DEFAULT '{}'::jsonb  -- Phase 5: Context persistence
);

CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_updated ON conversations(updated_at);
```

**Key Points:**
- `user_id` currently string (will be UUID FK)
- `metadata` stores arbitrary conversation data
- `context` persists conversation state (audience, section, etc.)

#### messages

Individual chat messages.

```sql
CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created ON messages(created_at);
```

**Key Points:**
- Cascade delete when conversation deleted
- `sources` JSONB array stores retrieved chunks
- `role` constrained to user/assistant

#### writing_styles

Custom writing style profiles.

```sql
CREATE TABLE writing_styles (
    style_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(50) CHECK (type IN ('grant', 'proposal', 'report', 'general')),
    description TEXT,
    prompt_content TEXT NOT NULL,
    samples JSONB DEFAULT '[]'::jsonb,
    analysis_metadata JSONB DEFAULT '{}'::jsonb,
    sample_count INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(user_id)
);

CREATE INDEX idx_styles_type ON writing_styles(type);
CREATE INDEX idx_styles_active ON writing_styles(active);
CREATE INDEX idx_styles_created_by ON writing_styles(created_by);
```

**Key Points:**
- Unique name constraint
- `samples` JSONB array stores original text
- `analysis_metadata` stores AI analysis results
- FK to users table

#### outputs

Saved/tracked generated content.

```sql
CREATE TABLE outputs (
    output_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(conversation_id) ON DELETE SET NULL,
    output_type VARCHAR(50) NOT NULL CHECK (output_type IN (
        'Grant Proposal', 'Grant Report', 'Case Study',
        'Annual Report', 'Marketing Material', 'Other'
    )),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN (
        'draft', 'submitted', 'pending', 'awarded', 'not_awarded'
    )),
    writing_style_id UUID REFERENCES writing_styles(style_id) ON DELETE SET NULL,
    funder_name VARCHAR(255),
    requested_amount NUMERIC(12, 2),
    awarded_amount NUMERIC(12, 2),
    submission_date DATE,
    decision_date DATE,
    success_notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_outputs_type ON outputs(output_type);
CREATE INDEX idx_outputs_status ON outputs(status);
CREATE INDEX idx_outputs_conversation ON outputs(conversation_id);
CREATE INDEX idx_outputs_style ON outputs(writing_style_id);
CREATE INDEX idx_outputs_created_by ON outputs(created_by);
```

**Key Points:**
- Links to conversation (SET NULL on delete)
- Links to writing style (SET NULL on delete)
- Tracks full lifecycle (draft → submitted → awarded/not_awarded)
- Financial tracking (requested/awarded amounts)
- `created_by` currently string (will be UUID FK)

#### prompt_templates

Reusable prompt structures.

```sql
CREATE TABLE prompt_templates (
    prompt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    variables JSONB DEFAULT '[]'::jsonb,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    version INTEGER DEFAULT 1
);

CREATE INDEX idx_prompts_category ON prompt_templates(category);
CREATE INDEX idx_prompts_active ON prompt_templates(active);
```

**Key Points:**
- Unique name constraint
- `variables` JSONB array lists placeholder variables
- Version tracking for prompt evolution

#### system_config

System-wide configuration key-value store.

```sql
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Points:**
- Simple key-value store
- JSONB values allow complex config objects
- Used for runtime configuration

#### audit_log

System audit trail.

```sql
CREATE TABLE audit_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    user_id VARCHAR(255),
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_event_type ON audit_log(event_type);
CREATE INDEX idx_audit_entity_type ON audit_log(entity_type);
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_created ON audit_log(created_at);
```

**Key Points:**
- Records all significant system events
- `details` JSONB stores event-specific data
- Indexed for fast searching/filtering

### 5.3 JSONB Field Structures

#### conversations.context
```json
{
  "audience": "Federal RFP",
  "section": "Program Description",
  "working_doc_id": "output_123",
  "filters": {
    "programs": ["Education"],
    "years": [2023]
  }
}
```

#### messages.sources
```json
[
  {
    "doc_id": "doc_123",
    "filename": "proposal-2023.pdf",
    "chunk_id": "chunk_001",
    "relevance_score": 0.89,
    "text": "Chunk content...",
    "doc_type": "Grant Proposal",
    "year": 2023
  }
]
```

#### writing_styles.analysis_metadata
```json
{
  "analyzed_at": "2025-11-10T12:00:00Z",
  "model_used": "claude-sonnet-4-5-20250929",
  "confidence": 0.92,
  "key_characteristics": [
    "Professional tone",
    "Evidence-based language",
    "Active voice"
  ]
}
```

#### outputs.metadata
```json
{
  "program_focus": "K-12 Literacy",
  "grant_type": "Federal",
  "deadline": "2024-03-20",
  "collaborators": ["partner-org-1"],
  "review_status": "approved"
}
```

### 5.4 Migration Management

**Alembic Configuration:**

- **Migrations Directory:** `/backend/alembic/versions/`
- **Auto-migration on startup:** Enabled by default (disable with `DISABLE_AUTO_MIGRATIONS=true`)

**Key Migrations:**

1. `2e0140e533a8_baseline_schema.py` - Initial 8 core tables
2. `d382069dacef_add_writing_styles.py` - Phase 3 additions
3. `212c31d97f11_add_seed_data.py` - System configuration data

**Common Operations:**

```bash
# Check current migration version
alembic current

# View migration history
alembic history

# Upgrade to latest
alembic upgrade head

# Downgrade one version
alembic downgrade -1

# Create new migration
alembic revision --autogenerate -m "description"
```

**Auto-Migration Flow:**
1. Backend starts
2. Checks current DB version
3. Applies pending migrations
4. Retries up to 3 times on failure
5. Times out after 30 seconds

---

## 6. Integration Patterns

### 6.1 File Upload Pattern

**Challenge:** Uploading files with JSON metadata to FastAPI.

**Solution:** Use `multipart/form-data` with JSON-stringified metadata.

**Nuxt 3/4 Implementation:**

```typescript
// composables/useFileUpload.ts
export const useFileUpload = () => {
  const config = useRuntimeConfig()
  const { token } = useAuth()

  const uploadDocument = async (
    file: File,
    metadata: DocumentMetadata
  ) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('metadata', JSON.stringify(metadata))
    formData.append('sensitivity_confirmed', 'true')

    const response = await $fetch('/api/documents/upload', {
      method: 'POST',
      baseURL: config.public.apiBase,
      headers: {
        'Authorization': `Bearer ${token.value}`
      },
      body: formData
    })

    return response
  }

  return { uploadDocument }
}
```

**Usage in Component:**

```vue
<script setup lang="ts">
const { uploadDocument } = useFileUpload()

const handleUpload = async (file: File) => {
  const metadata = {
    doc_type: 'Grant Proposal',
    programs: ['Education'],
    outcome: 'Awarded',
    year: 2023,
    tags: ['federal'],
    notes: 'K-12 literacy program',
    is_sensitive: false,
    sensitivity_level: 'low'
  }

  try {
    const result = await uploadDocument(file, metadata)
    console.log('Uploaded:', result)
  } catch (error) {
    console.error('Upload failed:', error)
  }
}
</script>
```

**Important:**
- Do NOT set `Content-Type` header (browser sets it automatically with boundary)
- Stringify the metadata object
- File size limit: 50MB (configured in backend settings)

### 6.2 Server-Sent Events (SSE) Streaming

**Challenge:** Receiving real-time streamed responses from generation endpoints.

**Solution:** Use EventSource API for SSE.

**Nuxt 3/4 Implementation:**

```typescript
// composables/useStreamingGeneration.ts
export const useStreamingGeneration = () => {
  const config = useRuntimeConfig()
  const { token } = useAuth()

  const generateStreaming = (
    request: QueryRequest,
    handlers: {
      onSources?: (sources: any[]) => void
      onContent?: (chunk: string) => void
      onDone?: (metadata: any) => void
      onError?: (error: any) => void
    }
  ) => {
    // EventSource doesn't support custom headers, so use POST workaround
    // Alternative: Use fetch with ReadableStream

    const streamResponse = async () => {
      const response = await fetch(`${config.public.apiBase}/api/query/stream`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token.value}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      let buffer = ''

      while (true) {
        const { done, value } = await reader!.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event:')) {
            const event = line.slice(6).trim()
            continue
          }

          if (line.startsWith('data:')) {
            const data = JSON.parse(line.slice(5).trim())

            if (event === 'sources' && handlers.onSources) {
              handlers.onSources(data.sources)
            } else if (event === 'content' && handlers.onContent) {
              handlers.onContent(data.content)
            } else if (event === 'done' && handlers.onDone) {
              handlers.onDone(data.metadata)
            } else if (event === 'error' && handlers.onError) {
              handlers.onError(data)
            }
          }
        }
      }
    }

    return streamResponse()
  }

  return { generateStreaming }
}
```

**Usage in Component:**

```vue
<script setup lang="ts">
const { generateStreaming } = useStreamingGeneration()

const generatedContent = ref('')
const sources = ref([])

const handleGenerate = async () => {
  generatedContent.value = ''

  await generateStreaming(
    {
      query: 'Describe our education programs',
      audience: 'Federal RFP',
      section: 'Program Description',
      max_sources: 5
    },
    {
      onSources: (retrievedSources) => {
        sources.value = retrievedSources
      },
      onContent: (chunk) => {
        generatedContent.value += chunk
      },
      onDone: (metadata) => {
        console.log('Generation complete:', metadata)
      },
      onError: (error) => {
        console.error('Error:', error)
      }
    }
  )
}
</script>

<template>
  <div>
    <button @click="handleGenerate">Generate</button>
    <div v-html="generatedContent"></div>
  </div>
</template>
```

**Alternative (simpler but less control):**

```typescript
// For simpler use cases, use non-streaming endpoint
const { data, error } = await useFetch('/api/query', {
  method: 'POST',
  baseURL: config.public.apiBase,
  headers: {
    'Authorization': `Bearer ${token.value}`
  },
  body: request
})
```

### 6.3 Error Handling Pattern

**Challenge:** Consistent error handling across API calls.

**Solution:** Centralized error handling composable.

**Nuxt 3/4 Implementation:**

```typescript
// composables/useApiError.ts
export interface ApiError {
  status: number
  message: string
  detail?: string
  validation_errors?: Record<string, string[]>
}

export const useApiError = () => {
  const handleError = (error: any): ApiError => {
    // FetchError from ofetch/$fetch
    if (error.response) {
      const status = error.response.status
      const data = error.response._data

      switch (status) {
        case 400:
          return {
            status,
            message: 'Invalid request',
            detail: data.detail || data.message,
            validation_errors: data.validation_errors
          }
        case 401:
          // Handle auth errors (redirect to login)
          navigateTo('/login')
          return {
            status,
            message: 'Authentication required'
          }
        case 403:
          return {
            status,
            message: 'Insufficient permissions',
            detail: data.detail
          }
        case 404:
          return {
            status,
            message: 'Resource not found'
          }
        case 422:
          return {
            status,
            message: 'Validation failed',
            detail: data.detail,
            validation_errors: data.detail // FastAPI format
          }
        case 500:
          return {
            status,
            message: 'Server error',
            detail: data.detail || 'An unexpected error occurred'
          }
        default:
          return {
            status,
            message: `Error ${status}`,
            detail: data.detail || data.message
          }
      }
    }

    // Network error
    return {
      status: 0,
      message: 'Network error',
      detail: 'Unable to connect to the server'
    }
  }

  return { handleError }
}
```

**Usage:**

```typescript
// In component or composable
const { handleError } = useApiError()

try {
  const result = await $fetch('/api/documents', {
    method: 'GET',
    baseURL: config.public.apiBase,
    headers: {
      'Authorization': `Bearer ${token.value}`
    }
  })
} catch (error) {
  const apiError = handleError(error)

  // Show error to user
  toast.error(apiError.message, {
    description: apiError.detail
  })

  // Handle validation errors
  if (apiError.validation_errors) {
    for (const [field, errors] of Object.entries(apiError.validation_errors)) {
      console.error(`${field}: ${errors.join(', ')}`)
    }
  }
}
```

### 6.4 Pagination Pattern

**Challenge:** Backend returns skip/limit but no pagination metadata.

**Solution:** Calculate pagination metadata client-side.

**Nuxt 3/4 Implementation:**

```typescript
// composables/usePagination.ts
export const usePagination = (
  fetchFunction: (skip: number, limit: number) => Promise<{ items: any[], total: number }>
) => {
  const page = ref(1)
  const pageSize = ref(20)
  const total = ref(0)
  const items = ref<any[]>([])
  const loading = ref(false)

  const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
  const hasNext = computed(() => page.value < totalPages.value)
  const hasPrev = computed(() => page.value > 1)

  const load = async () => {
    loading.value = true
    try {
      const skip = (page.value - 1) * pageSize.value
      const result = await fetchFunction(skip, pageSize.value)
      items.value = result.items
      total.value = result.total
    } finally {
      loading.value = false
    }
  }

  const nextPage = async () => {
    if (hasNext.value) {
      page.value++
      await load()
    }
  }

  const prevPage = async () => {
    if (hasPrev.value) {
      page.value--
      await load()
    }
  }

  const goToPage = async (pageNum: number) => {
    if (pageNum >= 1 && pageNum <= totalPages.value) {
      page.value = pageNum
      await load()
    }
  }

  return {
    page,
    pageSize,
    total,
    totalPages,
    items,
    loading,
    hasNext,
    hasPrev,
    load,
    nextPage,
    prevPage,
    goToPage
  }
}
```

**Usage:**

```vue
<script setup lang="ts">
const config = useRuntimeConfig()
const { token } = useAuth()

const fetchDocuments = async (skip: number, limit: number) => {
  const data = await $fetch('/api/documents', {
    method: 'GET',
    baseURL: config.public.apiBase,
    headers: {
      'Authorization': `Bearer ${token.value}`
    },
    query: { skip, limit }
  })

  return {
    items: data.documents,
    total: data.total
  }
}

const pagination = usePagination(fetchDocuments)

onMounted(() => {
  pagination.load()
})
</script>

<template>
  <div>
    <div v-if="pagination.loading.value">Loading...</div>
    <div v-else>
      <div v-for="doc in pagination.items.value" :key="doc.doc_id">
        {{ doc.filename }}
      </div>

      <div class="pagination">
        <button @click="pagination.prevPage()" :disabled="!pagination.hasPrev.value">
          Previous
        </button>
        <span>Page {{ pagination.page.value }} of {{ pagination.totalPages.value }}</span>
        <button @click="pagination.nextPage()" :disabled="!pagination.hasNext.value">
          Next
        </button>
      </div>
    </div>
  </div>
</template>
```

### 6.5 JSONB Data Handling

**Challenge:** JSONB fields require proper encoding/decoding.

**Solution:** TypeScript interfaces and validation.

**Nuxt 3/4 Implementation:**

```typescript
// types/api.ts
export interface DocumentMetadata {
  doc_type: DocumentType
  programs: Program[]
  outcome: Outcome
  year: number
  tags?: string[]
  notes?: string
  is_sensitive?: boolean
  sensitivity_level?: SensitivityLevel
}

export type DocumentType =
  | 'Grant Proposal'
  | 'Grant Report'
  | 'Case Study'
  | 'Annual Report'
  | 'Other'

export type Program =
  | 'Education'
  | 'Health'
  | 'Environment'
  | 'Arts & Culture'
  | 'Youth Development'
  | 'Economic Development'
  | 'Housing'
  | 'Other'

export type Outcome = 'Awarded' | 'Not Awarded' | 'Pending' | 'N/A'

export type SensitivityLevel = 'low' | 'medium' | 'high'

export interface ConversationContext {
  audience?: string
  section?: string
  working_doc_id?: string
  filters?: DocumentFilters
}

export interface OutputMetadata {
  program_focus?: string
  grant_type?: string
  deadline?: string
  collaborators?: string[]
  review_status?: string
  [key: string]: any  // Allow additional fields
}
```

**Validation:**

```typescript
// utils/validation.ts
export const validateDocumentMetadata = (metadata: any): DocumentMetadata => {
  const validDocTypes = ['Grant Proposal', 'Grant Report', 'Case Study', 'Annual Report', 'Other']
  const validPrograms = ['Education', 'Health', 'Environment', 'Arts & Culture', 'Youth Development', 'Economic Development', 'Housing', 'Other']
  const validOutcomes = ['Awarded', 'Not Awarded', 'Pending', 'N/A']

  if (!validDocTypes.includes(metadata.doc_type)) {
    throw new Error(`Invalid doc_type: ${metadata.doc_type}`)
  }

  if (!Array.isArray(metadata.programs) || metadata.programs.length === 0) {
    throw new Error('programs must be a non-empty array')
  }

  for (const program of metadata.programs) {
    if (!validPrograms.includes(program)) {
      throw new Error(`Invalid program: ${program}`)
    }
  }

  if (!validOutcomes.includes(metadata.outcome)) {
    throw new Error(`Invalid outcome: ${metadata.outcome}`)
  }

  if (metadata.year < 1900 || metadata.year > 2100) {
    throw new Error(`Invalid year: ${metadata.year}`)
  }

  return metadata as DocumentMetadata
}
```

### 6.6 Role-Based UI Rendering

**Challenge:** Show/hide features based on user role.

**Solution:** Auth composable with role checking.

**Nuxt 3/4 Implementation:**

```typescript
// composables/useAuth.ts
export const useAuth = () => {
  const token = useCookie('auth_token')
  const refreshToken = useCookie('refresh_token')
  const user = useState<User | null>('user', () => null)

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isEditor = computed(() => user.value?.role === 'editor' || isAdmin.value)
  const isWriter = computed(() => !!user.value)  // Any authenticated user

  const can = (permission: string): boolean => {
    if (!user.value) return false

    const permissions: Record<string, boolean> = {
      'view_documents': isWriter.value,
      'upload_documents': isEditor.value,
      'delete_documents': isEditor.value,
      'create_writing_styles': isEditor.value,
      'delete_writing_styles': isAdmin.value,
      'create_prompts': isEditor.value,
      'delete_prompts': isAdmin.value,
      'view_audit_logs': isAdmin.value,
      'manage_users': isAdmin.value,
      'system_config': isAdmin.value
    }

    return permissions[permission] || false
  }

  return {
    token,
    refreshToken,
    user,
    isAuthenticated,
    isAdmin,
    isEditor,
    isWriter,
    can
  }
}
```

**Usage in Component:**

```vue
<script setup lang="ts">
const { can, isEditor } = useAuth()
</script>

<template>
  <div>
    <!-- Show upload button only for editors -->
    <button v-if="can('upload_documents')" @click="uploadDocument">
      Upload Document
    </button>

    <!-- Show delete button only for editors -->
    <button v-if="can('delete_documents')" @click="deleteDocument">
      Delete
    </button>

    <!-- Show admin panel only for admins -->
    <div v-if="can('system_config')">
      <h2>System Configuration</h2>
      <!-- Admin controls -->
    </div>
  </div>
</template>
```

---

## 7. Configuration & Deployment

### 7.1 Environment Variables

**Required Variables:**

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx               # If using OpenAI embeddings
VOYAGE_API_KEY=pa-xxx                # If using Voyage embeddings

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=org_archivist
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=foundation_docs
QDRANT_API_KEY=                      # Optional

# Embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# Claude
CLAUDE_MODEL=claude-sonnet-4-5-20250929
CLAUDE_TEMPERATURE=0.3
CLAUDE_MAX_TOKENS=4096
CLAUDE_TIMEOUT_SECONDS=60
CLAUDE_MAX_RETRIES=3

# Security
SECRET_KEY=your-secret-key-256-bits
ENABLE_AUTH=true
SESSION_TIMEOUT_MINUTES=60

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

### 7.2 Feature Flags

**Authentication:**
- `ENABLE_AUTH=true` - Enforce authentication (MUST be true in production)
- `ENABLE_AUTH=false` - Disable auth (development only)

**Migrations:**
- `DISABLE_AUTO_MIGRATIONS=true` - Manual migration control (production)
- `DISABLE_AUTO_MIGRATIONS=false` - Auto-run migrations (development)

### 7.3 CORS Configuration

**Current Implementation** (`/backend/app/main.py`):

```python
# TODO: Load allowed origins from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # DEVELOPMENT ONLY
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production Configuration:**

```python
import os

ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS else ["https://app.orgarchivist.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Environment Variable:**
```bash
# Production domain (add additional subdomains if needed)
CORS_ALLOWED_ORIGINS=https://app.orgarchivist.com
```

### 7.4 Docker Deployment

**docker-compose.yml Example:**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
      - ENABLE_AUTH=true
      - ENVIRONMENT=production
      - DISABLE_AUTO_MIGRATIONS=true
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

volumes:
  postgres_data:
  qdrant_data:
```

### 7.5 Production Checklist

- [ ] Set `ENABLE_AUTH=true`
- [ ] Generate secure `SECRET_KEY` (256-bit random)
- [ ] Configure `CORS_ALLOWED_ORIGINS=https://app.orgarchivist.com` (add other subdomains if needed)
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Use strong database password
- [ ] Enable HTTPS/TLS
- [ ] Set `DISABLE_AUTO_MIGRATIONS=true`
- [ ] Run migrations manually before deploy
- [ ] Configure backup strategy (PostgreSQL + Qdrant)
- [ ] Set up monitoring and logging
- [ ] Implement rate limiting (nginx/CloudFlare)
- [ ] Review and set appropriate file size limits
- [ ] Configure session timeout appropriately

---

## 8. Known Issues & Limitations

### 8.1 Backend Bugs

#### 1. CORS Configuration Hardcoded
**File:** `/backend/app/main.py:90`

**Issue:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Load from settings
```

**Impact:** Security risk in production - allows any origin to access API

**Fix Required:**
1. Load from environment variable: `settings.get_cors_origins_list()`
2. Set environment variable: `CORS_ALLOWED_ORIGINS=https://app.orgarchivist.com`
3. If multiple subdomains needed, use comma-separated list:
   - `CORS_ALLOWED_ORIGINS=https://app.orgarchivist.com,https://admin.orgarchivist.com`

**Priority:** HIGH - Must be fixed before production deployment

#### 2. File Size Limit Inconsistency ✅ RESOLVED
**Files:** `/backend/app/api/documents.py` and `/backend/app/config.py`

**Previous Issue:**
- Code enforced hardcoded 10MB limit
- Settings specified 50MB max

**Resolution:**
- Updated `documents.py` to use centralized configuration from `config.py`
- File size limit now consistently reads from `settings.max_file_size_mb` (50MB)
- Error messages dynamically display configured limit

#### 3. Program Filtering Not Optimized
**File:** `/backend/app/api/documents.py:293`

**Issue:**
```python
# TODO: Implement program filtering (requires JOIN)
# Currently filters in memory after query
```

**Impact:** Performance degradation with large document sets

**Fix Required:** Implement SQL JOIN with `document_programs` table

#### 4. Session Refresh Endpoint Missing
**File:** `/backend/app/api/auth.py`

**Issue:** No endpoint to refresh access token using refresh token

**Impact:** Users must re-login when access token expires

**Fix Required:** Implement `POST /api/auth/refresh` endpoint

#### 5. Authentication Not Fully Enforced
**File:** Multiple endpoints

**Issue:** Many endpoints lack proper auth dependency injection

**Impact:** Security gap if `ENABLE_AUTH=true` but endpoints not protected

**Fix Required:** Add `Depends(get_current_user)` to all protected endpoints

#### 6. Pagination Metadata Missing
**File:** `/backend/app/api/documents.py`, `/backend/app/api/outputs.py`

**Issue:** Returns `total`, `skip`, `limit` but not `total_pages`, `has_next`, etc.

**Impact:** Frontend must calculate pagination metadata

**Fix Required:** Return comprehensive pagination object

### 8.2 Incomplete Implementations

#### 1. Quality Validation Service
**Status:** Partially implemented

**Missing:**
- Hallucination detection
- Completeness checking
- Automated quality scoring

**Impact:** No automated quality assurance

#### 2. Citation Manager
**Status:** Basic implementation only

**Missing:**
- APA/MLA/Chicago formatting
- Bibliography generation
- Footnote support

**Impact:** Manual citation formatting required

#### 3. Query Cache
**Status:** Service exists but not integrated

**File:** `/backend/app/services/query_cache.py`

**Impact:** Repeated queries re-process unnecessarily

**Fix Required:** Integrate into retrieval pipeline

#### 4. Metadata Auto-Extractor
**Status:** Service exists but not integrated

**File:** `/backend/app/services/metadata_extractor.py`

**Impact:** All metadata must be manually entered

**Fix Required:** Integrate into upload flow

#### 5. Reranking
**Status:** Optional, not enabled by default

**Impact:** Suboptimal result ordering

**Fix Required:** Enable by default or make easily configurable

#### 6. Conversation Context Persistence
**Status:** Database field exists, partially utilized

**Issue:** `conversations.context` JSONB field not fully leveraged

**Impact:** Context not consistently maintained across chat sessions

**Fix Required:** Fully implement context persistence in chat endpoints

### 8.3 Security Concerns

#### 1. Password Requirements Not Enforced
**Issue:** Backend only checks minimum 8 characters

**Impact:** Weak passwords allowed

**Recommendation:** Enforce complexity requirements (uppercase, numbers, symbols)

#### 2. No Password Reset Flow
**Issue:** No "forgot password" functionality

**Impact:** Users locked out if password forgotten

**Fix Required:** Implement email-based password reset

#### 3. No Rate Limiting
**Issue:** No API rate limits implemented

**Impact:** Vulnerable to abuse, DoS attacks

**Recommendation:** Implement at reverse proxy level (nginx)

#### 4. Token Rotation Not Implemented
**Issue:** Tokens not rotated on suspicious activity

**Impact:** Stolen tokens valid until expiration

**Fix Required:** Implement token rotation on unusual activity

#### 5. Document-Level Access Control Missing
**Issue:** All authenticated users can access all documents

**Impact:** No document-level permissions

**Fix Required:** Implement document-level ACL (Phase 5+)

#### 6. Sensitive Data Not Enforced in Retrieval
**Issue:** `is_sensitive` flag exists but not filtered during retrieval

**Impact:** Sensitive content included in responses

**Fix Required:** Filter sensitive documents based on user permissions

#### 7. SQL Injection Risk (Minimal)
**Issue:** Some raw SQL queries might exist

**Impact:** Potential injection vulnerability

**Audit Required:** Review all database queries

#### 8. JSONB Injection
**Issue:** JSONB fields accept arbitrary JSON

**Impact:** Potential for malicious data injection

**Fix Required:** Validate JSONB structure with Pydantic schemas

### 8.4 Performance Considerations

#### 1. No Connection Pool Limits
**Issue:** Database connection pool unconfigured

**Impact:** Could exhaust connections under load

**Fix Required:** Configure pool size and overflow limits

#### 2. No Response Caching
**Issue:** No HTTP response caching

**Impact:** Repeated requests re-processed

**Recommendation:** Implement Redis cache for common queries

#### 3. Synchronous Embedding Generation
**Issue:** Embedding generation blocks during upload

**Impact:** Slow upload experience for large documents

**Fix Required:** Move to background task queue (Celery/RQ)

#### 4. Large Result Sets
**Issue:** No enforced pagination limits

**Impact:** Could return thousands of records

**Fix Required:** Add max limit (e.g., 100) per request

#### 5. No Query Result Caching
**Issue:** Identical queries re-executed

**Impact:** Wasted compute and API costs

**Fix Required:** Implement query cache with TTL

### 8.5 TODO Comments in Code

**Found TODO markers:**

1. `/backend/app/main.py:90`
   - "TODO: Load allowed origins from environment"

2. `/backend/app/main.py:145-146`
   - "TODO: Add database check"
   - "TODO: Add Qdrant check"

3. `/backend/app/api/documents.py:187`
   - "TODO: Add user authentication"

4. `/backend/app/api/documents.py:293`
   - "TODO: Implement program filtering (requires JOIN)"

---

## 9. Nuxt 4 Integration Guide

### 9.1 Recommended Nuxt Modules

**Essential Modules:**

```bash
# Install via npm/pnpm/yarn
pnpm add -D @nuxt/ui @nuxt/icon @nuxt/fonts
pnpm add @pinia/nuxt
pnpm add @vueuse/nuxt
pnpm add nuxt-auth-utils  # or @sidebase/nuxt-auth
```

**nuxt.config.ts:**

```typescript
export default defineNuxtConfig({
  modules: [
    '@nuxt/ui',
    '@nuxt/icon',
    '@nuxt/fonts',
    '@pinia/nuxt',
    '@vueuse/nuxt',
    'nuxt-auth-utils'
  ],

  runtimeConfig: {
    // Private keys (server-side only)
    apiSecret: process.env.API_SECRET,

    // Public keys (exposed to client)
    public: {
      apiBase: process.env.API_BASE_URL || 'http://localhost:8000',
      environment: process.env.ENVIRONMENT || 'development'
    }
  },

  // Enable auto-imports
  imports: {
    dirs: ['composables', 'utils', 'types']
  }
})
```

**Environment Variables:**

```bash
# Development
API_BASE_URL=http://localhost:8000
ENVIRONMENT=development

# Production
API_BASE_URL=https://api.orgarchivist.com  # Or your backend API URL
ENVIRONMENT=production
```

**Note:** If your backend is hosted on the same domain as the frontend, you might use a subdomain like `api.orgarchivist.com` or a path like `https://app.orgarchivist.com/api`

### 9.2 Auth State Management

**Pinia Store** (`stores/auth.ts`):

```typescript
import { defineStore } from 'pinia'

export interface User {
  user_id: string
  email: string
  full_name: string
  role: 'admin' | 'editor' | 'writer'
  is_active: boolean
  created_at: string
}

export interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    token: null,
    refreshToken: null,
    isAuthenticated: false
  }),

  getters: {
    isAdmin: (state) => state.user?.role === 'admin',
    isEditor: (state) => state.user?.role === 'editor' || state.user?.role === 'admin',
    isWriter: (state) => !!state.user,

    can: (state) => (permission: string): boolean => {
      if (!state.user) return false

      const permissions: Record<string, boolean> = {
        'view_documents': !!state.user,
        'upload_documents': state.user.role === 'editor' || state.user.role === 'admin',
        'delete_documents': state.user.role === 'editor' || state.user.role === 'admin',
        'create_writing_styles': state.user.role === 'editor' || state.user.role === 'admin',
        'delete_writing_styles': state.user.role === 'admin',
        'create_prompts': state.user.role === 'editor' || state.user.role === 'admin',
        'delete_prompts': state.user.role === 'admin',
        'view_audit_logs': state.user.role === 'admin',
        'manage_users': state.user.role === 'admin',
        'system_config': state.user.role === 'admin'
      }

      return permissions[permission] || false
    }
  },

  actions: {
    async login(email: string, password: string) {
      const config = useRuntimeConfig()

      const response = await $fetch('/api/auth/login', {
        method: 'POST',
        baseURL: config.public.apiBase,
        body: { email, password }
      })

      this.token = response.access_token
      this.refreshToken = response.refresh_token
      this.user = response.user
      this.isAuthenticated = true

      // Store in cookies
      const tokenCookie = useCookie('auth_token', {
        maxAge: 60 * 60,  // 1 hour
        secure: true,
        sameSite: 'strict'
      })
      const refreshCookie = useCookie('refresh_token', {
        maxAge: 60 * 60 * 24 * 7,  // 7 days
        secure: true,
        sameSite: 'strict'
      })

      tokenCookie.value = this.token
      refreshCookie.value = this.refreshToken
    },

    async logout() {
      const config = useRuntimeConfig()

      try {
        await $fetch('/api/auth/logout', {
          method: 'POST',
          baseURL: config.public.apiBase,
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })
      } catch (error) {
        console.error('Logout error:', error)
      }

      // Clear state
      this.user = null
      this.token = null
      this.refreshToken = null
      this.isAuthenticated = false

      // Clear cookies
      const tokenCookie = useCookie('auth_token')
      const refreshCookie = useCookie('refresh_token')
      tokenCookie.value = null
      refreshCookie.value = null

      // Redirect to login
      navigateTo('/login')
    },

    async fetchUser() {
      const config = useRuntimeConfig()

      if (!this.token) {
        const tokenCookie = useCookie('auth_token')
        this.token = tokenCookie.value
      }

      if (!this.token) {
        this.isAuthenticated = false
        return
      }

      try {
        const user = await $fetch('/api/auth/me', {
          method: 'GET',
          baseURL: config.public.apiBase,
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })

        this.user = user
        this.isAuthenticated = true
      } catch (error) {
        console.error('Failed to fetch user:', error)
        this.isAuthenticated = false
        this.token = null
      }
    },

    async validateSession() {
      const config = useRuntimeConfig()

      if (!this.token) return false

      try {
        const response = await $fetch('/api/auth/session', {
          method: 'GET',
          baseURL: config.public.apiBase,
          headers: {
            'Authorization': `Bearer ${this.token}`
          }
        })

        return response.valid
      } catch (error) {
        return false
      }
    }
  }
})
```

**Auth Middleware** (`middleware/auth.ts`):

```typescript
export default defineNuxtRouteMiddleware(async (to) => {
  const authStore = useAuthStore()

  // Skip for public routes
  const publicRoutes = ['/login', '/register']
  if (publicRoutes.includes(to.path)) {
    return
  }

  // Check authentication
  if (!authStore.isAuthenticated) {
    await authStore.fetchUser()
  }

  if (!authStore.isAuthenticated) {
    return navigateTo('/login')
  }

  // Check role-based access
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return navigateTo('/')
  }

  if (to.meta.requiresEditor && !authStore.isEditor) {
    return navigateTo('/')
  }
})
```

**Usage in Page:**

```vue
<!-- pages/admin/index.vue -->
<script setup lang="ts">
definePageMeta({
  middleware: 'auth',
  requiresAdmin: true
})

const authStore = useAuthStore()
</script>

<template>
  <div>
    <h1>Admin Panel</h1>
    <p>Welcome, {{ authStore.user?.full_name }}</p>
  </div>
</template>
```

### 9.3 API Client Setup

**Composable** (`composables/useApi.ts`):

```typescript
export const useApi = () => {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()

  const apiFetch = $fetch.create({
    baseURL: config.public.apiBase,
    headers: {
      'Authorization': authStore.token ? `Bearer ${authStore.token}` : ''
    },
    onResponseError({ response }) {
      if (response.status === 401) {
        authStore.logout()
      }
    }
  })

  return { apiFetch }
}
```

**Usage:**

```typescript
// In component
const { apiFetch } = useApi()

const documents = await apiFetch('/api/documents')
```

### 9.4 File Upload Implementation

**Composable** (`composables/useFileUpload.ts`):

```typescript
export const useFileUpload = () => {
  const { apiFetch } = useApi()
  const toast = useToast()

  const uploadDocument = async (
    file: File,
    metadata: DocumentMetadata,
    onProgress?: (progress: number) => void
  ) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('metadata', JSON.stringify(metadata))
    formData.append('sensitivity_confirmed', 'true')

    try {
      const response = await apiFetch('/api/documents/upload', {
        method: 'POST',
        body: formData
      })

      toast.add({
        title: 'Success',
        description: `Document "${file.name}" uploaded successfully`,
        color: 'green'
      })

      return response
    } catch (error) {
      const { handleError } = useApiError()
      const apiError = handleError(error)

      toast.add({
        title: 'Upload Failed',
        description: apiError.detail || apiError.message,
        color: 'red'
      })

      throw error
    }
  }

  return { uploadDocument }
}
```

**Component** (`components/DocumentUpload.vue`):

```vue
<script setup lang="ts">
const { uploadDocument } = useFileUpload()

const file = ref<File | null>(null)
const metadata = ref<DocumentMetadata>({
  doc_type: 'Grant Proposal',
  programs: ['Education'],
  outcome: 'Awarded',
  year: new Date().getFullYear(),
  tags: [],
  notes: '',
  is_sensitive: false,
  sensitivity_level: 'low'
})

const uploading = ref(false)

const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    file.value = input.files[0]
  }
}

const handleUpload = async () => {
  if (!file.value) return

  uploading.value = true

  try {
    await uploadDocument(file.value, metadata.value)
    // Reset form
    file.value = null
    metadata.value = {
      doc_type: 'Grant Proposal',
      programs: ['Education'],
      outcome: 'Awarded',
      year: new Date().getFullYear(),
      tags: [],
      notes: '',
      is_sensitive: false,
      sensitivity_level: 'low'
    }
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <UCard>
    <template #header>
      <h3>Upload Document</h3>
    </template>

    <UForm :state="metadata" @submit="handleUpload">
      <UFormGroup label="File" required>
        <input type="file" @change="handleFileChange" accept=".pdf,.docx,.txt,.doc" />
      </UFormGroup>

      <UFormGroup label="Document Type" required>
        <USelect v-model="metadata.doc_type" :options="docTypeOptions" />
      </UFormGroup>

      <UFormGroup label="Programs" required>
        <USelectMenu v-model="metadata.programs" :options="programOptions" multiple />
      </UFormGroup>

      <UFormGroup label="Outcome" required>
        <USelect v-model="metadata.outcome" :options="outcomeOptions" />
      </UFormGroup>

      <UFormGroup label="Year" required>
        <UInput v-model="metadata.year" type="number" />
      </UFormGroup>

      <UFormGroup label="Tags">
        <UInput v-model="metadata.tags" placeholder="Comma-separated tags" />
      </UFormGroup>

      <UFormGroup label="Notes">
        <UTextarea v-model="metadata.notes" />
      </UFormGroup>

      <UButton type="submit" :loading="uploading" :disabled="!file">
        Upload Document
      </UButton>
    </UForm>
  </UCard>
</template>
```

### 9.5 SSE Streaming in Nuxt

**Composable** (`composables/useStreamingQuery.ts`):

```typescript
export const useStreamingQuery = () => {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()

  const executeQuery = async (
    request: QueryRequest,
    callbacks: {
      onSources?: (sources: any[]) => void
      onContent?: (chunk: string) => void
      onDone?: (metadata: any) => void
      onError?: (error: any) => void
    }
  ) => {
    try {
      const response = await fetch(`${config.public.apiBase}/api/query/stream`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authStore.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(request)
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      let buffer = ''
      let currentEvent = ''

      while (true) {
        const { done, value } = await reader!.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim()
          } else if (line.startsWith('data:')) {
            const data = JSON.parse(line.slice(5).trim())

            switch (currentEvent) {
              case 'sources':
                callbacks.onSources?.(data.sources)
                break
              case 'content':
                callbacks.onContent?.(data.content)
                break
              case 'done':
                callbacks.onDone?.(data.metadata)
                break
              case 'error':
                callbacks.onError?.(data)
                break
            }
          }
        }
      }
    } catch (error) {
      callbacks.onError?.(error)
    }
  }

  return { executeQuery }
}
```

**Usage Component** (`components/ContentGenerator.vue`):

```vue
<script setup lang="ts">
const { executeQuery } = useStreamingQuery()

const query = ref('')
const content = ref('')
const sources = ref([])
const generating = ref(false)

const handleGenerate = async () => {
  content.value = ''
  sources.value = []
  generating.value = true

  await executeQuery(
    {
      query: query.value,
      audience: 'Federal RFP',
      section: 'Program Description',
      max_sources: 5
    },
    {
      onSources: (retrievedSources) => {
        sources.value = retrievedSources
      },
      onContent: (chunk) => {
        content.value += chunk
      },
      onDone: (metadata) => {
        console.log('Generation complete:', metadata)
        generating.value = false
      },
      onError: (error) => {
        console.error('Error:', error)
        generating.value = false
      }
    }
  )
}
</script>

<template>
  <div>
    <UTextarea v-model="query" placeholder="Enter your query..." />
    <UButton @click="handleGenerate" :loading="generating">
      Generate
    </UButton>

    <div v-if="sources.length" class="sources">
      <h3>Sources</h3>
      <div v-for="source in sources" :key="source.doc_id">
        {{ source.filename }} ({{ source.year }})
      </div>
    </div>

    <div v-if="content" class="content">
      <h3>Generated Content</h3>
      <div v-html="content"></div>
    </div>
  </div>
</template>
```

### 9.6 Error Handling Utilities

**Composable** (`composables/useApiError.ts`):

See Section 6.3 for complete implementation.

**Toast Integration:**

```typescript
// In error handler
const toast = useToast()
const { handleError } = useApiError()

try {
  await someApiCall()
} catch (error) {
  const apiError = handleError(error)

  toast.add({
    title: apiError.message,
    description: apiError.detail,
    color: 'red',
    icon: 'i-heroicons-exclamation-triangle'
  })
}
```

### 9.7 TypeScript Types

**Create shared types** (`types/api.ts`):

```typescript
// All types from Section 6.5 plus:

export interface QueryRequest {
  query: string
  audience: string
  section: string
  tone?: string
  max_sources?: number
  recency_weight?: number
  include_citations?: boolean
  filters?: DocumentFilters
  custom_instructions?: string
  max_tokens?: number
  temperature?: number
}

export interface QueryResponse {
  content: string
  sources: Source[]
  metadata: {
    total_sources: number
    tokens_used: number
    model: string
    temperature: number
    retrieval_time_ms: number
    generation_time_ms: number
  }
}

export interface Source {
  doc_id: string
  filename: string
  chunk_id: string
  relevance_score: number
  text: string
  doc_type: string
  year: number
  programs: string[]
}

export interface ChatRequest {
  message: string
  conversation_id?: string
  context?: ConversationContext
  filters?: DocumentFilters
  max_sources?: number
}

export interface ChatResponse {
  message_id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  created_at: string
}

export interface WritingStyle {
  style_id: string
  name: string
  type: 'grant' | 'proposal' | 'report' | 'general'
  description: string
  prompt_content: string
  sample_count: number
  active: boolean
  created_at: string
  updated_at: string
  created_by: string
}

export interface Output {
  output_id: string
  conversation_id?: string
  output_type: string
  title: string
  content: string
  word_count: number
  status: 'draft' | 'submitted' | 'pending' | 'awarded' | 'not_awarded'
  writing_style_id?: string
  funder_name?: string
  requested_amount?: number
  awarded_amount?: number
  submission_date?: string
  decision_date?: string
  success_notes?: string
  metadata?: OutputMetadata
  created_by: string
  created_at: string
  updated_at: string
}
```

---

## Summary

This comprehensive backend API guide provides everything needed for Nuxt 4 frontend development:

**What's Complete:**
- ✅ Full authentication system with JWT and sessions
- ✅ Role-based access control (Admin/Editor/Writer)
- ✅ Complete document management pipeline
- ✅ RAG retrieval with hybrid search
- ✅ Claude integration (streaming and non-streaming)
- ✅ Writing style analysis and application
- ✅ Output tracking with success metrics
- ✅ Comprehensive database schema

**What Needs Attention:**
- ⚠️ CORS configuration must be fixed for production
- ⚠️ Authentication must be enabled (`ENABLE_AUTH=true`)
- ⚠️ Session refresh endpoint needs implementation
- ⚠️ File size limits need standardization
- ⚠️ Program filtering optimization required
- ⚠️ Password requirements need enforcement
- ⚠️ Rate limiting recommended

**Frontend Development Priorities:**
1. Implement auth flow (login, session management, role-based UI)
2. Set up API client with error handling
3. Build document upload with proper multipart handling
4. Implement SSE streaming for generation
5. Create consistent error handling
6. Build pagination utilities
7. Implement role-based feature visibility

**Next Steps:**
1. Review this documentation with the frontend team
2. Set up Nuxt 4 project with recommended modules
3. Implement auth store and middleware
4. Build core API composables
5. Create reusable UI components
6. Test all integration patterns
7. Report any backend issues discovered during integration

---

**Document Version:** 1.0
**Last Updated:** 2025-11-10
**Maintained By:** Backend Team
**Questions?** Contact backend team or refer to `/docs` for additional documentation.
