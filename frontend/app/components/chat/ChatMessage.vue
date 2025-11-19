<template>
  <div
    class="chat-message py-4 px-6"
    :class="{
      'bg-gray-50 dark:bg-gray-800/50': isAssistant,
      'bg-white dark:bg-gray-900': isUser
    }"
  >
    <div class="max-w-4xl mx-auto">
      <!-- Message Header -->
      <div class="flex items-start gap-4 mb-3">
        <!-- Avatar -->
        <div
          class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
          :class="{
            'bg-primary-100 dark:bg-primary-900/30': isAssistant,
            'bg-neutral-100 dark:bg-neutral-800': isUser
          }"
        >
          <UIcon
            :name="isUser ? 'i-heroicons-user' : 'i-heroicons-sparkles'"
            class="w-5 h-5"
            :class="{
              'text-primary-600 dark:text-primary-400': isAssistant,
              'text-neutral-600 dark:text-neutral-400': isUser
            }"
          />
        </div>

        <!-- Header Info -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-2">
            <span
              class="font-semibold text-sm"
              :class="{
                'text-primary-700 dark:text-primary-300': isAssistant,
                'text-neutral-700 dark:text-neutral-300': isUser
              }"
            >
              {{ isUser ? 'You' : 'Assistant' }}
            </span>
            <span class="text-xs text-gray-500 dark:text-gray-400">
              {{ formattedTimestamp }}
            </span>
          </div>

          <!-- Message Content -->
          <div
            class="prose prose-sm dark:prose-invert max-w-none"
            :class="{
              'prose-primary': isAssistant,
              'prose-neutral': isUser
            }"
            v-html="renderedContent"
          />

          <!-- Source Citations (Assistant only) -->
          <div v-if="isAssistant && sources && sources.length > 0" class="mt-4 space-y-2">
            <UAccordion
              :items="accordionItems"
            >
              <template #default="{ item, open }">
                <UButton
                  color="neutral"
                  variant="ghost"
                  class="w-full justify-between"
                >
                  <div class="flex items-center gap-2 flex-1 min-w-0">
                    <UIcon
                      name="i-heroicons-document-text"
                      class="w-4 h-4 flex-shrink-0"
                    />
                    <span class="text-sm font-medium truncate">
                      {{ item.filename }}
                    </span>
                    <UBadge
                      color="info"
                      variant="subtle"
                      size="xs"
                      class="ml-2"
                    >
                      {{ (item.relevance * 100).toFixed(0) }}%
                    </UBadge>
                  </div>
                  <UIcon
                    name="i-heroicons-chevron-down"
                    class="w-4 h-4 flex-shrink-0 transition-transform"
                    :class="{ 'rotate-180': open }"
                  />
                </UButton>
              </template>

              <template #item="{ item }">
                <div class="p-4 bg-gray-50 dark:bg-gray-800/50">
                  <!-- Source Metadata -->
                  <div class="flex items-center gap-3 mb-3 text-xs text-gray-600 dark:text-gray-400">
                    <span class="flex items-center gap-1">
                      <UIcon name="i-heroicons-folder" class="w-3 h-3" />
                      {{ item.doc_type }}
                    </span>
                    <span class="flex items-center gap-1">
                      <UIcon name="i-heroicons-calendar" class="w-3 h-3" />
                      {{ item.year }}
                    </span>
                    <span
                      v-if="item.programs && item.programs.length > 0"
                      class="flex items-center gap-1"
                    >
                      <UIcon name="i-heroicons-tag" class="w-3 h-3" />
                      {{ item.programs.join(', ') }}
                    </span>
                  </div>

                  <!-- Source Text Preview -->
                  <div class="bg-white dark:bg-gray-900 rounded-md p-3 text-sm">
                    <p class="text-gray-700 dark:text-gray-300 italic">
                      "{{ truncateText(item.text, 300) }}"
                    </p>
                  </div>
                </div>
              </template>
            </UAccordion>
          </div>

          <!-- Message Actions -->
          <div class="flex items-center gap-2 mt-3">
            <!-- Copy Button -->
            <UButton
              color="neutral"
              variant="ghost"
              size="xs"
              icon="i-heroicons-clipboard-document"
              @click="copyToClipboard"
            >
              {{ copied ? 'Copied!' : 'Copy' }}
            </UButton>

            <!-- Regenerate (Assistant only) -->
            <UButton
              v-if="isAssistant"
              color="neutral"
              variant="ghost"
              size="xs"
              icon="i-heroicons-arrow-path"
              @click="$emit('regenerate')"
            >
              Regenerate
            </UButton>

            <!-- Confidence Score (Assistant only) -->
            <div
              v-if="isAssistant && metadata?.confidence"
              class="ml-auto flex items-center gap-1"
            >
              <span class="text-xs text-gray-500 dark:text-gray-400">
                Confidence:
              </span>
              <UBadge
                :color="getConfidenceColor(metadata.confidence)"
                variant="subtle"
                size="xs"
              >
                {{ (metadata.confidence * 100).toFixed(0) }}%
              </UBadge>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ChatMessage Component
 *
 * Displays individual chat messages with:
 * - Different styling for user vs assistant messages
 * - Markdown rendering for formatted content
 * - Collapsible source citations (assistant messages)
 * - Timestamp display
 * - Copy to clipboard functionality
 * - Regenerate button for assistant messages
 * - Confidence scores and metadata
 */

