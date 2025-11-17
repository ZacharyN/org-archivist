<template>
  <UCard class="bg-gradient-to-br from-primary-50 to-primary-100 dark:from-primary-900 dark:to-primary-800">
    <template #header>
      <div class="flex items-center gap-2">
        <UIcon name="i-heroicons-chat-bubble-left-right" class="w-6 h-6" />
        <h2 class="text-xl font-semibold">Start a Conversation</h2>
      </div>
    </template>

    <div class="space-y-4">
      <!-- New Conversation Button -->
      <UButton
        block
        size="lg"
        color="primary"
        icon="i-heroicons-plus"
        :loading="isCreatingConversation"
        @click="startNewChat"
      >
        New Conversation
      </UButton>

      <!-- Resume Recent Conversation -->
      <USelectMenu
        v-model="selectedConversation"
        :options="recentConversationsOptions"
        placeholder="Or resume a recent conversation..."
        :loading="loadingConversations"
        :disabled="recentConversationsOptions.length === 0"
        @update:model-value="resumeChat"
      >
        <template #label>
          <span v-if="selectedConversation">
            {{ recentConversations.find(c => c.conversation_id === selectedConversation)?.name }}
          </span>
        </template>
      </USelectMenu>

      <!-- Quick Context Selectors -->
      <div class="grid grid-cols-2 gap-2">
        <!-- Writing Style Selector -->
        <USelectMenu
          v-model="quickContext.writingStyleId"
          :options="writingStyleOptions"
          placeholder="Writing Style"
          size="sm"
          :loading="loadingWritingStyles"
        >
          <template #label>
            <span v-if="quickContext.writingStyleId" class="truncate">
              {{ writingStyles.find(s => s.style_id === quickContext.writingStyleId)?.name }}
            </span>
          </template>
        </USelectMenu>

        <!-- Audience Input -->
        <UInput
          v-model="quickContext.audience"
          placeholder="Audience"
          size="sm"
          icon="i-heroicons-user-group"
        />
      </div>

      <!-- Context Applied Indicator -->
      <div v-if="quickContext.writingStyleId || quickContext.audience" class="text-xs text-gray-600 dark:text-gray-400">
        <UIcon name="i-heroicons-information-circle" class="w-3 h-3 inline" />
        Context will be applied to new conversations
      </div>
    </div>

    <template #footer>
      <NuxtLink
        to="/chat"
        class="text-sm text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
      >
        <span>Open full chat interface</span>
        <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
      </NuxtLink>
    </template>
  </UCard>
</template>

<script setup lang="ts">
/**
 * ChatQuickStart Dashboard Widget
 *
 * Provides quick access to AI chat functionality from the dashboard:
 * - Start new conversations with one click
 * - Resume recent conversations from dropdown
 * - Set quick context (writing style, audience)
 * - Navigate to full chat interface
 */

import type { Conversation, WritingStyle } from '~/types/api'

// ============================================================================
// State Management
// ============================================================================

// Recent conversations
const recentConversations = ref<Conversation[]>([])
const selectedConversation = ref<string | null>(null)
const loadingConversations = ref(false)

// Writing styles
const writingStyles = ref<WritingStyle[]>([])
const loadingWritingStyles = ref(false)

// Quick context settings
const quickContext = ref({
  writingStyleId: null as string | null,
  audience: '' as string
})

// UI state
const isCreatingConversation = ref(false)

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Format recent conversations for USelectMenu
 */
const recentConversationsOptions = computed(() => {
  return recentConversations.value.map(conv => ({
    label: conv.name || 'Untitled Conversation',
    value: conv.conversation_id,
    icon: 'i-heroicons-chat-bubble-left',
    // Show timestamp in sublabel
    description: formatRelativeTime(conv.updated_at)
  }))
})

/**
 * Format writing styles for USelectMenu
 */
const writingStyleOptions = computed(() => {
  return writingStyles.value.map(style => ({
    label: style.name,
    value: style.style_id,
    icon: 'i-heroicons-pencil-square',
    // Show style type as badge
    description: style.type
  }))
})

// ============================================================================
// Data Fetching
// ============================================================================

/**
 * Fetch recent conversations
 */
const fetchRecentConversations = async () => {
  loadingConversations.value = true

  try {
    const { apiFetch } = useApi()

    // Fetch last 5 conversations
    const response = await apiFetch<Conversation[]>('/api/chat', {
      params: {
        limit: 5,
        sort: 'updated_at:desc'
      }
    })

    recentConversations.value = response
  } catch (error) {
    console.error('Failed to fetch recent conversations:', error)
    // Don't show error - non-critical for dashboard widget
  } finally {
    loadingConversations.value = false
  }
}

/**
 * Fetch writing styles
 */
const fetchWritingStyles = async () => {
  loadingWritingStyles.value = true

  try {
    const { apiFetch } = useApi()

    // Fetch only active writing styles
    const response = await apiFetch<WritingStyle[]>('/api/writing-styles', {
      params: {
        active: true
      }
    })

    writingStyles.value = response
  } catch (error) {
    console.error('Failed to fetch writing styles:', error)
    // Don't show error - non-critical for dashboard widget
  } finally {
    loadingWritingStyles.value = false
  }
}

// ============================================================================
// Actions
// ============================================================================

/**
 * Start a new chat conversation
 */
const startNewChat = async () => {
  isCreatingConversation.value = true

  try {
    const { apiFetch } = useApi()

    // Create new conversation
    const conversation = await apiFetch<Conversation>('/api/chat', {
      method: 'POST',
      body: {
        name: 'New Conversation',
        context: {
          writing_style_id: quickContext.value.writingStyleId,
          audience: quickContext.value.audience
        }
      }
    })

    // Navigate to the new conversation
    navigateTo(`/chat/${conversation.conversation_id}`)
  } catch (error) {
    console.error('Failed to create conversation:', error)

    // Show error toast
    const toast = useToast()
    toast.add({
      title: 'Failed to create conversation',
      description: 'Please try again or navigate to the chat page directly.',
      color: 'red',
      icon: 'i-heroicons-exclamation-triangle'
    })
  } finally {
    isCreatingConversation.value = false
  }
}

/**
 * Resume an existing conversation
 */
const resumeChat = (conversationId: string) => {
  if (conversationId) {
    navigateTo(`/chat/${conversationId}`)
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format timestamp as relative time (e.g., "2 hours ago")
 */
const formatRelativeTime = (timestamp: string): string => {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`

  return date.toLocaleDateString()
}

// ============================================================================
// Lifecycle Hooks
// ============================================================================

/**
 * Fetch data on component mount
 */
onMounted(() => {
  fetchRecentConversations()
  fetchWritingStyles()
})
</script>
