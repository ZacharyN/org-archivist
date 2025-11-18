/**
 * API Type Definitions
 *
 * TypeScript interfaces matching backend Pydantic models
 * for type-safe API communication in the Nuxt 4 frontend.
 */

// ============================================================================
// Core Response Types
// ============================================================================

/**
 * Health check response from /api/health endpoint
 */
export interface HealthCheckResponse {
  status: string
  service: string
  version: string
  checks: Record<string, any>
}

/**
 * Standard error response format
 */
export interface ErrorResponse {
  error: string
  detail: string
  timestamp: string
}

/**
 * Generic success response wrapper
 */
export interface SuccessResponse<T = any> {
  success: boolean
  message: string
  data?: T
}

/**
 * Pagination metadata for list responses
 */
export interface PaginationMetadata {
  total: number
  page: number
  per_page: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

/**
 * Generic paginated response wrapper
 */
export interface PaginatedResponse<T> {
  items: T[]
  pagination: PaginationMetadata
}

// ============================================================================
// Authentication Types
// ============================================================================

/**
 * User role types
 */
export type UserRole = 'admin' | 'editor' | 'writer'

/**
 * User profile information
 */
export interface UserResponse {
  user_id: string
  email: string
  full_name: string | null
  role: UserRole
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at: string
}

/**
 * Registration request payload
 */
export interface RegisterRequest {
  email: string
  password: string
  full_name?: string
  role?: UserRole
}

/**
 * Login request payload
 */
export interface LoginRequest {
  email: string
  password: string
}

/**
 * Login response with tokens and user info
 */
export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_at: string
  user: UserResponse
}

/**
 * Session validation response
 */
export interface SessionResponse {
  valid: boolean
  user?: UserResponse
  message?: string
}

/**
 * Logout response
 */
export interface LogoutResponse {
  success: boolean
  message: string
}

/**
 * Refresh token request
 */
export interface RefreshRequest {
  refresh_token: string
}

// ============================================================================
// Document Types
// ============================================================================

/**
 * Document type literals
 */
export type DocumentType =
  | 'Grant Proposal'
  | 'Annual Report'
  | 'Program Description'
  | 'Impact Report'
  | 'Strategic Plan'
  | 'Other'

/**
 * Document outcome status
 */
export type DocumentOutcome =
  | 'N/A'
  | 'Funded'
  | 'Not Funded'
  | 'Pending'
  | 'Final Report'

/**
 * Document sensitivity level
 */
export type SensitivityLevel = 'low' | 'medium' | 'high'

/**
 * Document metadata
 */
export interface DocumentMetadata {
  doc_type: DocumentType
  year: number
  programs: string[]
  tags: string[]
  outcome: DocumentOutcome
  notes?: string
}

/**
 * Document sensitivity check information
 */
export interface DocumentSensitivityCheck {
  is_sensitive: boolean
  sensitivity_level?: SensitivityLevel
  sensitivity_notes?: string
  requires_review: boolean
}

/**
 * Document upload request
 */
export interface DocumentUploadRequest {
  metadata: DocumentMetadata
  sensitivity_check?: DocumentSensitivityCheck
}

/**
 * Document response from API
 */
