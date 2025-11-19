/**
 * Outputs Composable
 *
 * Provides output management operations for saved content and generations.
 *
 * Features:
 * - Fetch outputs with filtering and pagination
 * - Create, update, and delete outputs
 * - Get output statistics and analytics
 * - State management for outputs list
 * - Loading and error handling
 *
 * @example
 * ```ts
 * const {
 *   outputs,
 *   pagination,
 *   loading,
 *   error,
 *   getOutputs,
 *   getOutput,
 *   createOutput,
 *   updateOutput,
 *   deleteOutput,
 *   getStats,
 *   getAnalytics
 * } = useOutputs()
 *
 * // Fetch outputs with filters
 * await getOutputs({
 *   output_types: ['grant_proposal'],
 *   statuses: ['draft', 'submitted'],
 *   page: 1,
 *   per_page: 25
 * })
 *
 * // Create a new output
 * await createOutput({
 *   output_type: 'grant_proposal',
 *   title: 'Education Grant 2024',
 *   content: 'Our program...',
 *   status: 'draft'
 * })
 *
 * // Get statistics
 * const stats = await getStats()
 * ```
 */

import type {
  OutputResponse,
  OutputCreateRequest,
  OutputUpdateRequest,
  OutputStatsResponse,
  OutputType,
  OutputStatus,
  PaginatedResponse,
  PaginationMetadata,
  ApiError,
  SuccessResponse,
} from '~/types/api'

/**
 * Output filters for queries
 */
export interface OutputFilters {
  output_types?: OutputType[]
  statuses?: OutputStatus[]
  writing_style_ids?: string[]
  funder_names?: string[]
  date_from?: string
  date_to?: string
}

/**
 * Get outputs query parameters
 */
export interface GetOutputsParams {
  page?: number
  per_page?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  search?: string
  filters?: OutputFilters
}

/**
 * Output analytics response
 */
export interface OutputAnalyticsResponse {
  total_outputs: number
  by_type: Record<string, number>
  by_status: Record<string, number>
  by_month: Record<string, number>
  success_rate: number
  avg_word_count: number
  total_requested: number
  total_awarded: number
  award_rate?: number
  recent_outputs: OutputResponse[]
  top_funders?: Array<{ name: string; count: number; awarded: number }>
}

/**
 * Outputs composable state and operations
 */
