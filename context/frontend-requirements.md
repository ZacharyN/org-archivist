# Frontend Requirements & Business Logic

## 📘 CURRENT: Nuxt 4 Implementation Specification

**Document Status:** CURRENT - NUXT 4 REQUIREMENTS
**Last Updated:** November 16, 2025
**Implementation:** Nuxt 4 (Vue 3 + TypeScript + Nuxt UI)

**Migration Status:**
This document has been **updated for Nuxt 4** frontend implementation. The Org Archivist has migrated from Streamlit to a modern Vue 3/Nuxt 4 application with full TypeScript support.

**Key Technologies:**
- **Framework:** Nuxt 4 (Vue 3 composition API)
- **Language:** TypeScript (strict mode)
- **UI Library:** Nuxt UI (built on Tailwind CSS)
- **Icons:** Nuxt Icon
- **Authentication:** JWT-based with session management
- **Streaming:** Server-Sent Events (SSE) for real-time responses
- **State Management:** Vue Composition API (Pinia for complex state)

**Related Documentation:**
- **Nuxt 4 Setup Guide:** `/docs/nuxt4-setup.md`
- **Nuxt 4 Implementation Risks:** `/docs/nuxt4-implementation-risks.md`
- **Backend API Guide:** `/docs/backend-api-guide.md`
- **Architecture:** `/context/architecture.md` (Section 1: Frontend Layer)
- **Security Improvements:** `/docs/security-improvements.md`

**What's New in Nuxt 4 Implementation:**
1. ✅ JWT-based authentication with refresh tokens
2. ✅ Server-Sent Events (SSE) streaming for AI responses
3. ✅ Dynamic Programs API for managing organizational categories
4. ✅ Enhanced security (admin-only metrics endpoint)
5. ✅ TypeScript throughout for type safety
6. ✅ Modern Vue 3 components with Nuxt UI
7. ✅ Docker containerization with hot module replacement

---

## Document Overview

This document specifies the user experience, user roles, frontend features, and business logic for the Org Archivist frontend application. This complements the technical architecture and application requirements documents with detailed frontend-specific requirements.

**Implementation Status:**
- **Original Target:** Streamlit (MVP prototype)
- **Current Target:** Nuxt 4 (Vue 3 + TypeScript production application)
- **Business Logic:** Preserved and enhanced from original requirements
- **UI Components:** Updated from Streamlit to Vue 3/Nuxt UI components
- **Authentication:** Upgraded from basic auth to JWT-based system
- **Real-time:** Added SSE streaming for AI responses

---

## Nuxt 4 Implementation Overview

### Technology Stack

**Frontend Framework:**
- **Nuxt 4**: Latest Vue 3 meta-framework with SSR/SSG capabilities
- **Vue 3**: Composition API for reactive components
- **TypeScript**: Strict type checking throughout application
- **Nuxt UI**: Official Nuxt UI component library (built on Tailwind CSS)
- **Nuxt Icon**: Icon library with 200,000+ icons

**Authentication & Security:**
- **JWT Tokens**: Access tokens (5 hours) and refresh tokens (7 days)
- **Session Management**: Database-backed session tracking
- **Role-Based Access Control (RBAC)**: Three roles (Admin, Editor, Writer)
- **Secure Headers**: Authorization: Bearer {token}
- **Protected Routes**: Automatic route guards for authenticated pages

**Real-Time Communication:**
- **Server-Sent Events (SSE)**: Streaming AI responses
- **EventSource API**: Client-side SSE handling
- **ReadableStream**: Alternative streaming implementation
- **Fetch API**: Standard HTTP requests with streaming support

**API Integration:**
- **Fetch API**: Native browser API for HTTP requests
- **Composables**: Reusable `useApi()`, `useAuth()`, `useStreaming()`
- **Error Handling**: Centralized error handling with user-friendly messages
- **Type Safety**: Full TypeScript types for all API requests/responses

### Key Features Comparison: Streamlit vs Nuxt 4

| Feature | Streamlit (Original) | Nuxt 4 (Current) |
|---------|---------------------|------------------|
| **UI Framework** | Streamlit Python | Vue 3 + Nuxt UI |
| **Language** | Python | TypeScript |
| **Authentication** | Basic/Session | JWT-based |
| **Real-time Updates** | Session state | SSE streaming |
| **Component Library** | Streamlit widgets | Nuxt UI components |
| **State Management** | st.session_state | Composition API + Pinia |
| **Routing** | Page-based | File-based + dynamic |
| **Deployment** | Python container | Node.js container |
| **Hot Reload** | Streamlit rerun | Vite HMR |
| **Type Safety** | None | Full TypeScript |

### New Capabilities in Nuxt 4

**1. Dynamic Programs Management**
- CRUD operations for organizational program categories
- API endpoints: GET/POST/PUT/DELETE `/api/programs`
- Real-time program list updates
- Validation and display ordering
- Active/inactive program states

**2. Server-Sent Events (SSE) Streaming**
- Real-time AI response streaming via `/api/query/stream`
- Chat streaming via `/api/chat/{conversation_id}/stream`
- Progressive content display (typewriter effect)
- Sources delivered before content
- Metadata delivered after completion
- Graceful error handling during streams

**3. Enhanced Authentication**
- JWT access and refresh tokens
- Automatic token refresh before expiration
- Session validation endpoint
- Role-based component rendering
- Protected API routes with automatic 401/403 handling

**4. Modern UI/UX**
- Responsive design with Tailwind CSS
- Dark mode support (via Nuxt UI)
- Loading states and skeleton screens
- Toast notifications for user feedback
- Modal dialogs and slide-overs
- Smooth animations and transitions

**5. Developer Experience**
- TypeScript autocomplete for API calls
- Composable functions for reusability
- Auto-imported components
- Hot module replacement (HMR)
- Built-in testing utilities
- Type-safe routing

---

## ⚠️ IMPORTANT: Document Authority & Conflicts Resolution

**This document (frontend-requirements.md) supersedes architecture.md and requirements.md for all frontend-specific features and related backend changes.**

### Document Status & Authority

**Effective Date**: October 21, 2024

**Authority Declaration**:
- This document represents the **authoritative specification** for the Org Archivist frontend and related backend features going forward
- Where conflicts exist with `architecture.md` or `requirements.md`, **this document takes precedence**
- Previous documents remain valid for backend implementation details not covered here

### Identified Conflicts & Resolutions

The following conflicts have been identified between the original architecture/requirements documents and this frontend requirements document. **Frontend-requirements.md takes precedence in all cases.**

---

#### **CONFLICT 1: User Management & Authentication**

**Original Documents** (architecture.md, requirements.md):
- Mentioned "basic authentication" vaguely in security section (REQ-NFR-003)
- Database has `created_by VARCHAR(100)` and `user_id VARCHAR(100)` fields
- No user roles or permissions defined
- No users table specified

**Frontend Requirements** (THIS DOCUMENT - AUTHORITATIVE):
- Three specific roles: **Administrator**, **Editor**, **Writer**
- Detailed permission matrix for all features
- Role-based access control (RBAC) throughout application
- User management functionality for Administrators

**RESOLUTION**:
- **ADD new database tables**:
  ```sql
  CREATE TABLE users (
      user_id UUID PRIMARY KEY,
      email VARCHAR(255) UNIQUE NOT NULL,
      full_name VARCHAR(255) NOT NULL,
      role VARCHAR(50) NOT NULL,  -- 'administrator', 'editor', 'writer'
      active BOOLEAN DEFAULT TRUE,
      created_at TIMESTAMP NOT NULL,
      last_login TIMESTAMP,
      created_by UUID REFERENCES users(user_id),
      CONSTRAINT valid_role CHECK (role IN ('administrator', 'editor', 'writer'))
  );

  CREATE TABLE user_sessions (
      session_id UUID PRIMARY KEY,
      user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
      created_at TIMESTAMP NOT NULL,
      expires_at TIMESTAMP NOT NULL,
      last_activity TIMESTAMP NOT NULL
  );
  ```
- Update all existing tables with `user_id UUID REFERENCES users(user_id)` instead of `VARCHAR(100)`
- Implement role-based middleware in FastAPI backend
- Add user management endpoints (Admin only)

**Impact**: Backend API needs user authentication endpoints, session management, and role checking middleware.

---

#### **CONFLICT 2: Writing Styles vs. Prompt Templates**

**Original Documents**:
- Table: `prompt_templates`
- Manually created/edited prompts
- Categories: audience, section, brand_voice, custom
- Simple text content storage