export interface DocumentResponse {
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

/**
 * Document filters for queries
 */
export interface DocumentFilters {
  doc_types?: DocumentType[]
  years?: number[]
  programs?: string[]
  tags?: string[]
  outcomes?: DocumentOutcome[]
  sensitivity_levels?: SensitivityLevel[]
}

// ============================================================================
// Query & Generation Types
// ============================================================================

/**
 * Content generation query request
 */
export interface QueryRequest {
  query: string
  audience: string
  section: string
  tone?: string
  max_sources?: number
  recency_weight?: number
  include_citations?: boolean
  filters?: DocumentFilters
  conversation_id?: string
  context?: ConversationContext
}

/**
 * Query response with generated content
 */
export interface QueryResponse {
  content: string
  sources: Source[]
  metadata: GenerationMetadata
  conversation_id?: string
}

/**
 * Source document in query results (used in QueryResponse)
 */
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

/**
 * Document reference in query results (alternative format)
 */
export interface DocumentReference {
  document_id: string
  filename: string
  relevance_score: number
  excerpt: string
  page_number?: number
  metadata: DocumentMetadata
}

/**
 * Generation metadata
 */
export interface GenerationMetadata {
  total_sources: number
  tokens_used: number
  model: string
  temperature: number
  retrieval_time_ms: number
  generation_time_ms: number
}

// ============================================================================
// Conversation & Chat Types
// ============================================================================

/**
 * Session metadata for conversation tracking
 */
export interface SessionMetadata {
  started_at: string
  last_active: string
}

/**
 * Artifact version (generated content within conversation)
 */
export interface ArtifactVersion {
  artifact_id: string
  version: number
  created_at: string
  content: string
  word_count: number
  metadata: Record<string, any>
}

/**
 * Conversation context for multi-turn interactions
 */
export interface ConversationContext {
  writing_style_id?: string
  audience?: string
  section?: string
  tone?: string
  filters?: DocumentFilters
  artifacts?: ArtifactVersion[]
  last_query?: string
  session_metadata?: SessionMetadata
}

/**
 * Conversation context response
 */
export interface ConversationContextResponse {
  conversation_id: string
  context: ConversationContext
  updated_at: string
}

/**
 * Chat message
 */
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  metadata?: Record<string, any>
}

/**
 * Chat request
 */
export interface ChatRequest {
  message: string
  conversation_id?: string
  context?: DocumentFilters
}

/**
 * Chat response
 */
export interface ChatResponse {
  message: string
  conversation_id: string
  sources?: DocumentReference[]
  metadata?: GenerationMetadata
}

/**
 * Conversation (full chat session)
 */
export interface Conversation {
  conversation_id: string
  user_id: string
  name?: string
  messages: ChatMessage[]
  context?: ConversationContext
  created_at: string
  updated_at: string
}

// ============================================================================
// Writing Style Types
// ============================================================================

/**
 * Writing style type literals
 */
export type WritingStyleType = 'grant' | 'proposal' | 'report' | 'general'

/**
 * Writing style profile
 */
export interface WritingStyle {
  style_id: string
  name: string
  type: WritingStyleType
  description?: string
  prompt_content: string
  samples?: string[]
  analysis_metadata?: Record<string, any>
  sample_count: number
  active: boolean
  created_at: string
  updated_at: string
  created_by?: string
}

/**
 * Writing style analysis results (for analysis_metadata field)
 */
export interface WritingStyleAnalysis {
  tone?: string
  formality_level?: string
  sentence_structure?: string
  vocabulary_level?: string
  key_phrases?: string[]
  writing_patterns?: Record<string, any>
}

/**
 * Create writing style request
 */
export interface WritingStyleCreateRequest {
  name: string
  type: WritingStyleType
  description?: string
  prompt_content: string
  samples?: string[]
  analysis_metadata?: Record<string, any>
}

/**
 * Update writing style request
 */
export interface WritingStyleUpdateRequest {
  name?: string
  description?: string
  prompt_content?: string
  active?: boolean
}

/**
 * Style analysis request
 */
export interface StyleAnalysisRequest {
  samples: string[]
  style_type?: WritingStyleType
  style_name?: string
}

/**
 * Style analysis response
 */
export interface StyleAnalysisResponse {
  success: boolean
  style_prompt?: string
  style_name?: string
  style_type?: string
  analysis_metadata?: Record<string, any>
  sample_stats?: Record<string, any>
  word_count?: number
  generation_time?: number
  tokens_used?: number
  model?: string
  warnings?: string[]
  errors?: string[]
}

// ============================================================================
// Output Types
// ============================================================================

/**
 * Output type literals
 */
