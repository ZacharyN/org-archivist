<template>
  <div
    class="px-4 py-3 cursor-pointer transition-colors hover:bg-gray-100 dark:hover:bg-gray-800"
    :class="{
      'bg-primary-50 dark:bg-primary-900/20 border-l-4 border-primary-500': isActive,
      'border-l-4 border-transparent': !isActive
    }"
    @click="$emit('click')"
  >
    <div class="flex items-start justify-between gap-3">
      <!-- Conversation Info -->
      <div class="flex-1 min-w-0">
        <!-- Conversation Name -->
        <div class="flex items-center gap-2 mb-1">
          <UIcon
            name="i-heroicons-chat-bubble-left"
            class="w-4 h-4 flex-shrink-0"
            :class="isActive ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400'"
          />
          <h3
            class="font-medium text-sm truncate"
            :class="isActive ? 'text-primary-700 dark:text-primary-300' : 'text-gray-900 dark:text-gray-100'"
          >
            {{ conversationName }}
          </h3>
        </div>

        <!-- Last Message Preview -->
        <p
          v-if="lastMessagePreview"
          class="text-xs truncate"
          :class="isActive ? 'text-primary-600/80 dark:text-primary-400/80' : 'text-gray-600 dark:text-gray-400'"
        >
          {{ lastMessagePreview }}
        </p>
        <p
          v-else
          class="text-xs italic"
          :class="isActive ? 'text-primary-500/60 dark:text-primary-400/60' : 'text-gray-500 dark:text-gray-500'"
        >
          No messages yet
        </p>
      </div>

      <!-- Timestamp & Message Count -->
      <div class="flex flex-col items-end gap-1 flex-shrink-0">
        <span
          class="text-xs whitespace-nowrap"
          :class="isActive ? 'text-primary-600 dark:text-primary-400' : 'text-gray-500 dark:text-gray-400'"
        >
          {{ formattedTimestamp }}
        </span>
        <UBadge
          v-if="messageCount > 0"
          :color="isActive ? 'primary' : 'neutral'"
          variant="subtle"
          size="xs"
        >
          {{ messageCount }}
        </UBadge>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ConversationItem Component
 *
 * Individual conversation list item that displays:
 * - Conversation name (or default "Untitled Conversation")
 * - Last message preview (truncated to 60 characters)
 * - Relative timestamp (e.g., "2h ago")
 * - Message count badge
 * - Active state highlighting with left border
 */

import type { Conversation } from '~/types/api'

// ============================================================================
// Props & Emits
// ============================================================================

interface Props {
  /** Conversation data */
  conversation: Conversation
  /** Whether this conversation is currently active */
  isActive?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isActive: false
})

interface Emits {
  /** Emitted when conversation item is clicked */
  (e: 'click'): void
}

defineEmits<Emits>()

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Display name for the conversation
 * Falls back to "Untitled Conversation" if no name is set
 */
const conversationName = computed(() => {
  return props.conversation.name || 'Untitled Conversation'
})

/**
 * Preview of the last message in the conversation
 * Truncated to 60 characters with ellipsis
 */
const lastMessagePreview = computed(() => {
  if (!props.conversation.messages || props.conversation.messages.length === 0) {
    return null
  }

  const lastMessage = props.conversation.messages[props.conversation.messages.length - 1]
  if (!lastMessage?.content) {
    return null
  }

  const maxLength = 60
  const content = lastMessage.content.trim()

  return content.length > maxLength
    ? content.substring(0, maxLength) + '...'
    : content
})

/**
 * Number of messages in the conversation
 */
const messageCount = computed(() => {
  return props.conversation.messages?.length || 0
})

/**
 * Format timestamp as relative time (e.g., "2h ago", "3d ago")
 */
const formattedTimestamp = computed(() => {
  const date = new Date(props.conversation.updated_at)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'Now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
})
</script>