**Frontend Requirements** (THIS DOCUMENT - AUTHORITATIVE):
- Feature: **Writing Styles** (not just templates)
- AI-generated style prompts from user-provided writing samples
- Types: Grant, Proposal, Report (not categories)
- Rich workflow: sample upload → AI analysis → prompt generation → review/revision
- Analysis metadata stored (vocabulary, structure, tone, etc.)

**RESOLUTION**:
- **REPLACE `prompt_templates` table with `writing_styles` table**:
  ```sql
  CREATE TABLE writing_styles (
      style_id UUID PRIMARY KEY,
      name VARCHAR(100) NOT NULL,
      type VARCHAR(50) NOT NULL,  -- 'grant', 'proposal', 'report'
      description TEXT,
      prompt_content TEXT NOT NULL,  -- The actual style prompt
      samples JSONB,  -- Array of original writing samples
      analysis_metadata JSONB,  -- AI analysis results (vocabulary, structure, etc.)
      sample_count INTEGER,
      active BOOLEAN DEFAULT TRUE,
      created_at TIMESTAMP NOT NULL,
      updated_at TIMESTAMP NOT NULL,
      created_by UUID REFERENCES users(user_id),
      CONSTRAINT valid_type CHECK (type IN ('grant', 'proposal', 'report'))
  );
  ```
- Keep `prompt_templates` table for system-level prompts (audience, section)
- Add backend endpoint: `POST /api/writing-styles/analyze` for AI sample analysis
- Add backend endpoint: `POST /api/writing-styles` for creating styles
- Add backend endpoint: `GET/PUT/DELETE /api/writing-styles/{id}` for management

**Impact**: New backend service for AI-powered writing style analysis, new API endpoints, database migration.

---

#### **CONFLICT 3: Past Outputs Dashboard vs. Conversations**

**Original Documents**:
- Tables: `conversations` and `messages`
- Basic chat history tracking
- No output persistence or success tracking
- No searchable outputs dashboard

**Frontend Requirements** (THIS DOCUMENT - AUTHORITATIVE):
- Feature: **Past Outputs Dashboard**
- All generated artifacts saved automatically
- Success tracking for grants/proposals (Awarded/Not Awarded/Pending)
- Award amounts, funder names, dates
- Searchable, filterable output library
- Links to source conversations

**RESOLUTION**:
- **ADD new `outputs` table**:
  ```sql
  CREATE TABLE outputs (
      output_id UUID PRIMARY KEY,
      conversation_id UUID REFERENCES conversations(conversation_id),
      title VARCHAR(500) NOT NULL,  -- Auto-generated or user-provided
      content TEXT NOT NULL,
      output_type VARCHAR(50) NOT NULL,  -- 'grant', 'proposal', 'report', 'letter', 'other'

      -- Context at time of generation
      writing_style_id UUID REFERENCES writing_styles(style_id),
      audience VARCHAR(100),
      section VARCHAR(100),
      tone DECIMAL(2,1),  -- 0.0-1.0

      -- Sources used
      sources JSONB,  -- Array of {doc_id, chunk_ids, relevance_scores}

      -- Quality metrics
      confidence_score DECIMAL(3,2),
      quality_metrics JSONB,

      -- Grant/Proposal success tracking
      status VARCHAR(50),  -- 'draft', 'submitted', 'pending', 'awarded', 'not_awarded', 'unknown'
      funder_name VARCHAR(255),
      requested_amount DECIMAL(12,2),
      awarded_amount DECIMAL(12,2),
      submission_date DATE,
      decision_date DATE,
      success_notes TEXT,

      -- Metadata
      word_count INTEGER,
      created_at TIMESTAMP NOT NULL,
      created_by UUID REFERENCES users(user_id),
      saved_at TIMESTAMP,  -- When explicitly saved by user

      CONSTRAINT valid_output_type CHECK (output_type IN ('grant', 'proposal', 'report', 'letter', 'other')),
      CONSTRAINT valid_status CHECK (status IN ('draft', 'submitted', 'pending', 'awarded', 'not_awarded', 'unknown'))
  );

  CREATE INDEX idx_outputs_type ON outputs(output_type);
  CREATE INDEX idx_outputs_status ON outputs(status);
  CREATE INDEX idx_outputs_created_by ON outputs(created_by);
  CREATE INDEX idx_outputs_created_at ON outputs(created_at);
  ```
- Update `conversations` table to link to outputs
- Add backend endpoints for output management: `GET/POST/PUT/DELETE /api/outputs`
- Add filtering, search, and export functionality

**Impact**: New database table, new backend endpoints, integration with conversation flow.

---

#### **CONFLICT 4: Document Sensitivity Classification**

**Original Documents**:
- No mention of document sensitivity levels
- No access control based on document sensitivity

**Frontend Requirements** (THIS DOCUMENT - AUTHORITATIVE):
- **MVP**: Public documents only (with user confirmation)
- **Future**: 5-level sensitivity classification
  - Public
  - Internal
  - Confidential
  - Restricted
  - Highly Confidential
- Access control based on user role and document sensitivity

**RESOLUTION**:
- **ADD to `documents` table** (MVP):
  ```sql
  ALTER TABLE documents ADD COLUMN sensitivity_confirmed BOOLEAN DEFAULT FALSE;
  ```
- **ADD to `documents` table** (Future):
  ```sql
  ALTER TABLE documents ADD COLUMN sensitivity_level VARCHAR(50) DEFAULT 'public';
  ALTER TABLE documents ADD CONSTRAINT valid_sensitivity
      CHECK (sensitivity_level IN ('public', 'internal', 'confidential', 'restricted', 'highly_confidential'));
  ```
- Update document upload form with sensitivity warning and confirmation checkbox
- Add retrieval filtering based on user role and document sensitivity (future)

**Impact**: Minor database change for MVP, more extensive changes post-MVP.

---

#### **CONFLICT 5: Conversation Context Storage**

**Original Documents**:
- `conversations` table has basic fields: id, name, created_at, updated_at, user_id
- No storage for conversation parameters/context

**Frontend Requirements** (THIS DOCUMENT - AUTHORITATIVE):
- Conversations need to preserve context:
  - Writing style selected
  - Audience type
  - Section type
  - Tone level
  - Document filters
- Version tracking for artifacts within conversation
- Ability to restore full context when loading conversation

**RESOLUTION**:
- **UPDATE `conversations` table**:
  ```sql
  ALTER TABLE conversations ADD COLUMN context JSONB;
  -- Structure: {
  --   "writing_style_id": "uuid",
  --   "audience": "Federal RFP",
  --   "section": "Organizational Capacity",
  --   "tone": 0.9,
  --   "filters": {...}
  -- }

  ALTER TABLE conversations ADD COLUMN output_id UUID REFERENCES outputs(output_id);
  -- Links conversation to final saved output

  ALTER TABLE conversations ADD COLUMN artifacts JSONB;
  -- Array of artifact versions within conversation
  -- Structure: [{version: 1, content: "...", word_count: 500, timestamp: "..."}]
  ```

**Impact**: Database migration to add JSONB columns, backend logic to save/restore context.

---

#### **CONFLICT 6: Deployment Model**

**Original Documents**:
- Docker Compose configuration shown
- Single database `foundation_historian`
- Not explicitly single-tenant or multi-tenant

**Frontend Requirements** (THIS DOCUMENT - AUTHORITATIVE):
- **MVP**: Explicitly single-tenant
  - Each organization gets isolated containerized instance
  - No data commingling between organizations
  - Separate database, vector store, and application per org
- **Future**: Consider multi-tenant with row-level security

**RESOLUTION**:
- **NO DATABASE CHANGES NEEDED for MVP**
- Document deployment pattern clearly
- Each organization receives:
  - Own Docker Compose stack
  - Own PostgreSQL database
  - Own Qdrant collection
  - Own FastAPI + Streamlit containers
- Container naming: `org-archivist-{org-name}-frontend`, `org-archivist-{org-name}-backend`, etc.

**Impact**: Deployment/DevOps changes, no application code changes for MVP.

---

#### **CONFLICT 7: Audit Logging**

**Original Documents**:
- `audit_log` table mentioned in SQL schema
- Basic logging structure

**Frontend Requirements** (THIS DOCUMENT - AUTHORITATIVE):
- Need comprehensive audit logging for:
  - User actions (login, logout, role changes)
  - Document operations (upload, delete)
  - Writing style creation/editing
  - Output generation and success tracking
  - Settings changes

