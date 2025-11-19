<template>
  <div class="flex flex-col h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800">
    <!-- Header with New Chat Button -->
    <div class="p-4 border-b border-gray-200 dark:border-gray-800">
      <UButton
        color="primary"
        variant="solid"
        size="md"
        icon="i-heroicons-plus"
        label="New Chat"
        class="w-full justify-center"
        @click="handleNewChat"
      />
    </div>

    <!-- Search Input -->
    <div class="p-4 border-b border-gray-200 dark:border-gray-800">
      <UInput
        v-model="searchQuery"
        icon="i-heroicons-magnifying-glass"
        placeholder="Search conversations..."
        size="md"
      >
        <template v-if="searchQuery" #trailing>
          <UButton
            color="neutral"
            variant="ghost"
            size="xs"
            icon="i-heroicons-x-mark"
            @click="searchQuery = ''"
          />
        </template>
      </UInput>
    </div>

    <!-- Conversations List -->
    <div class="flex-1 overflow-y-auto">
      <!-- Loading State -->
      <div v-if="loading" class="flex items-center justify-center py-8">
        <UIcon name="i-heroicons-arrow-path" class="w-6 h-6 animate-spin text-gray-400" />
      </div>

      <!-- Empty State -->
      <div v-else-if="filteredConversations.length === 0" class="flex flex-col items-center justify-center py-12 px-4 text-center">
        <UIcon name="i-heroicons-chat-bubble-left-right" class="w-12 h-12 text-gray-400 mb-3" />
        <p class="text-sm text-gray-600 dark:text-gray-400">
          {{ searchQuery ? 'No conversations found' : 'No conversations yet' }}
        </p>
        <p v-if="!searchQuery" class="text-xs text-gray-500 dark:text-gray-500 mt-1">
          Start a new chat to begin
        </p>
      </div>

      <!-- Grouped Conversations -->
      <div v-else class="py-2">
        <!-- Today -->
        <div v-if="groupedConversations.today.length > 0" class="mb-4">
          <div class="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Today
          </div>
          <ConversationItem
            v-for="conversation in groupedConversations.today"
            :key="conversation.conversation_id"
            :conversation="conversation"
            :is-active="isActive(conversation.conversation_id)"
            @click="handleSelectConversation(conversation)"
          />
        </div>

        <!-- Yesterday -->
        <div v-if="groupedConversations.yesterday.length > 0" class="mb-4">
          <div class="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Yesterday
          </div>
          <ConversationItem
            v-for="conversation in groupedConversations.yesterday"
            :key="conversation.conversation_id"
            :conversation="conversation"
            :is-active="isActive(conversation.conversation_id)"
            @click="handleSelectConversation(conversation)"
          />
        </div>

        <!-- Last 7 Days -->
        <div v-if="groupedConversations.lastWeek.length > 0" class="mb-4">
          <div class="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Last 7 Days
          </div>
          <ConversationItem
            v-for="conversation in groupedConversations.lastWeek"
            :key="conversation.conversation_id"
            :conversation="conversation"
            :is-active="isActive(conversation.conversation_id)"
            @click="handleSelectConversation(conversation)"
          />
        </div>

        <!-- Older -->
        <div v-if="groupedConversations.older.length > 0">
          <div class="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Older
          </div>
          <ConversationItem
            v-for="conversation in groupedConversations.older"
            :key="conversation.conversation_id"
            :conversation="conversation"
            :is-active="isActive(conversation.conversation_id)"
            @click="handleSelectConversation(conversation)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ConversationList Sidebar Component
 *
 * Left sidebar for chat interface with:
 * - "New Chat" button at the top
 * - Search input for filtering conversations
 * - Conversations grouped by date (Today, Yesterday, Last 7 days, Older)
 * - Each item shows: conversation name, last message preview, timestamp
 * - Active conversation highlighting
 * - Click to navigate to conversation
 */

import type { Conversation } from '~/types/api'

// ============================================================================
// Props & Emits
// ============================================================================

interface Props {
  /** Currently active conversation ID */
  activeConversationId?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  activeConversationId: null
})

interface Emits {
  /** Emitted when user wants to create a new chat */
  (e: 'new-chat'): void
  /** Emitted when user selects a conversation */
  (e: 'select-conversation', conversation: Conversation): void
}

const emit = defineEmits<Emits>()

// ============================================================================
// Composables
// ============================================================================

const { conversations, getConversations, loading } = useChat()
const route = useRoute()

// ============================================================================
// State
// ============================================================================

/** Search query for filtering conversations */
const searchQuery = ref('')

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Filter conversations based on search query
 */
const filteredConversations = computed(() => {
  if (!searchQuery.value) {
    return conversations.value
  }

  const query = searchQuery.value.toLowerCase()
  return conversations.value.filter(conversation => {
    // Search in conversation name
    const nameMatch = conversation.name?.toLowerCase().includes(query)

    // Search in last message content
    const lastMessage = conversation.messages?.[conversation.messages.length - 1]
    const messageMatch = lastMessage?.content?.toLowerCase().includes(query)

    return nameMatch || messageMatch
  })
})

/**
 * Group conversations by date categories
 */
const groupedConversations = computed(() => {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const lastWeek = new Date(today)
  lastWeek.setDate(lastWeek.getDate() - 7)

  const groups = {
    today: [] as Conversation[],
    yesterday: [] as Conversation[],
    lastWeek: [] as Conversation[],
    older: [] as Conversation[]
  }

  for (const conversation of filteredConversations.value) {
    const updatedAt = new Date(conversation.updated_at)

    if (updatedAt >= today) {
      groups.today.push(conversation)
    } else if (updatedAt >= yesterday) {
      groups.yesterday.push(conversation)
    } else if (updatedAt >= lastWeek) {
      groups.lastWeek.push(conversation)
    } else {
      groups.older.push(conversation)
    }
  }

  return groups
})

// ============================================================================
// Methods
// ============================================================================

/**
 * Check if a conversation is currently active
 */
const isActive = (conversationId: string): boolean => {
  // Use prop if provided, otherwise check route
  if (props.activeConversationId) {
    return props.activeConversationId === conversationId
  }
  return route.params.id === conversationId
}

/**
 * Handle new chat button click
 */
const handleNewChat = () => {
  emit('new-chat')
}

/**
 * Handle conversation selection
 */
const handleSelectConversation = (conversation: Conversation) => {
  emit('select-conversation', conversation)
}

// ============================================================================
// Lifecycle Hooks
// ============================================================================

/**
 * Fetch conversations on mount
 */
onMounted(async () => {
  await getConversations({
    sort_by: 'updated_at',
    sort_order: 'desc',
    per_page: 100 // Load more for sidebar
  })
})
</script>
