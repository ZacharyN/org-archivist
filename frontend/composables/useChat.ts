/**
 * Chat Composable
 *
 * Provides conversation and message management for the AI writing assistant chat interface.
 *
 * Features:
 * - Fetch and manage conversations
 * - Send messages and receive responses
 * - SSE streaming support for real-time AI responses
 * - Conversation context management (writing style, audience, section, tone)
 * - Message history tracking
 * - Auto-save functionality
 * - Artifact version tracking
 *
 * @example
 * ```ts
 * const {
 *   conversations,
 *   currentConversation,
 *   messages,
 *   loading,
 *   error,
 *   getConversations,
 *   getConversation,
 *   createConversation,
 *   sendMessage,
 *   deleteConversation,
 *   updateConversationContext,
 *   getConversationContext
 * } = useChat()
 *
 * // Create new conversation
 * const conversation = await createConversation({
 *   name: 'Grant Proposal Draft',
 *   context: {
 *     writing_style_id: 'style-123',
 *     audience: 'Federal RFP',
 *     section: 'Organizational Capacity',
 *     tone: '0.9'
 *   }
 * })
 *
 * // Send a message
 * await sendMessage(conversation.conversation_id, 'Write an organizational capacity section')
 *
 * // Get all conversations
 * await getConversations()
 * ```
 */

import type {
  Conversation,
  ConversationContext,
  ConversationContextResponse,
  ChatMessage,
  ChatRequest,
  ChatResponse,
  PaginatedResponse,
  PaginationMetadata,
  ApiError,
  SuccessResponse,
} from '~/types/api'

/**
 * Conversation creation request parameters
 */
export interface CreateConversationParams {
  name?: string
  context?: ConversationContext
}

/**
 * Get conversations query parameters
 */
export interface GetConversationsParams {
  page?: number
  per_page?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  search?: string
}

/**
 * Send message parameters
 */
export interface SendMessageParams {
  message: string
  conversation_id: string
  context?: ConversationContext
}

/**
 * Streaming response chunk for SSE
 */
export interface StreamChunk {
  type: 'sources' | 'content' | 'metadata' | 'error'
  data: any
}

/**
 * Chat composable state and operations
 */