**RESOLUTION**:
- **EXPAND `audit_log` table**:
  ```sql
  CREATE TABLE audit_log (
      log_id UUID PRIMARY KEY,
      user_id UUID REFERENCES users(user_id),
      action VARCHAR(100) NOT NULL,  -- 'login', 'upload_document', 'create_style', etc.
      resource_type VARCHAR(50),  -- 'document', 'writing_style', 'output', 'user', etc.
      resource_id UUID,
      details JSONB,  -- Action-specific details
      ip_address INET,
      user_agent TEXT,
      created_at TIMESTAMP NOT NULL
  );

  CREATE INDEX idx_audit_user ON audit_log(user_id);
  CREATE INDEX idx_audit_action ON audit_log(action);
  CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id);
  CREATE INDEX idx_audit_created ON audit_log(created_at);
  ```

**Impact**: Middleware to log all important actions, database table for audit trail.

---

### Summary of Required Database Changes

#### New Tables (to be created):
1. ✅ **users** - User authentication and roles
2. ✅ **user_sessions** - Session management
3. ✅ **writing_styles** - AI-generated writing style prompts (replaces prompt_templates for this purpose)
4. ✅ **outputs** - Past outputs dashboard with success tracking
5. ✅ **audit_log** - Comprehensive audit logging (expand if already exists)

#### Tables to Modify:
1. ✅ **documents** - Add `sensitivity_confirmed` (MVP), `sensitivity_level` (future)
2. ✅ **conversations** - Add `context JSONB`, `output_id UUID`, `artifacts JSONB`
3. ✅ **prompt_templates** - Keep for system-level prompts (audience, section), separate from writing_styles

#### Tables to Keep As-Is:
- ✅ **document_programs** - No changes
- ✅ **document_tags** - No changes
- ✅ **messages** - No changes (may add `user_id` reference)
- ✅ **system_config** - No changes

---

### Migration Path

**Phase 1 - MVP (Immediate)**:
1. Create `users` and `user_sessions` tables
2. Create `writing_styles` table
3. Create `outputs` table
4. Modify `conversations` table (add context, output_id, artifacts)
5. Modify `documents` table (add sensitivity_confirmed)
6. Update all `user_id` fields from VARCHAR to UUID with foreign keys
7. Create `audit_log` table

**Phase 2 - Post-MVP**:
1. Add `sensitivity_level` to documents table
2. Implement role-based document access
3. Add user clearance levels
4. Expand audit logging

---

### API Endpoint Changes Required

#### Authentication Endpoints (✅ IMPLEMENTED):
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User authentication (returns JWT tokens)
- `POST /api/auth/logout` - User logout (invalidates session)
- `GET /api/auth/session` - Validate current session
- `GET /api/auth/me` - Get current user details

