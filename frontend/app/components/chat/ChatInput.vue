<template>
  <div class="chat-input border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
    <div class="max-w-4xl mx-auto p-4">
      <!-- Input Container -->
      <div class="relative">
        <!-- Textarea -->
        <UTextarea
          v-model="localMessage"
          :rows="1"
          :maxrows="4"
          autoresize
          :disabled="isStreaming"
          :placeholder="isStreaming ? 'Waiting for response...' : 'Type your message...'"
          class="resize-none pr-24"
          @keydown.enter.exact.prevent="handleSend"
          @keydown.enter.shift.exact="handleShiftEnter"
        />

        <!-- Send Button (positioned absolute in top-right) -->
        <div class="absolute right-2 top-2">
          <UButton
            color="primary"
            variant="solid"
            size="sm"
            icon="i-heroicons-paper-airplane"
            :disabled="!canSend"
            @click="handleSend"
          >
            Send
          </UButton>
        </div>
      </div>

      <!-- Footer Info -->
      <div class="flex items-center justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
        <!-- Keyboard Shortcuts Hint -->
        <div class="flex items-center gap-3">
          <span class="flex items-center gap-1">
            <kbd class="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700">
              Enter
            </kbd>
            <span>to send</span>
          </span>
          <span class="flex items-center gap-1">
            <kbd class="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700">
              Shift+Enter
            </kbd>
            <span>for new line</span>
          </span>
        </div>

        <!-- Word Count -->
        <div class="flex items-center gap-2">
          <span>{{ wordCount }} {{ wordCount === 1 ? 'word' : 'words' }}</span>
          <UBadge
            v-if="characterCount > 1000"
            :color="characterCount > 5000 ? 'warning' : 'info'"
            variant="subtle"
            size="xs"
          >
            {{ characterCount }} chars
          </UBadge>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ChatInput Component
 *
 * Input area for sending chat messages with:
 * - Auto-resizing textarea (max 4 rows)
 * - Send button (disabled when empty or streaming)
 * - Word count display
 * - Keyboard shortcuts (Enter to send, Shift+Enter for new line)
 * - Character count badge for long messages
 */

// ============================================================================
// Props & Emits
// ============================================================================

interface Props {
  /** Current message text (for v-model) */
  modelValue?: string
  /** Whether the assistant is currently streaming a response */
  isStreaming?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  isStreaming: false
})

interface Emits {
  /** Emitted when modelValue changes */
  (e: 'update:modelValue', value: string): void
  /** Emitted when user sends a message */
  (e: 'send', message: string): void
}

const emit = defineEmits<Emits>()

// ============================================================================
// State
// ============================================================================

/**
 * Local message state (synced with v-model)
 */
const localMessage = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value)
})

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Check if message can be sent
 * - Must have non-empty content (after trimming)
 * - Must not be streaming
 */
const canSend = computed(() => {
  return localMessage.value.trim().length > 0 && !props.isStreaming
})

/**
 * Count words in message
 */
const wordCount = computed(() => {
  const trimmed = localMessage.value.trim()
  if (trimmed.length === 0) return 0

  // Split by whitespace and filter empty strings
  return trimmed.split(/\s+/).filter(word => word.length > 0).length
})

/**
 * Count characters in message
 */
const characterCount = computed(() => {
  return localMessage.value.length
})

// ============================================================================
// Methods
// ============================================================================

/**
 * Handle send button click or Enter key
 */
const handleSend = () => {
  if (!canSend.value) return

  const message = localMessage.value.trim()
  if (message) {
    emit('send', message)
    // Clear input after sending
    localMessage.value = ''
  }
}

/**
 * Handle Shift+Enter for new line
 * This is handled automatically by preventing the Enter handler
 * and allowing the default textarea behavior
 */
const handleShiftEnter = (event: KeyboardEvent) => {
  // Allow default behavior (insert newline)
  // The prevent on the Enter handler ensures this works correctly
}
</script>

<style scoped>
/* Keyboard shortcut styling */
kbd {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 0.75rem;
  line-height: 1;
}

/* Ensure textarea has proper padding for the send button */
:deep(textarea) {
  padding-right: 7rem !important;
}
</style>