export const useChat = () => {
  // ============================================================================
  // State Management
  // ============================================================================

  /**
   * List of conversations (reactive state)
   */
  const conversations = useState<Conversation[]>('conversations', () => [])

  /**
   * Currently active conversation
   */
  const currentConversation = useState<Conversation | null>('current_conversation', () => null)

  /**
   * Messages in current conversation
   */
  const messages = useState<ChatMessage[]>('chat_messages', () => [])

  /**
   * Conversation context (writing style, audience, section, tone, filters)
   */
  const conversationContext = useState<ConversationContext>('conversation_context', () => ({
    writing_style_id: undefined,
    audience: undefined,
    section: undefined,
    tone: undefined,
    filters: undefined,
    artifacts: [],
  }))

  /**
   * Pagination metadata for conversations list
   */
  const pagination = useState<PaginationMetadata | null>('conversations_pagination', () => null)

  /**
   * Loading state for async operations
   */
  const loading = ref(false)

  /**
   * Error state for operations
   */
  const error = ref<ApiError | null>(null)

  /**
   * Streaming state (indicates if a message is currently being streamed)
   */
  const isStreaming = ref(false)

  /**
   * Currently streaming message content (accumulated)
   */
  const streamingContent = ref('')

  /**
   * Auto-save timer ID
   */
  let autoSaveTimer: NodeJS.Timeout | null = null

  /**
   * Auto-save interval in milliseconds (default: 5 minutes)
   */
  const autoSaveInterval = ref(5 * 60 * 1000)

  // ============================================================================
  // API Operations
  // ============================================================================

  const { apiFetch } = useApi()

  /**
   * Fetch conversations with optional filters and pagination
   *
   * @param params - Query parameters including pagination and search
   * @returns Promise resolving to paginated conversations response
   *
   * @example
   * ```ts
   * const { getConversations } = useChat()
   *
   * // Get all conversations
   * await getConversations()
   *
   * // Get with pagination
   * await getConversations({
   *   page: 1,
   *   per_page: 25,
   *   sort_by: 'updated_at',
   *   sort_order: 'desc'
   * })
   *
   * // Search conversations
   * await getConversations({
   *   search: 'grant proposal',
   *   page: 1,
   *   per_page: 10
   * })
   * ```
   */
  const getConversations = async (
    params?: GetConversationsParams
  ): Promise<PaginatedResponse<Conversation> | null> => {
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

      const queryString = queryParams.toString()
      const url = `/api/conversations${queryString ? `?${queryString}` : ''}`

      const response = await apiFetch<PaginatedResponse<Conversation>>(url, {
        method: 'GET',
      })

      // Update state with response
      conversations.value = response.items
      pagination.value = response.pagination

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to fetch conversations',
        detail: err.data?.detail || err.message,
      }
      console.error('Error fetching conversations:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Get a single conversation by ID
   *
   * Loads conversation with full message history and context.
   * Sets it as the current conversation.
   *
   * @param conversationId - UUID of conversation to fetch
   * @returns Promise resolving to conversation response
   *
   * @example
   * ```ts
   * const { getConversation } = useChat()
   *
   * const conversation = await getConversation('550e8400-e29b-41d4-a716-446655440000')
   * if (conversation) {
   *   console.log('Loaded conversation:', conversation.name)
   *   console.log('Messages:', conversation.messages.length)
   * }
   * ```
   */
  const getConversation = async (conversationId: string): Promise<Conversation | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await apiFetch<Conversation>(`/api/conversations/${conversationId}`, {
        method: 'GET',
      })

      // Set as current conversation
      currentConversation.value = response
      messages.value = response.messages || []

      // Load conversation context if available
      if (response.context) {
        conversationContext.value = response.context
      }

      // Start auto-save timer
      startAutoSave()

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to fetch conversation',
        detail: err.data?.detail || err.message,
      }
      console.error('Error fetching conversation:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Create a new conversation
   *
   * @param params - Conversation creation parameters (name, context)
   * @returns Promise resolving to created conversation
   *
   * @example
   * ```ts
   * const { createConversation } = useChat()
   *
   * const conversation = await createConversation({
   *   name: 'Grant Proposal - Q2 2024',
   *   context: {
   *     writing_style_id: 'style-uuid-123',
   *     audience: 'Federal RFP',
   *     section: 'Organizational Capacity',
   *     tone: '0.9',
   *     filters: {
   *       doc_types: ['Grant Proposal'],
   *       years: [2023, 2024]
   *     }
   *   }
   * })
   * ```
   */
  const createConversation = async (
    params: CreateConversationParams
  ): Promise<Conversation | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await apiFetch<Conversation>('/api/conversations', {
        method: 'POST',
        body: {
          name: params.name,
          context: params.context,
        },
      })

      // Set as current conversation
      currentConversation.value = response
      messages.value = response.messages || []

      // Set conversation context
      if (params.context) {
        conversationContext.value = params.context
      }

      // Add to conversations list
      conversations.value = [response, ...conversations.value]

      // Start auto-save timer
      startAutoSave()

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to create conversation',
        detail: err.data?.detail || err.message,
      }
      console.error('Error creating conversation:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Send a message to a conversation
   *
   * Adds user message to conversation and gets AI response.
   * Updates message history with both user and assistant messages.
   *
   * @param conversationId - UUID of conversation
   * @param message - User message content
   * @param streamCallback - Optional callback for streaming response chunks
   * @returns Promise resolving to chat response
   *
   * @example
   * ```ts
   * const { sendMessage } = useChat()
   *
   * // Send message without streaming
   * const response = await sendMessage(
   *   'conversation-id',
   *   'Write an organizational capacity section for our grant'
   * )
   *
   * // Send message with streaming
   * const response = await sendMessage(
   *   'conversation-id',
   *   'Write a program description',
   *   (chunk) => {
   *     console.log('Streaming chunk:', chunk)
   *   }
   * )
   * ```
   */
  const sendMessage = async (
    conversationId: string,
    message: string,
    streamCallback?: (chunk: string) => void
  ): Promise<ChatResponse | null> => {
    loading.value = true
    error.value = null

    try {
      // Add user message to local state immediately (optimistic update)
      const userMessage: ChatMessage = {
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      }
      messages.value.push(userMessage)

      // If streaming callback provided, use SSE endpoint
      if (streamCallback) {
        return await sendStreamingMessage(conversationId, message, streamCallback)
      }

      // Otherwise, use standard endpoint
      const response = await apiFetch<ChatResponse>(`/api/chat/${conversationId}`, {
        method: 'POST',
        body: {
          message,
          context: conversationContext.value,
        },
      })

      // Add assistant message to local state
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.message,
        timestamp: new Date().toISOString(),
        metadata: response.metadata,
      }
      messages.value.push(assistantMessage)

      // Update current conversation if this is it
      if (currentConversation.value?.conversation_id === conversationId) {
        currentConversation.value.messages = messages.value
        currentConversation.value.updated_at = new Date().toISOString()
      }

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to send message',
        detail: err.data?.detail || err.message,
      }
      console.error('Error sending message:', err)

      // Remove optimistic user message on error
      messages.value.pop()

      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Send message with SSE streaming support
   *
   * @param conversationId - UUID of conversation
   * @param message - User message content
   * @param onChunk - Callback for each streamed chunk
   * @returns Promise resolving to final chat response
   */
  const sendStreamingMessage = async (
    conversationId: string,
    message: string,
    onChunk: (chunk: string) => void
  ): Promise<ChatResponse | null> => {
    isStreaming.value = true
    streamingContent.value = ''

    try {
      const config = useRuntimeConfig()
      const { accessToken } = useAuth()

      const response = await fetch(
        `${config.public.apiBase}/api/chat/${conversationId}/stream`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${accessToken.value}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message,
            context: conversationContext.value,
          }),
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let sources: any[] = []
      let metadata: any = null

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data:')) {
            try {
              const data = JSON.parse(line.slice(5).trim())

              // Handle different SSE event types
              if (data.sources) {
                sources = data.sources
              } else if (data.content) {
                streamingContent.value += data.content
                onChunk(data.content)
              } else if (data.metadata) {
                metadata = data.metadata
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e)
            }
          }
        }
      }

      // Add assistant message with final content
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: streamingContent.value,
        timestamp: new Date().toISOString(),
        metadata,
      }
      messages.value.push(assistantMessage)

      // Update current conversation
      if (currentConversation.value?.conversation_id === conversationId) {
        currentConversation.value.messages = messages.value
        currentConversation.value.updated_at = new Date().toISOString()
      }

      return {
        message: streamingContent.value,
        conversation_id: conversationId,
        sources,
        metadata,
      }
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to stream message',
        detail: err.message,
      }
      console.error('Error streaming message:', err)
      return null
    } finally {
      isStreaming.value = false
      streamingContent.value = ''
    }
  }

  /**
   * Delete a conversation by ID
   *
   * @param conversationId - UUID of conversation to delete
   * @returns Promise resolving to success status
   *
   * @example
   * ```ts
   * const { deleteConversation } = useChat()
   *
   * const success = await deleteConversation('550e8400-e29b-41d4-a716-446655440000')
   * if (success) {
   *   console.log('Conversation deleted successfully')
   * }
   * ```
   */
  const deleteConversation = async (conversationId: string): Promise<boolean> => {
    loading.value = true
    error.value = null

    try {
      await apiFetch<SuccessResponse>(`/api/conversations/${conversationId}`, {
        method: 'DELETE',
      })

      // Remove conversation from local state
      conversations.value = conversations.value.filter(
        (conv) => conv.conversation_id !== conversationId
      )

      // Clear current conversation if it was deleted
      if (currentConversation.value?.conversation_id === conversationId) {
        currentConversation.value = null
        messages.value = []
        conversationContext.value = {}
      }

      // Stop auto-save timer
      stopAutoSave()

      // Update pagination count if available
      if (pagination.value) {
        pagination.value.total -= 1
      }

      return true
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to delete conversation',
        detail: err.data?.detail || err.message,
      }
      console.error('Error deleting conversation:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Update conversation context
   *
   * Updates the conversation's context (writing style, audience, section, tone, filters).
   * Context changes affect subsequent message generation.
   *
   * @param conversationId - UUID of conversation
   * @param context - New context to merge with existing context
   * @returns Promise resolving to updated context response
   *
   * @example
   * ```ts
   * const { updateConversationContext } = useChat()
   *
   * await updateConversationContext('conversation-id', {
   *   writing_style_id: 'new-style-id',
   *   audience: 'Foundation Grant',
   *   tone: '0.7'
   * })
   * ```
   */
  const updateConversationContext = async (
    conversationId: string,
    context: Partial<ConversationContext>
  ): Promise<ConversationContextResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await apiFetch<ConversationContextResponse>(
        `/api/conversations/${conversationId}/context`,
        {
          method: 'PUT',
          body: { context },
        }
      )

      // Update local context state
      conversationContext.value = {
        ...conversationContext.value,
        ...context,
      }

      // Update current conversation if this is it
      if (currentConversation.value?.conversation_id === conversationId) {
        currentConversation.value.context = conversationContext.value
      }

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to update conversation context',
        detail: err.data?.detail || err.message,
      }
      console.error('Error updating conversation context:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Get conversation context
   *
   * Fetches the current context for a conversation.
   *
   * @param conversationId - UUID of conversation
   * @returns Promise resolving to conversation context response
   *
   * @example
   * ```ts
   * const { getConversationContext } = useChat()
   *
   * const contextResponse = await getConversationContext('conversation-id')
   * if (contextResponse) {
   *   console.log('Writing style:', contextResponse.context.writing_style_id)
   *   console.log('Audience:', contextResponse.context.audience)
   * }
   * ```
   */
  const getConversationContext = async (
    conversationId: string
  ): Promise<ConversationContextResponse | null> => {
    loading.value = true
    error.value = null

    try {
      const response = await apiFetch<ConversationContextResponse>(
        `/api/conversations/${conversationId}/context`,
        {
          method: 'GET',
        }
      )

      // Update local context state
      conversationContext.value = response.context

      return response
    } catch (err: any) {
      error.value = {
        status: err.status || 500,
        message: err.message || 'Failed to fetch conversation context',
        detail: err.data?.detail || err.message,
      }
      console.error('Error fetching conversation context:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  // ============================================================================
  // Auto-Save Functionality
  // ============================================================================

  /**
   * Start auto-save timer
   *
   * Automatically saves conversation context at regular intervals.
   */
  const startAutoSave = () => {
    stopAutoSave() // Clear existing timer if any

    autoSaveTimer = setInterval(async () => {
      if (currentConversation.value && conversationContext.value) {
        await updateConversationContext(
          currentConversation.value.conversation_id,
          conversationContext.value
        )
      }
    }, autoSaveInterval.value)
  }

  /**
   * Stop auto-save timer
   */
  const stopAutoSave = () => {
    if (autoSaveTimer) {
      clearInterval(autoSaveTimer)
      autoSaveTimer = null
    }
  }

  /**
   * Manual save of current conversation
   */
  const saveConversation = async (): Promise<boolean> => {
    if (!currentConversation.value) {
      return false
    }

    const result = await updateConversationContext(
      currentConversation.value.conversation_id,
      conversationContext.value
    )

    return result !== null
  }

  // ============================================================================
  // Utility Functions
  // ============================================================================

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
    conversations.value = []
    currentConversation.value = null
    messages.value = []
    conversationContext.value = {}
    pagination.value = null
    loading.value = false
    error.value = null
    isStreaming.value = false
    streamingContent.value = ''
    stopAutoSave()
  }

  /**
   * Set current conversation (without fetching from API)
   *
   * Useful when selecting a conversation from the list
   */
  const setCurrentConversation = (conversation: Conversation | null) => {
    currentConversation.value = conversation
    messages.value = conversation?.messages || []
    conversationContext.value = conversation?.context || {}

    if (conversation) {
      startAutoSave()
    } else {
      stopAutoSave()
    }
  }

  // ============================================================================
  // Computed Properties
  // ============================================================================

  /**
   * Check if there are any conversations
   */
  const hasConversations = computed(() => conversations.value.length > 0)

  /**
   * Total conversation count from pagination metadata
   */
  const totalConversations = computed(() => pagination.value?.total || 0)

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
   * Check if a conversation is currently active
   */
  const hasActiveConversation = computed(() => !!currentConversation.value)

  /**
   * Current conversation ID (convenience getter)
   */
  const currentConversationId = computed(
    () => currentConversation.value?.conversation_id || null
  )

  /**
   * Number of messages in current conversation
   */
  const messageCount = computed(() => messages.value.length)

  // ============================================================================
  // Lifecycle Hooks
  // ============================================================================

  // Clean up auto-save timer on unmount
  onUnmounted(() => {
    stopAutoSave()
  })

  // ============================================================================
  // Return Public API
  // ============================================================================

  return {
    // State
    conversations,
    currentConversation,
    messages,
    conversationContext,
    pagination,
    loading,
    error,
    isStreaming,
    streamingContent,
    autoSaveInterval,

    // Computed
    hasConversations,
    totalConversations,
    hasNextPage,
    hasPreviousPage,
    currentPage,
    totalPages,
    hasActiveConversation,
    currentConversationId,
    messageCount,

    // Operations
    getConversations,
    getConversation,
    createConversation,
    sendMessage,
    deleteConversation,
    updateConversationContext,
    getConversationContext,
    setCurrentConversation,
    saveConversation,
    startAutoSave,
    stopAutoSave,
    clearError,
    reset,
  }
}
