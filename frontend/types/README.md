# TypeScript API Type Definitions

**Version:** 1.0
**Last Updated:** 2025-11-16
**Source of Truth:** Backend Pydantic models in `backend/app/models/`

## Overview

This directory contains comprehensive TypeScript type definitions that match the **actual backend API models**. All types are derived directly from the FastAPI Pydantic models to ensure 100% type safety and API contract alignment.

## Quick Start

```typescript
// Import types in your components or composables
import type {
  HealthCheckResponse,
  UserResponse,
  LoginRequest,
  DocumentResponse,
  QueryRequest,
  OutputResponse
} from '~/types/api'

// Use with $fetch for type-safe API calls
const user = await $fetch<UserResponse>('/api/auth/me')

// Use with useFetch for reactive data
const { data } = await useFetch<HealthCheckResponse>('/api/health')
```

## Type Categories

### 1. Core Response Types
Essential response structures used across the API.

#### `HealthCheckResponse`
Health check endpoint response (`GET /api/health`)
```typescript
{
  status: string        // "healthy"
  service: string       // "Org Archivist API"
  version: string       // "1.0.0"
  checks: Record<string, any>  // Component health checks
}
```

#### `ErrorResponse`
Standard error response format
```typescript
{
  error: string         // Error type
  detail: string        // Error details
  timestamp: string     // ISO 8601 timestamp
}
```

#### `SuccessResponse<T>`
Generic success wrapper
```typescript
{
  success: boolean
  message: string
  data?: T             // Optional response data
}
```

#### `PaginationMetadata`
Pagination information for list responses
```typescript
{
  total: number        // Total items
  page: number         // Current page (1-indexed)
  per_page: number     // Items per page
  total_pages: number  // Total pages
  has_next: boolean    // Has next page
  has_previous: boolean // Has previous page
}
```

---

### 2. Authentication Types
User authentication and authorization types.

**Role Hierarchy:**
- `admin` (Level 3) - Full system access
- `editor` (Level 2) - Manage content and library
- `writer` (Level 1) - Create content, read-only settings

#### `UserResponse`
User profile information
```typescript
{
  user_id: string           // UUID
  email: string
  full_name: string | null
  role: 'admin' | 'editor' | 'writer'
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at: string
}
```

#### `LoginRequest` / `LoginResponse`
```typescript
// Request
{ email: string, password: string }

// Response
{
  access_token: string
  refresh_token: string
  token_type: "bearer"
  expires_at: string     // ISO 8601
  user: UserResponse
}
```

**Endpoints:**
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/session` - Validate session
- `GET /api/auth/me` - Get current user

---

### 3. Document Types
Document management and metadata types.

#### `DocumentType`
```typescript
type DocumentType =
  | 'Grant Proposal'
  | 'Annual Report'
  | 'Program Description'
  | 'Impact Report'
  | 'Strategic Plan'
  | 'Other'
```

#### `DocumentOutcome`
```typescript
type DocumentOutcome =
  | 'N/A'
  | 'Funded'
  | 'Not Funded'
  | 'Pending'
  | 'Final Report'
