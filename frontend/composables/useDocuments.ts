/**
 * Documents Composable
 *
 * Provides document management operations for the Org Archivist application.
 *
 * Features:
 * - Fetch documents with filtering and pagination
 * - Upload documents with FormData
 * - Delete documents
 * - Get document statistics
 * - State management for documents list
 * - Loading and error handling
 *
 * @example
 * ```ts
 * const {
 *   documents,
 *   pagination,
 *   loading,
 *   error,
 *   getDocuments,
 *   uploadDocument,
 *   deleteDocument,
 *   getStats
 * } = useDocuments()
 *
 * // Fetch documents with filters
 * await getDocuments({
 *   doc_types: ['Grant Proposal'],
 *   years: [2024],
 *   page: 1,
 *   per_page: 25
 * })
 *
 * // Upload a document
 * const formData = new FormData()
 * formData.append('file', file)
 * formData.append('metadata', JSON.stringify(metadata))
 * await uploadDocument(formData)
 *
 * // Delete a document
 * await deleteDocument('doc-id-123')
 *
 * // Get statistics
 * const stats = await getStats()
 * ```
 */

import type {
  DocumentResponse,
  DocumentFilters,
  ListQueryParams,
  PaginatedResponse,
  PaginationMetadata,
  ApiError,
  SuccessResponse,
} from '~/types/api'

/**
 * Document statistics response
 */
export interface DocumentStats {
  total_documents: number
  total_chunks: number
  by_type: Record<string, number>
  by_outcome: Record<string, number>
  by_year: Record<string, number>
  storage_bytes: number
  recent_uploads: DocumentResponse[]
}

/**
 * Get documents query parameters
 */
export interface GetDocumentsParams {
  page?: number
  per_page?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  search?: string
  filters?: DocumentFilters
}

/**
 * Documents composable state and operations
 */