export type OutputType =
  | 'grant_proposal'
  | 'budget_narrative'
  | 'program_description'
  | 'impact_summary'
  | 'other'

/**
 * Output status literals
 */
export type OutputStatus =
  | 'draft'
  | 'submitted'
  | 'pending'
  | 'awarded'
  | 'not_awarded'

/**
 * Saved output/generation
 */
export interface OutputResponse {
  output_id: string
  conversation_id?: string
  output_type: OutputType
  title: string
  content: string
  word_count?: number
  status: OutputStatus
  writing_style_id?: string
  funder_name?: string
  requested_amount?: number
  awarded_amount?: number
  submission_date?: string
  decision_date?: string
  success_notes?: string
  metadata?: OutputMetadata
  created_by?: string
  created_at: string
  updated_at: string
}

/**
 * Output metadata structure
 */
export interface OutputMetadata {
  program_focus?: string
  grant_type?: string
  deadline?: string
  collaborators?: string[]
  review_status?: string
  sources?: Source[]
  confidence?: number
  [key: string]: any
}

/**
 * Create output request
 */
export interface OutputCreateRequest {
  output_type: OutputType
  title: string
  content: string
  word_count?: number
  status?: OutputStatus
  writing_style_id?: string
  funder_name?: string
  requested_amount?: number
  awarded_amount?: number
  submission_date?: string
  decision_date?: string
  success_notes?: string
  metadata?: OutputMetadata
  conversation_id?: string
}

/**
 * Update output request
 */
export interface OutputUpdateRequest {
  output_type?: OutputType
  title?: string
  content?: string
  word_count?: number
  status?: OutputStatus
  writing_style_id?: string
  funder_name?: string
  requested_amount?: number
  awarded_amount?: number
  submission_date?: string
  decision_date?: string
  success_notes?: string
  metadata?: OutputMetadata
}

/**
 * Output statistics response
 */
export interface OutputStatsResponse {
  total_outputs: number
  by_type: Record<string, number>
  by_status: Record<string, number>
  success_rate: number
  total_requested: number
  total_awarded: number
  avg_requested?: number
  avg_awarded?: number
}

// ============================================================================
// Program Types
// ============================================================================

/**
 * Program information
 */
export interface ProgramResponse {
  program_id: string
  name: string
  description?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

/**
 * Create/update program request
 */
export interface ProgramRequest {
  name: string
  description?: string
  is_active?: boolean
}

// ============================================================================
// Prompt Template Types
// ============================================================================

/**
 * Prompt template
 */
export interface PromptTemplate {
  template_id: string
  name: string
  description?: string
  template_text: string
  variables: string[]
  category?: string
  is_system: boolean
  created_at: string
  updated_at: string
}

/**
 * Create/update prompt template request
 */
export interface PromptTemplateRequest {
  name: string
  description?: string
  template_text: string
  variables?: string[]
  category?: string
}

// ============================================================================
// Audit Log Types
// ============================================================================

/**
 * Audit action types
 */
export type AuditAction =
  | 'CREATE'
  | 'READ'
  | 'UPDATE'
  | 'DELETE'
  | 'LOGIN'
  | 'LOGOUT'
  | 'UPLOAD'
  | 'DOWNLOAD'
  | 'GENERATE'

/**
 * Audit log entry
 */
export interface AuditLogEntry {
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

/**
 * Audit log query filters
 */
export interface AuditLogFilters {
  user_id?: string
  actions?: AuditAction[]
  resource_types?: string[]
  start_date?: string
  end_date?: string
}

// ============================================================================
// Utility Types
// ============================================================================

/**
 * API error details
 */
export interface ApiError {
  status: number
  message: string
  detail?: string
  errors?: Record<string, string[]>
}

/**
 * File upload progress
 */
export interface UploadProgress {
  loaded: number
  total: number
  percentage: number
}

/**
 * Generic list query parameters
 */
export interface ListQueryParams {
  page?: number
  per_page?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  search?: string
}