#### User Management Endpoints (Admin only):
- `GET /api/users` - List users
- `POST /api/users` - Create user
- `PUT /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Deactivate user

#### Programs API (✅ IMPLEMENTED):
- `GET /api/programs` - List all programs with filtering
- `GET /api/programs/active` - Get active program names only
- `POST /api/programs` - Create new program (Admin/Editor)
- `PUT /api/programs/{id}` - Update program (Admin/Editor)
- `DELETE /api/programs/{id}` - Delete/deactivate program (Admin)

#### Writing Styles API:
- `POST /api/writing-styles/analyze` - AI analysis of writing samples
- `GET /api/writing-styles` - List writing styles
- `POST /api/writing-styles` - Create writing style
- `PUT /api/writing-styles/{id}` - Update writing style
- `DELETE /api/writing-styles/{id}` - Delete writing style

#### Outputs API:
- `GET /api/outputs` - List/search past outputs
- `GET /api/outputs/{id}` - Get specific output
- `POST /api/outputs` - Save output from conversation
- `PUT /api/outputs/{id}` - Update output (success tracking)
- `DELETE /api/outputs/{id}` - Delete output

#### Streaming Endpoints (✅ IMPLEMENTED):
- `POST /api/query/stream` - Generate content with SSE streaming
- `POST /api/chat/{conversation_id}/stream` - Chat with SSE streaming

#### Admin Endpoints:
- `GET /api/metrics` - System metrics (✅ Admin-only authentication added)
- `GET /api/audit-log` - View audit log (Admin only)

#### Endpoints to Modify:
- ✅ All endpoints: Authentication middleware added
- ✅ All endpoints: Role checking implemented
- `POST /api/documents/upload` - Add sensitivity confirmation validation
- `POST /api/chat` - Save context to conversations table
- `GET /api/conversations/{id}` - Include context and artifacts in response

---

### Frontend Component Changes Required

Based on Nuxt 4 implementation, the following Vue 3 components are required:

#### Authentication Components (NEW - Nuxt 4):
1. **LoginPage.vue** (`pages/login.vue`) - JWT-based authentication
   - Email/password form with validation
   - Token storage in localStorage/cookie
   - Redirect to dashboard after successful login
   - Error handling for invalid credentials

2. **AuthGuard Middleware** (`middleware/auth.ts`) - Route protection
   - Verify JWT token presence and validity
   - Redirect to login if unauthenticated
   - Role-based route restrictions
   - Automatic token refresh

#### User Management Components (Admin):
1. **UserManagementPage.vue** - Admin interface for users
   - User list with UTable component
   - Create/edit user modal (UModal)
   - Role assignment dropdown (USelectMenu)
   - Activate/deactivate toggle
   - Search and filter users

#### Programs Management Components (NEW - Nuxt 4):
1. **ProgramsPage.vue** - Manage organizational programs
   - Programs list with display ordering
   - Create/edit program modal
   - Active/inactive toggle
   - Drag-and-drop reordering
   - Used by document upload for tagging

#### Writing Styles Components:
1. **WritingStylesCreator.vue** - AI-powered style creation
   - Multi-step form wizard
   - Sample text input (3-7 samples)
   - AI analysis progress indicator
   - Generated style prompt editor
   - Preview and refinement interface

2. **WritingStylesManager.vue** - Manage writing styles
   - Styles list with UCard components
   - Edit/delete/duplicate actions
   - Test style preview
   - Active/inactive states

#### Document Management Components:
1. **DocumentUploadPage.vue** - Enhanced upload interface
   - File drag-and-drop (UFileUpload)
   - Metadata form with program multi-select
   - Sensitivity confirmation checkbox
   - Upload progress with UProgress
   - Batch upload support

2. **DocumentLibraryPage.vue** - Document browser
   - Searchable, filterable UTable
   - Quick filters for type, year, program
   - Document preview modal
   - Bulk delete actions (Admin/Editor)

#### AI Writing Assistant Components:
1. **ChatInterface.vue** - Main chat interface
   - Message list with streaming support
   - Input box with UTextarea
   - Context sidebar (style, audience, section)
   - Sources panel with expandable cards
   - Artifact display panel
   - SSE streaming integration

2. **StreamingMessageComponent.vue** - Real-time message display
   - Progressive content rendering
   - Typewriter effect animation
   - Citation highlighting
   - Copy and regenerate actions

#### Outputs Management Components:
1. **PastOutputsPage.vue** - Output library dashboard
   - Outputs grid/list with UCard
   - Search and filter sidebar
   - Success indicator badges
   - Award amount display
   - Quick actions (download, duplicate)

2. **SuccessTrackingForm.vue** - Grant/proposal outcome tracking
   - Status dropdown (Submitted, Pending, Awarded, Not Awarded)
   - Funder name input
   - Award amount fields
   - Dates (submission, decision)
   - Notes textarea

#### Layout Components:
1. **DefaultLayout.vue** - Main application layout
   - Navigation sidebar with role-based menu items
   - User profile dropdown
   - Dark mode toggle
   - Logout button

2. **NavigationSidebar.vue** - App navigation
   - Collapsible sidebar
   - Active route highlighting
   - Icon + label menu items
   - Role-restricted menu items

#### Reusable Components:
1. **ApiErrorAlert.vue** - Error display
2. **LoadingSpinner.vue** - Loading states
3. **ConfirmDialog.vue** - Confirmation modals
4. **ToastNotification.vue** - User feedback
5. **ProtectedRoute.vue** - Auth wrapper component

---

### Testing Requirements

Due to these conflicts and changes, the following additional testing is required:

1. **User authentication and authorization** - Role-based access control
2. **Writing style AI analysis** - Quality and accuracy of style extraction
3. **Conversation context persistence** - Save/restore full context across sessions
4. **Output tracking and search** - Dashboard functionality, filtering, export
5. **Database migrations** - Data integrity during schema changes
6. **Audit logging** - Comprehensive action tracking

---

**End of Conflicts Resolution Section**

---

## 1. Deployment Model (MVP)

### Single-Tenant Containerization

**REQ-DEPLOY-001: Isolated Instances**
- Each organization receives its own containerized instance of Org Archivist
- No data commingling between organizations
- Each instance has independent database, vector store, and application containers
- Simplifies security, privacy, and data management for MVP

**REQ-DEPLOY-002: Future Multi-Tenancy**
- Post-MVP: Consider multi-tenant architecture with organization-level data isolation
- Tenant identification via subdomain or organization ID
- Row-level security in database for data separation
- Shared infrastructure with isolated data stores

---

## 2. User Roles & Permissions

### Role Definitions

**REQ-ROLE-001: Administrator Role**

Full system access with the following capabilities:
- User management (create, edit, deactivate users)
- Plan management (future feature - subscription/billing)
- Writing style management (create, edit, delete writing styles)
- Prompt management (create, edit, delete prompts)
- Document library management (upload, view, delete documents)
- AI writing assistant access (full access to chat interface)
- System settings configuration
- Usage analytics and reporting (future)

**REQ-ROLE-002: Editor Role**

Extended access without user/plan management:
- Writing style management (create, edit, delete writing styles)
- Prompt management (create, edit, delete prompts)
- Document library management (upload, view, delete documents)
- AI writing assistant access (full access to chat interface)
- View system settings (cannot modify core settings)
- View usage analytics (future)

**Cannot perform:**
- User management
- Plan/billing management
- System configuration changes

**REQ-ROLE-003: Writer Role**

Basic user access focused on content creation:
- Writing style selection (choose from available styles)
- AI writing assistant access (full access to chat interface)
- Document library viewing (cannot upload or delete)
- Past outputs viewing (can see all past generations)
- Save and manage own writing outputs
- View own usage statistics (future)

**Cannot perform:**
- User management
- Writing style creation/editing
- Prompt management
- Document upload/deletion
- System settings access

### Permission Matrix

| Feature | Administrator | Editor | Writer |
|---------|--------------|--------|--------|
| Manage Users | ✓ | ✗ | ✗ |
| Manage Plan/Billing | ✓ | ✗ | ✗ |
| Create/Edit Writing Styles | ✓ | ✓ | ✗ |
| Select Writing Styles | ✓ | ✓ | ✓ |
| Manage Prompts | ✓ | ✓ | ✗ |
| Upload Documents | ✓ | ✓ | ✗ |
| Delete Documents | ✓ | ✓ | ✗ |
| View Document Library | ✓ | ✓ | ✓ |
| AI Writing Assistant | ✓ | ✓ | ✓ |
| View Past Outputs | ✓ | ✓ | ✓ |
| Mark Output Success | ✓ | ✓ | ✓ |
| System Settings | ✓ | View | ✗ |

---

## 3. Document Sensitivity & Classification

### MVP: Public Documents Only

**REQ-SENS-001: MVP Restriction**
- System shall accept **only public-facing documents** during MVP phase
- Users shall be warned during upload: "Only upload public-facing documents. Do not upload confidential, financial, or sensitive operational documents."
- Upload form shall include checkbox: "I confirm this document is public-facing and appropriate for AI processing"
- Examples of appropriate documents:
  - Published grant proposals
  - Annual reports (public versions)
  - Public program descriptions
  - Published impact reports
  - Public-facing strategic plans
  - Donor communications

**REQ-SENS-002: Prohibited Content (MVP)**
- System shall explicitly warn against uploading:
  - Financial documents (budgets, audits, tax returns)
  - Client/beneficiary information (case notes, personal data)
  - Confidential donor information
  - Internal personnel documents
  - Proprietary operational documents
  - Board minutes and executive session notes
  - Unpublished strategic plans

### Future: Sensitivity Tagging

**REQ-SENS-003: Future Sensitivity Levels**
- Post-MVP: Add sensitivity classification for documents:
  - **Public**: Public-facing content, no restrictions
  - **Internal**: Internal use only, staff access
  - **Confidential**: Restricted access, approved staff only
  - **Restricted**: Highly restricted, senior leadership only
  - **Highly Confidential**: Executive access only

**REQ-SENS-004: Future Access Control**
- Users can only retrieve/access documents at or below their clearance level
- AI writing assistant respects sensitivity levels when retrieving sources
- Audit logging for access to Confidential+ documents
- Document sensitivity can be changed by Administrator/Editor only

---

## 4. Writing Styles Feature

### Purpose & Overview

The Writing Styles feature allows organizations to teach the AI their unique writing voice by analyzing sample documents and creating reusable style prompts.

### Writing Style Types

**REQ-STYLE-001: Style Types (MVP)**

Three pre-configured style types available:
- **Grant**: Style for grant proposals and applications
- **Proposal**: Style for general proposals (non-grant)
- **Report**: Style for reports and communications

Each type has different default parameters and guidance for sample selection.

**REQ-STYLE-002: Style Types (Future)**
- Additional types: Letter, Email, Website Copy, Social Media, Press Release
- Premium plans: Custom style types with user-defined names
- Style type inheritance (base style + variations)

### Style Creation Workflow

**REQ-STYLE-003: Sample Document Upload**

When creating a new writing style:

1. User selects style type (Grant, Proposal, or Report)
2. System displays guidance: "Paste 3-7 representative writing samples that demonstrate your desired style"
3. Text input area supports:
   - Rich text formatting (bold, italic, underline)
   - Paragraph preservation
   - Lists (numbered and bulleted)
   - Basic structure (headings)
4. User pastes samples (minimum 3, maximum 7)
5. System validates:
   - Minimum word count per sample (200 words)
   - Total combined word count (1000-10000 words recommended)
   - At least 3 samples provided

**REQ-STYLE-004: AI Analysis & Prompt Generation**

After samples submitted:

1. System sends samples to Claude API for analysis
2. AI analyzes samples for:
   - **Vocabulary selection**: Common words, technical terms, jargon usage, complexity level
   - **Sentence structure**: Average length, complexity, variety, passive vs. active voice
   - **Thought composition**: Logical flow, argument structure, use of evidence
   - **Paragraph structure**: Length, topic sentences, transitions, coherence
   - **Transitions**: Connective phrases, logical connectors, flow between ideas
   - **Tone**: Formality level, warmth, directness, confidence
   - **Perspective**: 1st person organizational voice, 3rd person, etc.
   - **Data integration**: How statistics and evidence are woven into narrative
3. AI generates draft style prompt (1000-2000 words)
4. Draft prompt includes:
   - Style overview summary
   - Detailed style guidelines organized by category
   - Specific examples extracted from samples
   - Do's and Don'ts based on analysis
5. Processing time: 30-60 seconds
6. User presented with draft prompt for review

**REQ-STYLE-005: Prompt Review & Revision**

User reviews AI-generated draft style prompt:

1. Draft displayed in editable text area with rich formatting
2. User can:
   - Edit any part of the prompt
   - Add additional guidelines
   - Remove or modify examples
   - Adjust emphasis on different aspects
   - Save as draft for later editing
3. AI assistance available:
   - "Make more specific" - Add more detail to guidelines
   - "Make more concise" - Reduce verbosity
   - "Add examples" - Extract more examples from samples
   - "Emphasize [aspect]" - Focus more on specific element
4. Side-by-side preview:
   - Original samples
   - Generated style prompt
   - Test output showing style application

**REQ-STYLE-006: Style Finalization & Storage**

Once user satisfied with prompt:

1. User provides style name (e.g., "Federal Grant Style", "Foundation Proposal Voice")
2. Optional: Add description/notes about when to use this style
3. Style saved to database with:
   - Style ID (UUID)
   - Name
   - Type (Grant/Proposal/Report)
   - Prompt content
   - Sample count
   - Created date
   - Last modified date
   - Active/inactive status
   - Created by (user ID)
4. Style immediately available for use in AI writing assistant
5. Style appears in selection dropdown for all users

**REQ-STYLE-007: Style Management**

Administrator and Editor roles can:

- View all writing styles (list view with filters)
- Edit existing styles:
  - Modify prompt content
  - Re-run AI analysis with different samples
  - Version history (future)
- Deactivate styles (remove from active use but preserve)
- Delete styles (requires confirmation)
- Duplicate styles (create variations)
- Export/import styles (JSON format)

Writer role can:
- View all active styles
- Select styles for use in AI assistant
- Cannot edit or create styles

### Style Application

**REQ-STYLE-008: Style Selection in AI Assistant**

When using AI writing assistant:

1. User selects writing style from dropdown:
   - Organized by type (Grant, Proposal, Report)
   - Shows style name and description
   - Indicates when style was last updated
2. Selected style prompt automatically included in system prompt
3. Style selection persists across conversation turns
4. User can change style mid-conversation (creates new conversation context)
5. Output reflects style guidelines:
   - Vocabulary matches analyzed samples
   - Sentence structure mirrors examples
   - Transitions follow identified patterns
   - Overall tone and voice consistent

**REQ-STYLE-009: Style Quality Indicators**

System provides feedback on style application:

- **Style adherence score**: 0-100% indicating how well output matches style
- **Vocabulary match**: Percentage of output using style-appropriate vocabulary
- **Structure alignment**: Whether output follows style's structural patterns
- **Tone consistency**: Whether output maintains the defined tone
- Warnings if output significantly deviates from style guidelines

---

## 5. Document Library

### Purpose

Central repository for all organizational documents used by AI for content generation.

### Library Views & Access

**REQ-LIB-001: View Permissions**

All roles (Administrator, Editor, Writer) can:
- View document library
- See all uploaded documents
- View document metadata
- Search and filter documents
- See document statistics
- Preview document excerpts

**REQ-LIB-002: Upload Permissions**

Only Administrator and Editor can:
- Upload new documents
- Batch upload multiple documents
- Edit document metadata
- Re-process documents

**REQ-LIB-003: Delete Permissions**

Only Administrator and Editor can:
- Delete individual documents
- Bulk delete selected documents
- Permanently remove documents from vector database
- View deletion audit log

### Library Interface

**REQ-LIB-004: Document Table**

Display all documents in sortable, filterable table:

| Filename | Type | Year | Programs | Outcome | Chunks | Upload Date | Actions |
|----------|------|------|----------|---------|--------|-------------|---------|
| Grant_2024.pdf | Grant Proposal | 2024 | Education, Youth | Funded | 47 | 2024-10-15 | View, Delete |

Features:
- Sortable columns (click header to sort)
- Multi-select checkboxes for bulk actions
- Pagination (25/50/100 per page)
- Search bar (searches filename and content)
- Filter panel (type, year, program, outcome)
- Total count and statistics at top

**REQ-LIB-005: Document Upload Interface**

Upload interface includes:
- Drag-and-drop file area
- Browse files button
- Multiple file selection
- Upload progress indicators
- Metadata form for each document:
  - Document type (required)
  - Year (required)
  - Programs (multi-select, required)
  - Outcome (optional: N/A, Funded, Not Funded, Pending)
  - Tags (comma-separated)
  - Notes (optional)
- Public document confirmation checkbox (MVP)
- Preview before processing
- Batch metadata application option

**REQ-LIB-006: Document Details View**

Clicking document opens detail panel:
- Full metadata display
- Document statistics:
  - File size
  - Word count
  - Chunk count
  - Processing date
- Chunk preview (first 5 chunks)
- Edit metadata (Admin/Editor only)
- Download original file
- View in context (show where document was used in outputs)
- Delete button (Admin/Editor only, requires confirmation)

**REQ-LIB-007: Library Statistics**

Dashboard showing:
- Total documents: 142
- Total chunks: 6,847
- Distribution by type (chart):
  - Grant Proposals: 67
  - Annual Reports: 28
  - Program Descriptions: 31
  - Impact Reports: 16
- Distribution by outcome (funded proposals)
- Most recent uploads
- Most frequently retrieved documents
- Storage usage

---

## 6. Past Outputs Dashboard

### Purpose

Track all content generated by the AI writing assistant for review, reuse, and quality assessment.

### Output Storage & Organization

**REQ-OUTPUT-001: Automatic Saving**

System automatically saves all generated outputs:
- Final artifacts from conversations
- Explicitly saved drafts during conversation
- User-initiated saves
- Auto-saves every 5 minutes during active writing

Each output includes:
- Output ID (UUID)
- Output text content
- Writing style used
- Audience type
- Section type
- Generation date
- User who created it
- Conversation ID (link to full chat)
- Sources used (document references)
- Quality scores
- Word count
- Success indicator (for grants/proposals)

**REQ-OUTPUT-002: Success Tracking (Grants & Proposals)**

For grant and proposal outputs:
- Status field: Draft, Submitted, Pending, Awarded, Not Awarded, Unknown
- Award amount field (if awarded)
- Funder name
- Submission date
- Decision date
- Notes on outcome

This data enables:
- Future fine-tuning on successful content
- Analysis of what works for different funders
- Success rate tracking by writing style
- ROI calculation on successful grants

**REQ-OUTPUT-003: Dashboard Views**

Multiple views for accessing past outputs:

1. **Recent Outputs** (default view)
   - Last 50 outputs, newest first
   - Quick preview cards showing:
     - Title/first line
     - Date created
     - Type (Grant/Proposal/Report)
     - Success indicator (if applicable)
     - Word count
     - Quick actions (View, Download, Duplicate)

2. **By Type** (filtered view)
   - Filter by: Grant, Proposal, Report, Other
   - Group by: Audience, Section, Style
   - Sort by: Date, Success rate, Word count

3. **Successful Outputs** (grants/proposals only)
   - Show only outputs marked as "Awarded"
   - Sort by award amount
   - Filter by funder, year, program
   - Use for future content generation inspiration

4. **Search** (full-text search)
   - Search across all output content
   - Filter results by date range, type, success
   - Preview search results with highlighting

**REQ-OUTPUT-004: Output Actions**

For each past output:
- **View**: Open in full-screen reader mode
- **Download**: Export as .txt, .docx, or .pdf
- **Duplicate**: Create new writing session with same parameters
- **Edit**: Open in AI assistant to continue working
- **Mark Success**: Add outcome information (grant award, proposal win)
- **Share**: Share with team (future - collaborative features)
- **Delete**: Remove from dashboard (requires confirmation)
- **Compare**: Side-by-side comparison with other outputs (future)

### Access Permissions

**REQ-OUTPUT-005: View Permissions**

All roles can:
- View all past outputs from all users
- Search and filter outputs
- See success indicators
- Download outputs

This supports:
- Knowledge sharing across team
- Learning from successful content
- Maintaining institutional memory
- Collaborative improvement

**REQ-OUTPUT-006: Edit/Delete Permissions**

Users can:
- Edit their own outputs
- Delete their own outputs

Administrator and Editor can:
- Edit any output
- Delete any output
- Bulk manage outputs
- Export all outputs for backup

---

## 7. AI Writing Assistant (Chat Interface)

### Core Interaction Model

**REQ-CHAT-001: Conversational Interface**

Primary interface for AI-assisted content creation:
- Chat-style layout similar to Claude, ChatGPT, etc.
- Left sidebar: Conversation history
- Center panel: Active conversation
- Right sidebar: Context panel (sources, settings, style info)
- Message-based interaction with persistent context

**REQ-CHAT-002: Nuxt 4 Implementation**

Using Vue 3 composition API with Nuxt UI components:
- **Message Display**: Custom `ChatMessage.vue` component with UCard
- **User Input**: UTextarea with send button
- **State Management**: Vue `ref()` and `reactive()` for conversation state
- **Sidebar**: `USlideover` or persistent navigation panel
- **Streaming**: SSE streaming with `ReadableStream` API for real-time response display

**Component Structure:**
```vue
<template>
  <div class="chat-container flex h-screen">
    <!-- Left Sidebar: Conversation History -->
    <aside class="w-64 border-r">
      <ConversationList
        :conversations="conversations"
        @select="loadConversation"
      />
    </aside>

    <!-- Center: Active Chat -->
    <main class="flex-1 flex flex-col">
      <ChatMessages :messages="currentMessages" />
      <ChatInput @send="handleSendMessage" />
    </main>

    <!-- Right Sidebar: Context & Sources -->
    <aside class="w-80 border-l">
      <ContextPanel :context="conversationContext" />
      <SourcesPanel :sources="currentSources" />
    </aside>
  </div>