export const useDocuments = () => {
  // ============================================================================
  // State Management
  // ============================================================================

  /**
   * List of documents (reactive state)
   */
  const documents = useState<DocumentResponse[]>('documents', () => [])

  /**
   * Pagination metadata
   */
  const pagination = useState<PaginationMetadata | null>('documents_pagination', () => null)

  /**
   * Loading state for async operations
   */
  const loading = ref(false)

  /**
   * Error state for operations
   */
  const error = ref<ApiError | null>(null)

  /**
   * Upload progress (0-100)
   */
  const uploadProgress = ref(0)

  /**
   * Currently uploading flag
   */
  const isUploading = ref(false)

  // ============================================================================
  // API Operations
  // ============================================================================

  const { apiFetch } = useApi()

  /**
   * Fetch documents with optional filters and pagination
   *
   * @param params - Query parameters including filters, pagination, sorting
   * @returns Promise resolving to paginated document response
   *
   * @example
   * ```ts
   * const { getDocuments } = useDocuments()
   *
   * // Get all documents
   * await getDocuments()
   *
   * // Get with filters
   * await getDocuments({
   *   filters: {
   *     doc_types: ['Grant Proposal', 'Annual Report'],
   *     years: [2023, 2024],
   *     programs: ['Education', 'Youth Development'],
   *     outcomes: ['Funded']
   *   },
   *   page: 1,
   *   per_page: 25,
   *   sort_by: 'upload_date',
   *   sort_order: 'desc'
   * })
   *
   * // Search documents
   * await getDocuments({
   *   search: 'grant proposal',
   *   page: 1,
   *   per_page: 10
   * })
   * ```
   */
  const getDocuments = async (params?: GetDocumentsParams): Promise<PaginatedResponse<DocumentResponse> | null> => {
    loading.value = true
    error.value = null

    try {
      // Build query string from parameters
      const queryParams = new URLSearchParams()

      if (params?.page) queryParams.append('page', params.page.toString())
      if (params?.per_page) queryParams.append('per_page', params.per_page.toString())
      if (params?.sort_by) queryParams.append('sort_by', params.sort_by)
      if (params?.sort_order) queryParams.append('sort_order', params.sort_order)
      if (params?.search) queryParams.append('search', params.search)

      // Add filters as JSON string if present
      if (params?.filters) {
        queryParams.append('filters', JSON.stringify(params.filters))
      }

      const queryString = queryParams.toString()
      const url = `/api/documents${queryString ? `?${queryString}` : ''}`

      const response = await apiFetch<PaginatedResponse<DocumentResponse>>(url, {
        method: 'GET',
      })

      // Update state with response
      documents.value = response.items
      pagination.value = response.pagination

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to fetch documents',
        detail: err.data?.detail || err.message,
      }
      console.error('Error fetching documents:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Upload a document with FormData
   *
   * FormData should include:
   * - file: File object
   * - metadata: JSON string with DocumentMetadata
   * - sensitivity_check: Optional JSON string with DocumentSensitivityCheck
   *
   * @param formData - FormData containing file and metadata
   * @returns Promise resolving to uploaded document response
   *
   * @example
   * ```ts
   * const { uploadDocument } = useDocuments()
   *
   * const formData = new FormData()
   * formData.append('file', file)
   * formData.append('metadata', JSON.stringify({
   *   doc_type: 'Grant Proposal',
   *   year: 2024,
   *   programs: ['Education'],
   *   tags: ['federal', 'doe'],
   *   outcome: 'Pending',
   *   notes: 'Q2 2024 submission'
   * }))
   * formData.append('sensitivity_check', JSON.stringify({
   *   is_sensitive: false,
   *   requires_review: false
   * }))
   *
   * const result = await uploadDocument(formData)
   * if (result) {
   *   console.log('Document uploaded:', result.document_id)
   * }
   * ```
   */
  const uploadDocument = async (formData: FormData): Promise<DocumentResponse | null> => {
    isUploading.value = true
    uploadProgress.value = 0
    error.value = null

    try {
      // Note: For actual upload progress tracking, we would need to use XMLHttpRequest
      // or a library like axios. $fetch doesn't provide upload progress callbacks.
      // For now, we'll just track completion.

      const response = await apiFetch<DocumentResponse>('/api/documents/upload', {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header - let browser set it with boundary for FormData
        headers: {},
      })

      uploadProgress.value = 100

      // Refresh documents list after successful upload
      await getDocuments({
        page: 1,
        per_page: pagination.value?.per_page || 25,
      })

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to upload document',
        detail: err.data?.detail || err.message,
      }
      console.error('Error uploading document:', err)
      return null
    } finally {
      isUploading.value = false
      uploadProgress.value = 0
    }
  }

  /**
   * Delete a document by ID
   *
   * @param documentId - UUID of document to delete
   * @returns Promise resolving to success status
   *
   * @example
   * ```ts
   * const { deleteDocument } = useDocuments()
   *
   * const success = await deleteDocument('550e8400-e29b-41d4-a716-446655440000')
   * if (success) {
   *   console.log('Document deleted successfully')
   * }
   * ```
   */
  const deleteDocument = async (documentId: string): Promise<boolean> => {
    loading.value = true
    error.value = null

    try {
      await apiFetch<SuccessResponse>(`/api/documents/${documentId}`, {
        method: 'DELETE',
      })

      // Remove document from local state
      documents.value = documents.value.filter((doc) => doc.document_id !== documentId)

      // Update pagination count if available
      if (pagination.value) {
        pagination.value.total -= 1
      }

      return true
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to delete document',
        detail: err.data?.detail || err.message,
      }
      console.error('Error deleting document:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Get document statistics
   *
   * Returns aggregate statistics about the document library including:
   * - Total documents and chunks
   * - Distribution by type, outcome, year
   * - Storage usage
   * - Recent uploads
   *
   * @returns Promise resolving to document statistics
   *
   * @example
   * ```ts
   * const { getStats } = useDocuments()
   *
   * const stats = await getStats()
   * if (stats) {
   *   console.log(`Total documents: ${stats.total_documents}`)
   *   console.log(`Total chunks: ${stats.total_chunks}`)
   *   console.log('By type:', stats.by_type)
   *   console.log('By outcome:', stats.by_outcome)
   * }
   * ```
   */
  const getStats = async (): Promise<DocumentStats | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await apiFetch<DocumentStats>('/api/documents/stats', {
        method: 'GET',
      })

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to fetch document statistics',
        detail: err.data?.detail || err.message,
      }
      console.error('Error fetching document stats:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Get a single document by ID
   *
   * @param documentId - UUID of document to fetch
   * @returns Promise resolving to document response
   *
   * @example
   * ```ts
   * const { getDocument } = useDocuments()
   *
   * const document = await getDocument('550e8400-e29b-41d4-a716-446655440000')
   * if (document) {
   *   console.log('Document:', document.filename)
   * }
   * ```
   */
  const getDocument = async (documentId: string): Promise<DocumentResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await apiFetch<DocumentResponse>(`/api/documents/${documentId}`, {
        method: 'GET',
      })

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to fetch document',
        detail: err.data?.detail || err.message,
      }
      console.error('Error fetching document:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Upload multiple documents with metadata (batch upload)
   *
   * @param files - Array of File objects to upload
   * @param metadata - Map of filename to DocumentMetadata
   * @returns Promise resolving to upload results
   *
   * @example
   * ```ts
   * const { uploadDocuments } = useDocuments()
   *
   * const files = [file1, file2, file3]
   * const metadata = {
   *   'file1.pdf': { doc_type: 'Grant Proposal', year: 2024, programs: ['Education'], outcome: 'Pending' },
   *   'file2.pdf': { doc_type: 'Annual Report', year: 2023, programs: ['Health'], outcome: 'N/A' },
   * }
   *
   * const result = await uploadDocuments(files, metadata)
   * console.log('Successful:', result.successful)
   * console.log('Failed:', result.failed)
   * console.log('Errors:', result.errors)
   * ```
   */
  const uploadDocuments = async (
    files: File[],
    metadata: Record<string, any>
  ): Promise<{
    successful: string[]
    failed: string[]
    errors?: Record<string, string>
    documentIds?: Record<string, string>
  }> => {
    isUploading.value = true
    error.value = null

    const result = {
      successful: [] as string[],
      failed: [] as string[],
      errors: {} as Record<string, string>,
      documentIds: {} as Record<string, string>,
    }

    try {
      // Upload each file individually
      for (const file of files) {
        try {
          const fileMetadata = metadata[file.name]

          if (!fileMetadata) {
            result.failed.push(file.name)
            result.errors[file.name] = 'Missing metadata for file'
            continue
          }

          // Create FormData for this file
          const formData = new FormData()
          formData.append('file', file)
          formData.append('metadata', JSON.stringify(fileMetadata))

          // Upload the document
          const response = await uploadDocument(formData)

          if (response) {
            result.successful.push(file.name)
            result.documentIds[file.name] = response.document_id
          } else {
            result.failed.push(file.name)
            const err = error.value
            const errorMessage = err ? (err as ApiError).message : 'Upload failed'
            result.errors[file.name] = errorMessage
          }
        } catch (err) {
          result.failed.push(file.name)
          const errorMessage = err instanceof Error ? err.message : 'Upload failed'
          result.errors[file.name] = errorMessage
        }
      }

      return result
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Batch upload failed',
        detail: err.data?.detail || err.message,
      }
      throw err
    } finally {
      isUploading.value = false
    }
  }

  /**
   * Clear error state
   */
  const clearError = () => {
    error.value = null
  }

  /**
   * Reset all state to initial values
   */
  const reset = () => {
    documents.value = []
    pagination.value = null
    loading.value = false
    error.value = null
    uploadProgress.value = 0
    isUploading.value = false
  }

  // ============================================================================
  // Computed Properties
  // ============================================================================

  /**
   * Check if there are any documents
   */
  const hasDocuments = computed(() => documents.value.length > 0)

  /**
   * Total document count from pagination metadata
   */
  const totalDocuments = computed(() => pagination.value?.total || 0)

  /**
   * Check if there are more pages available
   */
  const hasNextPage = computed(() => pagination.value?.has_next || false)

  /**
   * Check if there is a previous page
   */
  const hasPreviousPage = computed(() => pagination.value?.has_previous || false)

  /**
   * Current page number
   */
  const currentPage = computed(() => pagination.value?.page || 1)

  /**
   * Total number of pages
   */
  const totalPages = computed(() => pagination.value?.total_pages || 1)

  // ============================================================================
  // Return Public API
  // ============================================================================

  return {
    // State
    documents,
    pagination,
    loading,
    error,
    uploadProgress,
    isUploading,

    // Computed
    hasDocuments,
    totalDocuments,
    hasNextPage,
    hasPreviousPage,
    currentPage,
    totalPages,

    // Operations
    getDocuments,
    uploadDocument,
    uploadDocuments,
    deleteDocument,
    getStats,
    getDocument,
    clearError,
    reset,
  }
}