```

#### `DocumentMetadata`
Metadata structure for uploaded documents
```typescript
{
  doc_type: DocumentType
  year: number          // 2000-2030
  programs: string[]    // Related programs
  tags: string[]        // Custom tags
  outcome: DocumentOutcome
  notes?: string
}
```

#### `DocumentResponse`
Complete document response
```typescript
{
  document_id: string
  filename: string
  user_id: string
  upload_date: string
  file_size: number
  metadata: DocumentMetadata
  sensitivity_check?: DocumentSensitivityCheck
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
}
```

**Document Upload:**
- `POST /api/documents/upload` - Upload single file
- `POST /api/documents/upload/batch` - Batch upload
- `GET /api/documents` - List documents (paginated)
- `GET /api/documents/{id}` - Get specific document
- `DELETE /api/documents/{id}` - Delete document (Editor/Admin only)

---

### 4. Query & Generation Types
RAG query and content generation types.

#### `QueryRequest`
Request for content generation
```typescript
{
  query: string                 // User's generation request (min 10 chars)
  audience: string              // Target audience
  section: string               // Document section
  tone?: string                 // Default: "Professional"
  max_sources?: number          // Default: 5, max: 15
  recency_weight?: number       // 0.0-1.0, default: 0.7
  include_citations?: boolean   // Default: true
  filters?: DocumentFilters
  conversation_id?: string      // For multi-turn conversations
  context?: ConversationContext
}
```

#### `QueryResponse`
Generated content response
```typescript
{
  content: string              // Generated text
  sources: Source[]            // Retrieved source documents
  metadata: GenerationMetadata
  conversation_id?: string
}
```

#### `Source`
Source document reference
```typescript
{
  doc_id: string
  filename: string
  chunk_id: string
  relevance_score: number      // 0.0-1.0
  text: string                 // Extracted text chunk
  doc_type: string
  year: number
  programs: string[]
}
```

#### `GenerationMetadata`
Generation statistics and metadata
```typescript
{
  total_sources: number
  tokens_used: number
  model: string                // e.g., "claude-sonnet-4-5"
  temperature: number
  retrieval_time_ms: number
  generation_time_ms: number
}
```

**Endpoints:**
- `POST /api/query` - Generate content (one-shot)
- `POST /api/chat` - Chat-based generation (multi-turn)

---

### 5. Chat & Conversation Types
Multi-turn conversation and context persistence.

#### `ConversationContext`
Conversation state for context persistence
```typescript
{
  writing_style_id?: string
  audience?: string
  section?: string
  tone?: string
  filters?: DocumentFilters
  artifacts?: ArtifactVersion[]    // Version history
  last_query?: string
  session_metadata?: SessionMetadata
}
```

#### `ArtifactVersion`
Generated content with versioning
```typescript
{
  artifact_id: string
  version: number                   // 1-indexed
  created_at: string
  content: string
  word_count: number
  metadata: Record<string, any>
}
```

#### `ChatMessage`
Individual chat message
```typescript
{
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  metadata?: Record<string, any>
}
```

**Endpoints:**
- `POST /api/chat` - Send chat message
- `GET /api/conversations/{id}/context` - Get conversation context
- `PUT /api/conversations/{id}/context` - Update context

---

### 6. Writing Style Types
Writing style analysis and application.

#### `WritingStyleType`
```typescript
type WritingStyleType = 'grant' | 'proposal' | 'report' | 'general'
```

#### `WritingStyle`
Complete writing style profile
```typescript
{
  style_id: string
  name: string
  type: WritingStyleType
  description?: string
  prompt_content: string           // The actual style prompt
  samples?: string[]               // Original writing samples
  analysis_metadata?: Record<string, any>
  sample_count: number
  active: boolean
  created_at: string
  updated_at: string
  created_by?: string
}
```

#### `StyleAnalysisRequest`
Analyze writing samples to create style
```typescript
{
  samples: string[]                // 3-7 samples, 200+ words each
  style_type?: WritingStyleType
  style_name?: string
}
```

**Endpoints:**
- `POST /api/writing-styles/analyze` - Analyze samples
- `POST /api/writing-styles` - Create style
- `GET /api/writing-styles` - List styles
- `PUT /api/writing-styles/{id}` - Update style
- `DELETE /api/writing-styles/{id}` - Delete style (Admin only)

---

### 7. Output Types
Generated content tracking with success metrics.

#### `OutputType`
```typescript
type OutputType =
  | 'grant_proposal'
  | 'budget_narrative'
  | 'program_description'
  | 'impact_summary'
  | 'other'
```

#### `OutputStatus`
```typescript
type OutputStatus =
  | 'draft'
  | 'submitted'
  | 'pending'
  | 'awarded'
  | 'not_awarded'
```

#### `OutputResponse`
Complete output with success tracking
```typescript
{
  output_id: string
  conversation_id?: string
  output_type: OutputType
  title: string
  content: string
  word_count?: number
  status: OutputStatus
  writing_style_id?: string

  // Grant tracking fields
  funder_name?: string
  requested_amount?: number
  awarded_amount?: number
  submission_date?: string         // ISO 8601 date
  decision_date?: string           // ISO 8601 date
  success_notes?: string

  metadata?: OutputMetadata
  created_by?: string
  created_at: string
  updated_at: string
}
```

#### `OutputStatsResponse`
Analytics and success metrics
```typescript
{
  total_outputs: number
  by_type: Record<string, number>
  by_status: Record<string, number>
  success_rate: number             // awarded / submitted
  total_requested: number
  total_awarded: number
  avg_requested?: number
  avg_awarded?: number
}
```

**Endpoints:**
- `POST /api/outputs` - Create output
- `GET /api/outputs` - List outputs (paginated)
- `GET /api/outputs/{id}` - Get specific output
- `PUT /api/outputs/{id}` - Update output
- `GET /api/outputs/stats` - Get statistics

---

### 8. Audit Log Types
Audit logging for compliance and tracking.

#### `AuditAction`
```typescript
type AuditAction =
  | 'CREATE'
  | 'READ'
  | 'UPDATE'
  | 'DELETE'
  | 'LOGIN'
  | 'LOGOUT'
  | 'UPLOAD'
  | 'DOWNLOAD'
  | 'GENERATE'