</template>

<script setup lang="ts">
const currentMessages = ref<Message[]>([])
const conversations = ref<Conversation[]>([])
const conversationContext = reactive({
  writingStyle: null,
  audience: null,
  section: null,
  tone: 0.8
})

const handleSendMessage = async (message: string) => {
  // Add user message
  currentMessages.value.push({
    role: 'user',
    content: message,
    timestamp: new Date()
  })

  // Stream AI response
  await streamResponse(message)
}
</script>
```

### Conversation Management

**REQ-CHAT-003: New Conversation**

Starting new writing session:
1. User clicks "New Conversation" button
2. Optional: Select conversation template (quick start)
3. Initial configuration panel:
   - **Writing Style**: Dropdown of available styles
   - **Audience**: Federal RFP, Foundation Grant, Corporate, Donor, etc.
   - **Section**: Org Capacity, Program Desc, Impact, Budget, etc.
   - **Tone**: Slider from Very Formal to Conversational
   - **Document Filters** (optional): Limit retrieval to specific docs/years/programs
4. Configuration saved to conversation context
5. Chat interface opens, ready for first message
6. Parameters editable throughout conversation

**REQ-CHAT-004: Conversation History**

Left sidebar shows:
- List of recent conversations (last 50)
- Organized by date (Today, Yesterday, Last 7 days, etc.)
- Each conversation shows:
  - Auto-generated title (from first query)
  - Date/time created
  - Last message preview (truncated)
  - Type indicator (Grant/Proposal/Report)
  - Star/favorite option
- Search conversations
- Filter by date range, type, success
- Delete conversation (requires confirmation)

**REQ-CHAT-005: Loading Past Conversations**

Clicking conversation from history:
- Loads full conversation into center panel
- Restores conversation context (style, audience, section)
- Displays all previous messages
- User can continue conversation where they left off
- Shows sources used in previous responses
- Indicates if conversation was saved as output

**REQ-CHAT-006: Auto-Save**

System automatically saves:
- Every message exchange
- Conversation parameters
- Sources retrieved
- Quality metrics
- Saves to session state (persists during session)
- Saves to database every 5 minutes
- Saves on conversation close

### Message Exchange

**REQ-CHAT-007: User Input**

Message input area:
- Multi-line text input at bottom of chat
- Keyboard shortcuts:
  - Enter: Send message
  - Shift+Enter: New line
  - Ctrl+K: Clear conversation
  - Ctrl+S: Save as output
- Character counter (shows current/max)
- Voice input button (future)
- Attach files/images (future for analysis)

**REQ-CHAT-008: AI Response Display**

When AI responds:
1. Show typing indicator ("Claude is writing...")
2. Stream response tokens as they arrive (typewriter effect)
3. Display response in formatted message bubble:
   - Preserve markdown formatting
   - Render lists, bold, italic
   - Show inline citations [1], [2], etc.
4. Response metadata shown below:
   - Generation time (e.g., "Generated in 4.2s")
   - Confidence score with color coding (green >0.8, yellow 0.6-0.8, red <0.6)
   - Token count
   - Model used
5. Action buttons:
   - Copy to clipboard
   - Regenerate response
   - Continue writing
   - Save as output

**REQ-CHAT-009: SSE Streaming Implementation (Nuxt 4)**

Using Server-Sent Events (SSE) with Fetch ReadableStream API:

```typescript
// composables/useStreamingChat.ts
export const useStreamingChat = () => {
  const config = useRuntimeConfig()
  const { token } = useAuth()

  const streamChatResponse = async (
    query: string,
    onChunk: (content: string) => void,
    onSources?: (sources: any[]) => void,
    onDone?: () => void,
    onError?: (error: any) => void
  ) => {
    try {
      const response = await fetch(`${config.public.apiBase}/api/query/stream`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token.value}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query,
          audience: conversationContext.audience,
          section: conversationContext.section,
          writing_style_id: conversationContext.writingStyleId
        })
      })

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
          if (line.startsWith('data:')) {
            const data = JSON.parse(line.slice(5).trim())

            // Handle different SSE event types
            if (data.sources && onSources) {
              onSources(data.sources)
            } else if (data.content) {
              onChunk(data.content)
            } else if (data.metadata && onDone) {
              onDone()
            }
          }
        }
      }
    } catch (error) {
      onError?.(error)
    }
  }

  return { streamChatResponse }
}
```

**Usage in Component:**
```vue
<script setup lang="ts">
const { streamChatResponse } = useStreamingChat()
const streamingContent = ref('')