import type { ChatMessage, Source } from '~/types/api'
import { marked } from 'marked'
import DOMPurify from 'isomorphic-dompurify'

// Define BadgeColor type locally (Nuxt UI v4 colors)
type BadgeColor = 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'error' | 'neutral'

// ============================================================================
// Props & Emits
// ============================================================================

interface Props {
  /** The chat message to display */
  message: ChatMessage
  /** Optional sources for assistant messages */
  sources?: Source[]
}

const props = defineProps<Props>()

interface Emits {
  /** Emitted when user clicks regenerate button */
  (e: 'regenerate'): void
}

defineEmits<Emits>()

// ============================================================================
// State
// ============================================================================

const copied = ref(false)

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Check if message is from user
 */
const isUser = computed(() => props.message.role === 'user')

/**
 * Check if message is from assistant
 */
const isAssistant = computed(() => props.message.role === 'assistant')

/**
 * Get metadata from message
 */
const metadata = computed(() => props.message.metadata)

/**
 * Render markdown content as HTML
 */
const renderedContent = computed(() => {
  // Configure marked for security and features
  marked.setOptions({
    breaks: true, // Convert \n to <br>
    gfm: true, // GitHub Flavored Markdown
  })

  // Render markdown to HTML (synchronous)
  const rawHtml = marked.parse(props.message.content) as string

  // Sanitize HTML to prevent XSS
  return DOMPurify.sanitize(rawHtml)
})

/**
 * Format timestamp as relative time or absolute time
 */
const formattedTimestamp = computed(() => {
  const date = new Date(props.message.timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)

  // Within last hour: relative time
  if (diffMins < 60) {
    if (diffMins < 1) return 'Just now'
    return `${diffMins}m ago`
  }

  // Within last 24 hours: hours ago
  if (diffHours < 24) {
    return `${diffHours}h ago`
  }

  // Otherwise: formatted date and time
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  })
})

/**
 * Create accordion items from sources
 */
const accordionItems = computed(() => {
  if (!props.sources) return []

  return props.sources.map((source, index) => ({
    label: `[${index + 1}] ${source.filename}`,
    filename: source.filename,
    relevance: source.relevance_score,
    text: source.text,
    doc_type: source.doc_type,
    year: source.year,
    programs: source.programs,
    slot: 'item'
  }))
})

// ============================================================================
// Methods
// ============================================================================

/**
 * Copy message content to clipboard
 */
const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(props.message.content)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (error) {
    console.error('Failed to copy to clipboard:', error)
  }
}

/**
 * Get badge color based on confidence score
 */
const getConfidenceColor = (confidence: number): BadgeColor => {
  if (confidence >= 0.8) return 'success'
  if (confidence >= 0.6) return 'warning'
  return 'error'
}

/**
 * Truncate text to specified length
 */
const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}
</script>

<style scoped>
@reference "~/assets/css/main.css";

/* Markdown prose styling adjustments */
.prose :deep(p) {
  margin-bottom: 0.75rem;
}

.prose :deep(p:last-child) {
  margin-bottom: 0;
}

.prose :deep(ul),
.prose :deep(ol) {
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}

.prose :deep(li) {
  margin-bottom: 0.25rem;
}

.prose :deep(code) {
  @apply bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-sm;
}

.prose :deep(pre) {
  @apply bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto;
}

.prose :deep(blockquote) {
  @apply border-l-4 border-gray-300 dark:border-gray-700 pl-4 italic;
}

/* Citation links styling */
.prose :deep(a) {
  @apply text-primary-600 dark:text-primary-400 hover:underline;
}
</style>