```

#### `AuditLogEntry`
```typescript
{
  log_id: string
  user_id: string
  action: AuditAction
  resource_type: string
  resource_id?: string
  details?: Record<string, any>
  ip_address?: string
  user_agent?: string
  timestamp: string
}
```

---

## Usage Patterns

### Pattern 1: Type-Safe API Calls

```typescript
// In a composable
export const useDocuments = () => {
  const fetchDocuments = async (page: number = 1) => {
    const { data } = await useFetch<PaginatedResponse<DocumentResponse>>(
      '/api/documents',
      { query: { page, per_page: 20 } }
    )
    return data
  }

  return { fetchDocuments }
}
```

### Pattern 2: Form Validation with Types

```typescript
<script setup lang="ts">
import type { LoginRequest, LoginResponse } from '~/types/api'

const loginForm = ref<LoginRequest>({
  email: '',
  password: ''
})

const handleLogin = async () => {
  const response = await $fetch<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: loginForm.value
  })

  // TypeScript knows the structure!
  const { access_token, user } = response
}
</script>
```

### Pattern 3: Enum Usage

```typescript
import type { OutputStatus, OutputType } from '~/types/api'

// Type-safe status selection
const statusOptions: OutputStatus[] = [
  'draft',
  'submitted',
  'pending',
  'awarded',
  'not_awarded'
]

// Filter by type
const filterByType = (type: OutputType) => {
  // TypeScript enforces valid values
}
```

### Pattern 4: Generic Response Handling

```typescript
const handleApiResponse = <T>(response: SuccessResponse<T>) => {
  if (response.success) {
    // response.data is type T
    return response.data
  }
  throw new Error(response.message)
}
```

---

## Type Alignment with Backend

**Source Mapping:**

| TypeScript Type | Backend Model | File |
|----------------|---------------|------|
| `UserResponse` | `UserResponse` | `backend/app/models/auth.py` |
| `DocumentMetadata` | `DocumentMetadata` | `backend/app/models/document.py` |
| `QueryRequest` | `QueryRequest` | `backend/app/models/query.py` |
| `OutputResponse` | `OutputResponse` | `backend/app/models/output.py` |
| `WritingStyle` | `WritingStyle` | `backend/app/models/writing_style.py` |
| `ConversationContext` | `ConversationContext` | `backend/app/models/conversation.py` |

**Validation Rules:**

All backend validation rules are reflected in the types:
- String length constraints documented in comments
- Number ranges (e.g., `year: 2000-2030`)
- Enum values match backend exactly
- Required vs optional fields match Pydantic models

---

## Common Gotchas & Tips

### 1. Date/DateTime Handling
All dates/datetimes are **ISO 8601 strings** in TypeScript:
```typescript
// Backend sends: "2025-11-16T12:00:00Z"
// Frontend receives: string
const date = new Date(response.created_at)  // Convert to Date object
```

### 2. UUID Types
UUIDs are represented as **strings** in TypeScript:
```typescript
user_id: string  // e.g., "550e8400-e29b-41d4-a716-446655440000"
```

### 3. Optional vs Required
Pay attention to `?` in type definitions:
```typescript
title: string       // Required - must be present
title?: string      // Optional - may be undefined
```

### 4. Enum String Literals
Use const assertions for better autocomplete:
```typescript
const status: OutputStatus = 'draft'  // ✅ Type-safe
const status = 'draft' as const       // ✅ Also works
```

### 5. Record<string, any> Fields
Some fields allow arbitrary JSON:
```typescript
metadata: Record<string, any>  // Can contain any structure
```

---

## Updating Types

**When to update:**
- Backend Pydantic models change
- New API endpoints added
- Field requirements change

**Update process:**
1. Review backend model changes in `backend/app/models/*.py`
2. Update corresponding TypeScript types in `types/api.ts`
3. Update this README with new examples
4. Run `npx nuxi typecheck` to verify
5. Test with actual API calls

**Version control:**
- Update `Last Updated` date at top of this file
- Document breaking changes in commit message
- Consider adding migration notes if needed

---

## Testing Type Definitions

```bash
# Type check entire project
npx nuxi typecheck

# Type check in watch mode
npx nuxi typecheck --watch
```

---

## Additional Resources

- [Backend API Guide](/docs/backend-api-guide.md) - Complete API documentation
- [Nuxt 4 Setup Guide](/docs/nuxt4-setup.md) - Frontend setup instructions
- [Backend Pydantic Models](/backend/app/models/) - Source of truth for types
- [API Endpoints](/backend/app/api/) - Backend API implementation

---

## Questions & Support

For questions about:
- **Type definitions**: Check this README first
- **API behavior**: See Backend API Guide
- **Backend changes**: Review Pydantic models in `backend/app/models/`
- **Integration issues**: Check Nuxt 4 Setup Guide

**Maintained by:** Frontend Development Team
**Last Reviewed:** 2025-11-16