const handleSend = async (message: string) => {
  streamingContent.value = ''

  await streamChatResponse(
    message,
    (chunk) => {
      streamingContent.value += chunk  // Typewriter effect
    },
    (sources) => {
      currentSources.value = sources
    },
    () => {
      // Stream complete
      isStreaming.value = false
    }
  )
}
</script>
```

Benefits:
- Immediate user feedback (lower perceived latency)
- Shows generation in real-time (typewriter effect)
- Can cancel long generations (abort controller)
- Better UX for long responses
- Native browser API support
- Works seamlessly with Nuxt SSR

### Context & Sources Panel

**REQ-CHAT-010: Right Sidebar - Sources**

Shows sources retrieved for current/last response:
- Expandable panel for each source
- Source preview:
  ```
  [1] Grant_Proposal_2023.pdf
  Grant Proposal | 2023 | Relevance: 0.89

  "Nebraska Children and Families Foundation has
  demonstrated organizational capacity through 35
  years of service..."

  [View full document] [View all chunks]
  ```
- Click to expand full source text
- Highlight citation in response when source clicked
- Filter sources by relevance threshold
- Export sources list

**REQ-CHAT-011: Right Sidebar - Context Info**

Current conversation context display:
- **Active Style**: "Federal Grant Style"
- **Audience**: Federal RFP
- **Section**: Organizational Capacity
- **Tone**: Very Formal (9/10)
- **Document Filters**:
  - Types: Grant Proposals, Annual Reports
  - Years: 2020-2024
  - Programs: Education, Youth Development
- **Edit** button to modify context

**REQ-CHAT-012: Right Sidebar - Quality Metrics**

For last response:
- **Confidence Score**: 0.87 (High) ✓
- **Groundedness**: 94% (citations supported)
- **Completeness**: All required elements present ✓
- **Tone Match**: 96% alignment with requested tone
- **Issues**: None detected
- Detailed breakdown on click

### Iterative Refinement

**REQ-CHAT-013: Conversation Flow**

Natural back-and-forth refinement:

Example conversation:
```
User: Write an organizational capacity section for a DoED grant
      focused on early childhood literacy.

AI:   [Generates 800-word section with citations]
      Confidence: 0.89 | Sources: 5 documents

User: Make it more concise, focus on our literacy program
      experience specifically.

AI:   [Generates refined 500-word version focusing on literacy]
      Confidence: 0.91 | Sources: 3 documents

User: Add specific metrics on student outcomes from our 2023
      annual report.

AI:   [Incorporates metrics from specified source]
      Confidence: 0.93 | Sources: 4 documents

User: Perfect, save this as final draft.

System: ✓ Saved to Past Outputs Dashboard
        [Download] [Continue Editing]
