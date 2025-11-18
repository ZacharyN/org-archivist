<template>
  <UCard>
    <template #header>
      <div class="flex items-center gap-2">
        <UIcon name="i-heroicons-clock" class="w-6 h-6" />
        <h2 class="text-xl font-semibold">Recent Activity</h2>
      </div>
    </template>

    <UTabs :items="tabItems" class="w-full">
      <!-- Recent Chats Tab -->
      <template #chats>
        <div class="space-y-2 mt-4">
          <div v-if="loadingChats" class="text-center py-8">
            <UIcon name="i-heroicons-arrow-path" class="w-6 h-6 animate-spin inline-block text-gray-400" />
          </div>

          <div v-else-if="recentChats.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400">
            <UIcon name="i-heroicons-chat-bubble-left" class="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p class="text-sm">No recent conversations</p>
          </div>

          <UCard
            v-for="chat in recentChats"
            :key="chat.conversation_id"
            class="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
            @click="navigateTo(`/chat/${chat.conversation_id}`)"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <UIcon name="i-heroicons-chat-bubble-left" class="w-4 h-4 text-primary-500 flex-shrink-0" />
                  <h3 class="font-medium truncate">{{ chat.name || 'Untitled Conversation' }}</h3>
                </div>
                <p v-if="chat.messages && chat.messages.length > 0" class="text-sm text-gray-600 dark:text-gray-400 truncate">
                  {{ getLastMessage(chat) }}
                </p>
              </div>
              <div class="flex flex-col items-end gap-1 flex-shrink-0">
                <span class="text-xs text-gray-500 dark:text-gray-400">
                  {{ formatRelativeTime(chat.updated_at) }}
                </span>
                <UBadge v-if="chat.messages" color="neutral" variant="subtle" size="xs">
                  {{ chat.messages.length }} messages
                </UBadge>
              </div>
            </div>
          </UCard>
        </div>
      </template>

      <!-- Recent Uploads Tab -->
      <template #uploads>
        <div class="space-y-2 mt-4">
          <div v-if="loadingUploads" class="text-center py-8">
            <UIcon name="i-heroicons-arrow-path" class="w-6 h-6 animate-spin inline-block text-gray-400" />
          </div>

          <div v-else-if="recentUploads.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400">
            <UIcon name="i-heroicons-document" class="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p class="text-sm">No recent uploads</p>
          </div>

          <UCard
            v-for="upload in recentUploads"
            :key="upload.document_id"
            class="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
            @click="navigateTo(`/documents/${upload.document_id}`)"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <UIcon name="i-heroicons-document-text" class="w-4 h-4 text-blue-500 flex-shrink-0" />
                  <h3 class="font-medium truncate">{{ upload.filename }}</h3>
                </div>
                <div class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <UBadge color="info" variant="subtle" size="xs">
                    {{ upload.metadata.doc_type }}
                  </UBadge>
                  <span class="text-xs">{{ formatFileSize(upload.file_size) }}</span>
                </div>
              </div>
              <div class="flex flex-col items-end gap-1 flex-shrink-0">
                <span class="text-xs text-gray-500 dark:text-gray-400">
                  {{ formatRelativeTime(upload.upload_date) }}
                </span>
                <UBadge
                  :color="getStatusColor(upload.processing_status)"
                  variant="subtle"
                  size="xs"
                >
                  {{ upload.processing_status }}
                </UBadge>
              </div>
            </div>
          </UCard>
        </div>
      </template>

      <!-- Recent Outputs Tab -->
      <template #outputs>
        <div class="space-y-2 mt-4">
          <div v-if="loadingOutputs" class="text-center py-8">
            <UIcon name="i-heroicons-arrow-path" class="w-6 h-6 animate-spin inline-block text-gray-400" />
          </div>

          <div v-else-if="recentOutputs.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400">
            <UIcon name="i-heroicons-document-duplicate" class="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p class="text-sm">No recent outputs</p>
          </div>

          <UCard
            v-for="output in recentOutputs"
            :key="output.output_id"
            class="hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
            @click="navigateTo(`/outputs/${output.output_id}`)"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <UIcon name="i-heroicons-document-check" class="w-4 h-4 text-green-500 flex-shrink-0" />
                  <h3 class="font-medium truncate">{{ output.title }}</h3>
                </div>
                <div class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <UBadge color="success" variant="subtle" size="xs">
                    {{ formatOutputType(output.output_type) }}
                  </UBadge>
                  <span v-if="output.word_count" class="text-xs">{{ output.word_count }} words</span>
                </div>
              </div>
              <div class="flex flex-col items-end gap-1 flex-shrink-0">
                <span class="text-xs text-gray-500 dark:text-gray-400">
                  {{ formatRelativeTime(output.updated_at) }}
                </span>
                <UBadge
                  :color="getOutputStatusColor(output.status)"
                  variant="subtle"
                  size="xs"
                >
                  {{ output.status }}
                </UBadge>
              </div>
            </div>
          </UCard>
        </div>
      </template>
    </UTabs>
  </UCard>