export const useOutputs = () => {
  // ============================================================================
  // State Management
  // ============================================================================

  /**
   * List of outputs (reactive state)
   */
  const outputs = useState<OutputResponse[]>('outputs', () => [])

  /**
   * Pagination metadata
   */
  const pagination = useState<PaginationMetadata | null>('outputs_pagination', () => null)

  /**
   * Loading state for async operations
   */
  const loading = ref(false)

  /**
   * Error state for operations
   */
  const error = ref<ApiError | null>(null)

  /**
   * Currently selected output (for detail view)
   */
  const currentOutput = ref<OutputResponse | null>(null)

  // ============================================================================
  // API Operations
  // ============================================================================

  const { apiFetch } = useApi()

  /**
   * Fetch outputs with optional filters and pagination
   *
   * @param params - Query parameters including filters, pagination, sorting
   * @returns Promise resolving to paginated output response
   *
   * @example
   * ```ts
   * const { getOutputs } = useOutputs()
   *
   * // Get all outputs
   * await getOutputs()
   *
   * // Get with filters
   * await getOutputs({
   *   filters: {
   *     output_types: ['grant_proposal', 'budget_narrative'],
   *     statuses: ['submitted', 'awarded'],
   *     funder_names: ['Department of Education']
   *   },
   *   page: 1,
   *   per_page: 25,
   *   sort_by: 'created_at',
   *   sort_order: 'desc'
   * })
   *
   * // Search outputs
   * await getOutputs({
   *   search: 'education grant',
   *   page: 1,
   *   per_page: 10
   * })
   * ```
   */
  const getOutputs = async (params?: GetOutputsParams): Promise<PaginatedResponse<OutputResponse> | null> => {
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
      const url = `/api/outputs${queryString ? `?${queryString}` : ''}`

      const response = await apiFetch<PaginatedResponse<OutputResponse>>(url, {
        method: 'GET',
      })

      // Update state with response
      outputs.value = response.items
      pagination.value = response.pagination

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to fetch outputs',
        detail: err.data?.detail || err.message,
      }
      console.error('Error fetching outputs:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Get a single output by ID
   *
   * @param outputId - UUID of output to fetch
   * @returns Promise resolving to output response
   *
   * @example
   * ```ts
   * const { getOutput } = useOutputs()
   *
   * const output = await getOutput('550e8400-e29b-41d4-a716-446655440000')
   * if (output) {
   *   console.log('Output:', output.title)
   * }
   * ```
   */
  const getOutput = async (outputId: string): Promise<OutputResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await apiFetch<OutputResponse>(`/api/outputs/${outputId}`, {
        method: 'GET',
      })

      currentOutput.value = response
      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to fetch output',
        detail: err.data?.detail || err.message,
      }
      console.error('Error fetching output:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Create a new output
   *
   * @param data - Output creation data
   * @returns Promise resolving to created output response
   *
   * @example
   * ```ts
   * const { createOutput } = useOutputs()
   *
   * const output = await createOutput({
   *   output_type: 'grant_proposal',
   *   title: 'Education Grant Proposal 2024',
   *   content: 'Our comprehensive education program...',
   *   status: 'draft',
   *   writing_style_id: 'style-123',
   *   funder_name: 'Department of Education',
   *   requested_amount: 250000
   * })
   *
   * if (output) {
   *   console.log('Output created:', output.output_id)
   * }
   * ```
   */
  const createOutput = async (data: OutputCreateRequest): Promise<OutputResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await apiFetch<OutputResponse>('/api/outputs', {
        method: 'POST',
        body: data,
      })

      // Refresh outputs list after successful creation
      await getOutputs({
        page: 1,
        per_page: pagination.value?.per_page || 25,
      })

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to create output',
        detail: err.data?.detail || err.message,
      }
      console.error('Error creating output:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Update an existing output
   *
   * @param outputId - UUID of output to update
   * @param data - Partial output update data
   * @returns Promise resolving to updated output response
   *
   * @example
   * ```ts
   * const { updateOutput } = useOutputs()
   *
   * const updated = await updateOutput('output-123', {
   *   status: 'submitted',
   *   submission_date: '2024-03-15',
   *   content: 'Updated content...'
   * })
   *
   * if (updated) {
   *   console.log('Output updated:', updated.title)
   * }
   * ```
   */
  const updateOutput = async (
    outputId: string,
    data: OutputUpdateRequest
  ): Promise<OutputResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await apiFetch<OutputResponse>(`/api/outputs/${outputId}`, {
        method: 'PUT',
        body: data,
      })

      // Update in local state if present
      const index = outputs.value.findIndex((o) => o.output_id === outputId)
      if (index !== -1) {
        outputs.value[index] = response
      }

      // Update current output if it's the one being edited
      if (currentOutput.value?.output_id === outputId) {
        currentOutput.value = response
      }

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to update output',
        detail: err.data?.detail || err.message,
      }
      console.error('Error updating output:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete an output by ID
   *
   * @param outputId - UUID of output to delete
   * @returns Promise resolving to success status
   *
   * @example
   * ```ts
   * const { deleteOutput } = useOutputs()
   *
   * const success = await deleteOutput('550e8400-e29b-41d4-a716-446655440000')
   * if (success) {
   *   console.log('Output deleted successfully')
   * }
   * ```
   */
  const deleteOutput = async (outputId: string): Promise<boolean> => {
    loading.value = true
    error.value = null

    try {
      await apiFetch<SuccessResponse>(`/api/outputs/${outputId}`, {
        method: 'DELETE',
      })

      // Remove output from local state
      outputs.value = outputs.value.filter((o) => o.output_id !== outputId)

      // Update pagination count if available
      if (pagination.value) {
        pagination.value.total -= 1
      }

      // Clear current output if it was deleted
      if (currentOutput.value?.output_id === outputId) {
        currentOutput.value = null
      }

      return true
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to delete output',
        detail: err.data?.detail || err.message,
      }
      console.error('Error deleting output:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Get output statistics
   *
   * Returns aggregate statistics about outputs including:
   * - Total outputs
   * - Distribution by type and status
   * - Success rate and award amounts
   *
   * @returns Promise resolving to output statistics
   *
   * @example
   * ```ts
   * const { getStats } = useOutputs()
   *
   * const stats = await getStats()
   * if (stats) {
   *   console.log(`Total outputs: ${stats.total_outputs}`)
   *   console.log(`Success rate: ${stats.success_rate}%`)
   *   console.log('By type:', stats.by_type)
   * }
   * ```
   */
  const getStats = async (): Promise<OutputStatsResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await apiFetch<OutputStatsResponse>('/api/outputs/stats', {
        method: 'GET',
      })

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to fetch output statistics',
        detail: err.data?.detail || err.message,
      }
      console.error('Error fetching output stats:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Get output analytics
   *
   * Returns detailed analytics about outputs including:
   * - Time-based trends (by month)
   * - Success metrics and award rates
   * - Top funders
   * - Recent outputs
   *
   * @param params - Optional time range parameters
   * @returns Promise resolving to output analytics
   *
   * @example
   * ```ts
   * const { getAnalytics } = useOutputs()
   *
   * const analytics = await getAnalytics({
   *   date_from: '2024-01-01',
   *   date_to: '2024-12-31'
   * })
   *
   * if (analytics) {
   *   console.log('Monthly trend:', analytics.by_month)
   *   console.log('Top funders:', analytics.top_funders)
   * }
   * ```
   */
  const getAnalytics = async (params?: {
    date_from?: string
    date_to?: string
  }): Promise<OutputAnalyticsResponse | null> => {
    loading.value = true
    error.value = null

    try {
      // Build query string from parameters
      const queryParams = new URLSearchParams()

      if (params?.date_from) queryParams.append('date_from', params.date_from)
      if (params?.date_to) queryParams.append('date_to', params.date_to)

      const queryString = queryParams.toString()
      const url = `/api/outputs/analytics${queryString ? `?${queryString}` : ''}`

      const response = await apiFetch<OutputAnalyticsResponse>(url, {
        method: 'GET',
      })

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to fetch output analytics',
        detail: err.data?.detail || err.message,
      }
      console.error('Error fetching output analytics:', err)
      return null
    } finally {
      loading.value = false
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
    outputs.value = []
    pagination.value = null
    loading.value = false
    error.value = null
    currentOutput.value = null
  }

  // ============================================================================
  // Computed Properties
  // ============================================================================

  /**
   * Check if there are any outputs
   */
  const hasOutputs = computed(() => outputs.value.length > 0)

  /**
   * Total output count from pagination metadata
   */
  const totalOutputs = computed(() => pagination.value?.total || 0)

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

  /**
   * Get outputs grouped by status
   */
  const outputsByStatus = computed(() => {
    return outputs.value.reduce((acc, output) => {
      const status = output.status
      if (!acc[status]) {
        acc[status] = []
      }
      acc[status].push(output)
      return acc
    }, {} as Record<OutputStatus, OutputResponse[]>)
  })

  /**
   * Get outputs grouped by type
   */
  const outputsByType = computed(() => {
    return outputs.value.reduce((acc, output) => {
      const type = output.output_type
      if (!acc[type]) {
        acc[type] = []
      }
      acc[type].push(output)
      return acc
    }, {} as Record<OutputType, OutputResponse[]>)
  })

  // ============================================================================
  // Return Public API
  // ============================================================================

  return {
    // State
    outputs,
    pagination,
    loading,
    error,
    currentOutput,

    // Computed
    hasOutputs,
    totalOutputs,
    hasNextPage,
    hasPreviousPage,
    currentPage,
    totalPages,
    outputsByStatus,
    outputsByType,

    // Operations
    getOutputs,
    getOutput,
    createOutput,
    updateOutput,
    deleteOutput,
    getStats,
    getAnalytics,
    clearError,
    reset,
  }
}