```

**REQ-CHAT-014: Refinement Commands**

Support natural language refinement:
- "Make it longer/shorter"
- "Add more data/statistics"
- "Make it more formal/casual"
- "Expand section on [topic]"
- "Remove references to [topic]"
- "Use different sources"
- "Focus on [year/program]"
- "Rewrite in 3rd person"

AI understands intent and modifies accordingly.

**REQ-CHAT-015: Version Tracking in Conversation**

Within single conversation:
- Track iterations of same section/artifact
- Show version history:
  ```
  Version 1 (initial): 800 words, 5 sources
  Version 2 (refined): 500 words, 3 sources
  Version 3 (final):   550 words, 4 sources ← Current
  ```
- Allow reverting to previous version
- Compare versions side-by-side
- Save any version as output

### Artifact Creation & Display

**REQ-CHAT-016: Artifact Detection**

System creates artifacts for:
- Responses > 500 words
- Explicitly requested "write [section/document]"
- Formatted documents (proposals, letters, reports)
- Multi-section outputs
- User says "create artifact" or "save as draft"

**REQ-CHAT-017: Artifact Presentation**

When artifact created:
- Display in dedicated artifact panel (separate from chat)
- Styled differently from chat messages
- Artifact header shows:
  - Title: "Organizational Capacity Section"
  - Type: Grant Proposal - Federal RFP
  - Word count: 847 words
  - Generated: Oct 21, 2024, 2:34 PM
  - Confidence: 0.89
- Formatted content with:
  - Preserved paragraphs
  - Bold/italic/headers
  - Numbered/bulleted lists
  - Inline citations [1], [2]
- Action buttons:
  - Download (.txt, .docx, .pdf)
  - Copy entire artifact
  - Edit inline
  - Create new version
  - Save to Past Outputs

**REQ-CHAT-018: Artifact Editing**

User can edit artifacts inline:
- Click "Edit" button
- Content becomes editable rich text area
- User makes changes
- Options:
  - Save changes (updates artifact)
  - Ask AI to revise (continues conversation)
  - Revert changes
  - Save as new version
- Edits tracked in version history

### Special Features

**REQ-CHAT-019: Quick Actions**

Floating action buttons during conversation:
- **Save Draft**: Save current artifact to Past Outputs
- **Download**: Quick export current artifact
- **New Version**: Start fresh iteration while keeping history
- **Change Style**: Switch writing style mid-conversation
- **Add Filters**: Adjust document retrieval filters
- **Reset**: Start completely new conversation

**REQ-CHAT-020: Suggested Follow-ups**

After each AI response, show suggested next steps:
- Based on context and response
- Examples:
  - "Add specific metrics"
  - "Expand the timeline section"
  - "Make it more concise"
  - "Generate budget narrative next"
  - "Create matching program description"
- Clicking suggestion sends that as next message

**REQ-CHAT-021: Templates & Quick Starts**

Pre-configured conversation starters:
- "Federal Grant - Full Proposal"
  - Walks through all sections sequentially
  - Prompts for each required section
  - Maintains consistency across sections
- "Foundation Proposal - Program Description"
  - Focused on single section
  - Optimized prompts and style
- "Donor Letter - Impact Update"
  - Casual tone, story-focused
  - Pulls recent impact data
- Custom templates created by Admins

---

## 8. Settings & Configuration

### User-Accessible Settings

**REQ-SET-001: Personal Preferences**

Each user can configure:
- Default writing style (pre-selected in new conversations)
- Default audience type
- Default section type
- Default tone level
- Citation style preference (numbered, footnote, APA)
- Auto-save interval (1-10 minutes)
- UI theme (light/dark) - future
- Notification preferences - future

**REQ-SET-002: Writing Style Management**

Admin/Editor access to:
- View all writing styles
- Create new styles (full workflow)
- Edit existing styles
- Deactivate/reactivate styles
- Delete styles
- Export/import styles
- Test styles (preview output)

**REQ-SET-003: Prompt Management**

Admin/Editor access to:
- View all system prompts
- Edit prompt templates:
  - Brand voice base prompt
  - Audience-specific prompts
  - Section-specific prompts
  - Custom prompts
- Create new prompt templates
- Version prompt templates (track changes)
- Test prompts (preview how they affect output)
- Export/import prompts

**REQ-SET-004: System Configuration (Admin Only)**

Administrator can configure:
- Claude model selection (Sonnet/Opus)
- Model temperature (0.0-1.0)
- Max tokens per response
- Embedding model configuration
- RAG parameters:
  - Default retrieval count
  - Similarity threshold
  - Recency weight
  - Chunking parameters
- API keys (Anthropic, OpenAI, Voyage)
- Rate limits and timeouts
- User management:
  - Add users
  - Change roles
  - Deactivate users
  - Reset passwords

**REQ-SET-005: Organization Settings**

Configurable organization info:
- Organization name
- Logo upload
- Primary programs list (used for metadata)
- Document types in use
- Funder relationships (for tagging)
- Fiscal year definition

---

## 9. Frontend Business Logic

### Writing Style Analysis Logic

**REQ-LOGIC-001: Sample Processing**

When user submits writing samples:

1. **Validation**:
   - Minimum 3 samples required
   - Each sample minimum 200 words
   - Total combined 1000-10000 words recommended
   - Warn if samples too short/long
   - Warn if samples very dissimilar (might confuse AI)

2. **Sample Preparation**:
   - Preserve formatting (bold, italic, lists)
   - Clean up extra whitespace
   - Extract text content
   - Combine samples with delimiters

3. **AI Analysis Prompt**:
   ```
   You are a writing style analyst. Analyze the following writing
   samples and create a detailed style guide that captures:

   1. Vocabulary: Word choices, complexity, technical terms, jargon
   2. Sentence Structure: Length, variety, active vs passive voice
   3. Thought Composition: How ideas are presented and developed
   4. Paragraph Structure: Length, organization, topic sentences
   5. Transitions: How ideas flow and connect
   6. Tone: Formality, warmth, confidence, directness
   7. Perspective: Person (1st, 3rd), organizational voice
   8. Evidence Integration: How data and facts are incorporated

   Writing Samples:
   [samples]

   Generate a comprehensive style prompt (1500-2000 words) that
   instructs an AI to write in this style. Include specific examples
   from the samples. Organize as:
   - Style Overview (summary)
   - Detailed Guidelines (by category above)
   - Examples (extracted from samples)
   - Do's and Don'ts
   ```

4. **Response Processing**:
   - Parse AI-generated style prompt
   - Format for display (markdown)
   - Validate completeness (all categories addressed)
   - Calculate confidence (is analysis coherent?)

5. **User Review Interface**:
   - Display draft prompt in editable rich text
   - Show original samples alongside for reference
   - Highlight key style elements
   - Allow inline editing
   - Provide refinement suggestions

### Conversation Context Management

**REQ-LOGIC-002: Context Persistence**

Session state management in Streamlit:

```python
# Conversation state structure
st.session_state.conversation = {
    'id': 'uuid-1234',
    'created_at': datetime,
    'messages': [
        {'role': 'user', 'content': '...', 'timestamp': datetime},
        {'role': 'assistant', 'content': '...', 'sources': [...], 'timestamp': datetime}
    ],
    'context': {
        'style_id': 'uuid-style',
        'audience': 'Federal RFP',
        'section': 'Organizational Capacity',
        'tone': 0.9,
        'filters': {...}
    },
    'artifacts': [
        {'version': 1, 'content': '...', 'word_count': 500, 'timestamp': datetime},
        {'version': 2, 'content': '...', 'word_count': 847, 'timestamp': datetime}
    ]
}
```

Context preserved:
- Across page refreshes (using session state)
- Between messages (conversation continuity)
- When switching conversations (load from database)
- On app restart (reload from database)

**REQ-LOGIC-003: Context Updates**

When conversation context changes:
- User edits style/audience/section/tone
- System detects context change
- Options:
  1. Apply to current conversation (update context)
  2. Start new conversation with new context
  3. Create branch (fork conversation with new context)
- Warn if context change is significant
- Update prompt composition for next query

### Quality Validation Logic

**REQ-LOGIC-004: Real-Time Quality Checks**

After each AI response:

1. **Confidence Calculation**:
   - Average source relevance: 40%
   - Number of sources (more = higher, up to 5): 20%
   - Source agreement (consistency): 20%
   - Query-response alignment: 20%
   - Normalize to 0.0-1.0
   - Color code: Green (>0.8), Yellow (0.6-0.8), Red (<0.6)

2. **Citation Validation**:
   - Extract all [N] markers from response
   - Verify N ≤ number of sources
   - Check if citations actually used in text
   - Identify uncited sources
   - Flag invalid citations

3. **Completeness Check**:
   - Based on section type, check for required elements
   - Organizational Capacity: staff, governance, history, financial
   - Program Description: goals, activities, timeline, participants
   - Impact: metrics, outcomes, evidence
   - Budget: costs, justification, sustainability
   - Flag missing elements

4. **Tone Validation**:
   - Analyze response for formality markers
   - Compare to requested tone
   - Flag significant mismatches
   - Suggest regeneration if off

5. **Issue Display**:
   - Show quality metrics in sidebar
   - Display warnings inline with response
   - Provide actionable suggestions
   - Allow user to proceed or regenerate

### Output Success Tracking

**REQ-LOGIC-005: Grant/Proposal Success Workflow**

For marking grant or proposal outcomes:

1. **Initial State**: All outputs start as "Draft"

2. **Submission Tracking**:
   - User marks output as "Submitted"
   - Prompt for:
     - Funder name
     - Submission date
     - Requested amount
     - Program focus
   - Status changes to "Pending"

3. **Outcome Recording**:
   - User updates status to "Awarded" or "Not Awarded"
   - If Awarded:
     - Prompt for award amount
     - Award date
     - Contract/grant period
     - Notes on what worked
   - If Not Awarded:
     - Prompt for feedback received
     - Notes on why (if known)
     - Lessons learned

4. **Data Analysis** (Future):
   - Track success rate by:
     - Writing style used
     - Funder type
     - Program area
     - Section quality scores
   - Identify patterns in successful content
   - Use for fine-tuning recommendations
   - ROI calculation (awarded $ vs. system cost)

### Document Retrieval Strategy

**REQ-LOGIC-006: Intelligent Retrieval**

When user sends query:

1. **Query Analysis**:
   - Extract key concepts and entities
   - Identify implicit requirements
   - Classify query intent (write new, revise, extract info)
   - Determine if RAG needed or conversational response

2. **Filter Application**:
   - Apply user-specified filters:
     - Document types
     - Date ranges
     - Programs
     - Outcomes
   - Apply context-based filters:
     - If writing grant proposal, prefer successful grants
     - If specific funder mentioned, prefer that funder's docs
     - If recent data needed, boost recency weight

3. **Hybrid Retrieval**:
   - Vector search for semantic similarity
   - Keyword search for exact matches
   - Combine with weighted scoring (70% vector, 30% keyword)
   - Apply recency weighting
   - Diversify results (max 3 chunks per document)

4. **Source Validation**:
   - Check retrieved sources are relevant
   - Ensure sufficient coverage of query
   - Warn if low relevance scores
   - Suggest broadening filters if insufficient results

5. **Context Composition**:
   - Format sources for prompt
   - Calculate total token count
   - Prioritize if exceeding context limit
   - Include source metadata for citations

---

## 10. Error Handling & User Guidance

### Error States

**REQ-ERROR-001: Empty Retrieval**

If no documents match query/filters:
- Clear message: "No documents found matching your criteria"
- Suggestions:
  - "Try broadening your date range"
  - "Remove some document type filters"
  - "Search all documents"
- Option: "Proceed without retrieval (general knowledge only)"
- Show current active filters for easy editing

**REQ-ERROR-002: Low Confidence Response**

If confidence score < 0.5:
- Prominent warning banner: "⚠️ Low confidence in this response"
- Explanation: "Retrieved sources may not fully support this content"
- Suggestions:
  - "Try rephrasing your query"
  - "Upload more relevant documents"
  - "Review and edit response carefully"
- Options:
  - Regenerate with different parameters
  - Proceed anyway (user accepts risk)
  - Abandon and start over

**REQ-ERROR-003: API Failures**

If Claude API call fails:
- User-friendly message: "Unable to generate response"
- Technical details (for admins): Error code and message
- Automatic retry (up to 3 times)
- If all retries fail:
  - "Service temporarily unavailable"
  - "Your conversation has been saved"
  - "Try again in a few minutes"
- Preserve user's message for retry

**REQ-ERROR-004: Processing Failures**

If document upload processing fails:
- Specific error messages:
  - "Unable to extract text from PDF (may be scanned image)"
  - "File format not supported"
  - "File too large (max 50MB)"
  - "File appears to be corrupted"
- Suggestions for resolution
- Option to retry with different file
- Support contact info for persistent issues

### User Guidance

**REQ-GUIDE-001: Contextual Help**

Throughout interface:
- Tooltip hints on hover (question mark icons)
- Inline examples in form fields
- "Learn more" links to documentation
- First-time user walkthroughs
- Video tutorials (future)

**REQ-GUIDE-002: Writing Tips**

In chat interface:
- Suggest query improvements:
  - "Try being more specific about the audience"
  - "Include the funding amount or program scope"
  - "Specify which section you're writing"
- Best practices sidebar:
  - "Most effective queries are 20-100 words"
  - "Mention specific programs or timeframes"
  - "Reference successful past proposals"

**REQ-GUIDE-003: Quality Improvement**

When quality issues detected:
- Actionable feedback:
  - "Low confidence detected. Try adding 'data' or 'metrics' to your query"
  - "Response missing required elements. Regenerate with 'include governance structure'"
  - "Tone too casual for federal RFP. Adjust tone slider to more formal"
- Learning resources:
  - Link to example high-quality outputs
  - Link to writing style guidelines
  - Link to successful grant examples in library

---

## 11. Performance & UX Requirements

### Response Time Expectations

**REQ-PERF-001: Loading States**

All async operations show loading indicators:
- Document upload: Progress bar with percentage
- AI analysis: Spinner with estimated time ("~30 seconds")
- Retrieval: "Searching document library..."
- Generation: "Claude is writing..." with streaming text
- Save operations: Quick flash confirmation

**REQ-PERF-002: Streaming Responses**

For AI generation:
- First token within 1 second (perceived latency)
- Stream tokens as they arrive (typewriter effect)
- Show partial response immediately
- Allow canceling mid-generation
- Show token count and estimated time remaining

**REQ-PERF-003: Perceived Performance**

Optimizations:
- Optimistic UI updates (assume success, rollback on error)
- Cached results for repeated queries
- Prefetch conversation history on app load
- Debounced search inputs (wait for typing to stop)
- Pagination for large lists (don't load all 500 docs at once)

### Responsive Design

**REQ-RESP-001: Desktop Optimization**

Primary target: Desktop/laptop screens (1920x1080, 1440x900)
- Three-column layout: Sidebar | Main | Context Panel
- Comfortable reading width for generated text
- Side-by-side comparisons when needed
- Keyboard shortcuts for power users

**REQ-RESP-002: Tablet Support** (Future)

Basic support for tablets (iPad, Surface):
- Collapsible sidebars
- Touch-friendly buttons (larger tap targets)
- Simplified navigation
- Portrait and landscape modes

**REQ-RESP-003: Mobile** (Not MVP)

Mobile phone support not required for MVP:
- Primary users are staff at desks
- Complex workflows not suitable for mobile
- Future: mobile-friendly read-only views

---

## 12. Accessibility

**REQ-ACCESS-001: Keyboard Navigation**

Support keyboard-only operation:
- Tab through interactive elements
- Enter/Space to activate buttons
- Escape to close modals/panels
- Keyboard shortcuts for common actions
- Focus indicators clearly visible

**REQ-ACCESS-002: Screen Reader Support**

Semantic HTML and ARIA labels:
- Proper heading hierarchy
- Alt text for images/icons
- Labels for form inputs
- Status announcements for dynamic updates
- Skip navigation links

**REQ-ACCESS-003: Color & Contrast**

Accessible color choices:
- High contrast text (4.5:1 minimum)
- Don't rely on color alone for meaning
- Color-blind friendly palettes
- Adjustable text size

---

## 13. Future Enhancements

### Post-MVP Features

**REQ-FUTURE-001: Collaborative Features**
- Multiple users editing same output
- Comments and suggestions
- Version control with merge
- Team approval workflows

**REQ-FUTURE-002: Advanced Analytics**
- Success rate dashboards
- Content quality trends
- Most effective sources
- User productivity metrics
- ROI tracking (grant awards)

**REQ-FUTURE-003: Fine-Tuning**
- Use successful grant outputs to fine-tune models
- Organization-specific model adaptation
- Continuous learning from user edits
- A/B testing different prompts

**REQ-FUTURE-004: Integration**
- Export to grant management systems (Fluxx, etc.)
- Calendar integration for deadlines
- Email integration for drafts
- API for external tools

**REQ-FUTURE-005: Multi-Modal**
- Image analysis (charts, infographics from reports)
- Table extraction and analysis
- Video transcription (for impact stories)
- Audio input (dictation)

---

## Summary

This comprehensive frontend requirements document specifies the **Nuxt 4 (Vue 3 + TypeScript)** implementation for Org Archivist:

✅ **User Roles**: Three distinct roles (Administrator, Editor, Writer) with clear permissions
✅ **JWT Authentication**: Full authentication flow with access/refresh tokens and session management
✅ **Writing Styles**: Complete workflow for creating AI-powered writing style guides from samples
✅ **Document Library**: Full-featured document management with role-based access
✅ **Programs Management**: Dynamic CRUD operations for organizational program categories
✅ **Past Outputs**: Comprehensive output tracking with success indicators for grants
✅ **AI Writing Assistant**: Chat-style interface with SSE streaming, iterative refinement, and conversation history
✅ **SSE Streaming**: Real-time AI response streaming with typewriter effect using ReadableStream API
✅ **Nuxt 4 Components**: Modern Vue 3 components using Nuxt UI library built on Tailwind CSS
✅ **TypeScript Throughout**: Full type safety for all API interactions and component props
✅ **Business Logic**: Detailed logic for style analysis, context management, quality validation, and retrieval
✅ **Error Handling**: Comprehensive error states and user guidance with toast notifications
✅ **Performance**: Response time expectations, SSE streaming, and UX optimizations
✅ **Security**: Role-based access control, protected routes, and admin-only endpoints

**Key Migration Changes:**
- ✅ Replaced Streamlit with Nuxt 4 (Vue 3 + TypeScript)
- ✅ Added JWT-based authentication with refresh tokens
- ✅ Implemented SSE streaming for real-time AI responses
- ✅ Added dynamic Programs API for organizational categories
- ✅ Enhanced security with admin-only metrics endpoint
- ✅ Full type safety with TypeScript
- ✅ Modern UI with Nuxt UI components

The document provides sufficient detail for Nuxt 4 frontend development with clear requirements for each feature, Vue 3 component structure, TypeScript types, and a complete understanding of the user experience.