</template>

<script setup lang="ts">
/**
 * RecentActivity Dashboard Widget
 *
 * Displays recent user activity across three tabs:
 * - Recent Chats: Last 5 conversations
 * - Recent Uploads: Last 5 document uploads
 * - Recent Outputs: Last 5 generated outputs
 *
 * Each item is clickable and navigates to the detail page.
 */

import type { TabsItem } from '@nuxt/ui'
import type { Conversation, DocumentResponse, OutputResponse } from '~/types/api'

// Type-safe Nuxt UI colors
type BadgeColor = 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'error' | 'neutral'

// ============================================================================
// Tab Configuration
// ============================================================================

const tabItems: TabsItem[] = [
  {
    label: 'Recent Chats',
    icon: 'i-heroicons-chat-bubble-left',
    slot: 'chats'
  },
  {
    label: 'Recent Uploads',
    icon: 'i-heroicons-document',
    slot: 'uploads'
  },
  {
    label: 'Recent Outputs',
    icon: 'i-heroicons-document-duplicate',
    slot: 'outputs'
  }
]

// ============================================================================
// State Management
// ============================================================================

// Recent Chats
const recentChats = ref<Conversation[]>([])
const loadingChats = ref(false)

// Recent Uploads
const recentUploads = ref<DocumentResponse[]>([])
const loadingUploads = ref(false)

// Recent Outputs
const recentOutputs = ref<OutputResponse[]>([])
const loadingOutputs = ref(false)

// ============================================================================
// Data Fetching
// ============================================================================

/**
 * Fetch recent conversations
 */
const fetchRecentChats = async () => {
  loadingChats.value = true

  try {
    const { apiFetch } = useApi()

    const response = await apiFetch<Conversation[]>('/api/chat', {
      params: {
        limit: 5,
        sort: 'updated_at:desc'
      }
    })

    recentChats.value = response
  } catch (error) {
    console.error('Failed to fetch recent chats:', error)
  } finally {
    loadingChats.value = false
  }
}

/**
 * Fetch recent document uploads
 */
const fetchRecentUploads = async () => {
  loadingUploads.value = true

  try {
    const { apiFetch } = useApi()

    const response = await apiFetch<DocumentResponse[]>('/api/documents', {
      params: {
        limit: 5,
        sort: 'upload_date:desc'
      }
    })

    recentUploads.value = response
  } catch (error) {
    console.error('Failed to fetch recent uploads:', error)
  } finally {
    loadingUploads.value = false
  }
}

/**
 * Fetch recent outputs
 */
const fetchRecentOutputs = async () => {
  loadingOutputs.value = true

  try {
    const { apiFetch } = useApi()

    const response = await apiFetch<OutputResponse[]>('/api/outputs', {
      params: {
        limit: 5,
        sort: 'updated_at:desc'
      }
    })

    recentOutputs.value = response
  } catch (error) {
    console.error('Failed to fetch recent outputs:', error)
  } finally {
    loadingOutputs.value = false
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

/**
 * Get last message from conversation
 */
const getLastMessage = (chat: Conversation): string => {
  if (!chat.messages || chat.messages.length === 0) {
    return 'No messages yet'
  }
  const lastMessage = chat.messages[chat.messages.length - 1]
  if (!lastMessage) {
    return 'No messages yet'
  }
  return lastMessage.content.substring(0, 100) + (lastMessage.content.length > 100 ? '...' : '')
}

/**
 * Format file size in human-readable format
 */
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

/**
 * Format output type for display
 */
const formatOutputType = (type: string): string => {
  return type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

/**
 * Get color for processing status badge
 */
const getStatusColor = (status: string): BadgeColor => {
  const statusColors: Record<string, BadgeColor> = {
    pending: 'warning',
    processing: 'info',
    completed: 'success',
    failed: 'error'
  }
  return statusColors[status] || 'neutral'
}

/**
 * Get color for output status badge
 */
const getOutputStatusColor = (status: string): BadgeColor => {
  const statusColors: Record<string, BadgeColor> = {
    draft: 'neutral',
    submitted: 'info',
    pending: 'warning',
    awarded: 'success',
    not_awarded: 'error'
  }
  return statusColors[status] || 'neutral'
}

// ============================================================================
// Lifecycle Hooks
// ============================================================================

/**
 * Fetch all data on component mount
 */
onMounted(() => {
  fetchRecentChats()
  fetchRecentUploads()
  fetchRecentOutputs()
})
</script>
