<template>
  <UCard
    class="output-card cursor-pointer transition-all duration-200 hover:shadow-lg hover:scale-[1.02]"
    :class="{ 'ring-2 ring-primary-500': isSelected }"
    @click="handleClick"
  >
    <!-- Card Header: Title and Status Badge -->
    <template #header>
      <div class="flex items-start justify-between gap-3">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white line-clamp-2 flex-1">
          {{ output.title }}
        </h3>
        <UBadge
          :color="statusColor"
          variant="soft"
          size="sm"
          class="flex-shrink-0"
        >
          {{ statusLabel }}
        </UBadge>
      </div>
    </template>

    <!-- Card Body: Output Details -->
    <div class="space-y-3">
      <!-- Output Type -->
      <div class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
        <UIcon name="i-heroicons-document-text" class="w-4 h-4" />
        <span>{{ outputTypeLabel }}</span>
      </div>

      <!-- Word Count (if available) -->
      <div
        v-if="output.word_count"
        class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400"
      >
        <UIcon name="i-heroicons-bars-3-bottom-left" class="w-4 h-4" />
        <span>{{ formattedWordCount }}</span>
      </div>

      <!-- Funder Name (if available) -->
      <div
        v-if="output.funder_name"
        class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400"
      >
        <UIcon name="i-heroicons-building-library" class="w-4 h-4" />
        <span class="line-clamp-1">{{ output.funder_name }}</span>
      </div>

      <!-- Financial Information (if available) -->
      <div
        v-if="hasFinancialInfo"
        class="flex flex-col gap-2 pt-2 border-t border-gray-200 dark:border-gray-700"
      >
        <div
          v-if="output.requested_amount"
          class="flex items-center justify-between text-sm"
        >
          <span class="text-gray-600 dark:text-gray-400">Requested:</span>
          <span class="font-medium text-gray-900 dark:text-white">
            {{ formattedRequestedAmount }}
          </span>
        </div>
        <div
          v-if="output.awarded_amount"
          class="flex items-center justify-between text-sm"
        >
          <span class="text-gray-600 dark:text-gray-400">Awarded:</span>
          <span class="font-medium text-success-600 dark:text-success-400">
            {{ formattedAwardedAmount }}
          </span>
        </div>
      </div>
    </div>

    <!-- Card Footer: Created Date -->
    <template #footer>
      <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
        <UIcon name="i-heroicons-calendar" class="w-4 h-4" />
        <span>Created {{ formattedCreatedDate }}</span>
      </div>
    </template>
  </UCard>
</template>

<script setup lang="ts">
import type { OutputResponse, OutputStatus, OutputType } from '~/types/api'

/**
 * OutputCard Component
 *
 * A card component for displaying output information in a grid layout.
 * Shows key output details including title, status, type, funder, amounts, and dates.
 *
 * Features:
 * - Clickable card navigation to detail page
 * - Status badge with semantic colors
 * - Conditional display of financial information
 * - Formatted dates and currency
 * - Hover effects for interactivity
 * - Responsive design
 *
 * @example
 * ```vue
 * <OutputCard
 *   :output="outputData"
 *   @click="navigateTo(`/outputs/${outputData.output_id}`)"
 * />
 * ```
 */

// ============================================================================
// Props & Emits
// ============================================================================

interface Props {
  output: OutputResponse
  isSelected?: boolean
}

interface Emits {
  (e: 'click', output: OutputResponse): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// ============================================================================
// Navigation
// ============================================================================

const router = useRouter()

const handleClick = () => {
  emit('click', props.output)
  router.push(`/outputs/${props.output.output_id}`)
}

// ============================================================================
// Status Badge Formatting
// ============================================================================

/**
 * Get badge color based on output status
 */
const statusColor = computed(() => {
  const statusColorMap: Record<OutputStatus, 'success' | 'warning' | 'info' | 'error' | 'neutral'> = {
    draft: 'neutral',
    submitted: 'info',
    pending: 'warning',
    awarded: 'success',
    not_awarded: 'error',
  }
  return statusColorMap[props.output.status] || 'neutral'
})

/**
 * Get human-readable status label
 */
const statusLabel = computed(() => {
  const statusLabelMap: Record<OutputStatus, string> = {
    draft: 'Draft',
    submitted: 'Submitted',
    pending: 'Pending',
    awarded: 'Awarded',
    not_awarded: 'Not Awarded',
  }
  return statusLabelMap[props.output.status] || props.output.status
})

// ============================================================================
// Output Type Formatting
// ============================================================================

/**
 * Get human-readable output type label
 */
const outputTypeLabel = computed(() => {
  const typeLabelMap: Record<OutputType, string> = {
    grant_proposal: 'Grant Proposal',
    budget_narrative: 'Budget Narrative',
    program_description: 'Program Description',
    impact_summary: 'Impact Summary',
    other: 'Other',
  }
  return typeLabelMap[props.output.output_type] || props.output.output_type
})

// ============================================================================
// Formatting Helpers
// ============================================================================

/**
 * Format word count with commas
 */
const formattedWordCount = computed(() => {
  if (!props.output.word_count) return '0 words'
  return `${props.output.word_count.toLocaleString()} words`
})

/**
 * Format requested amount as currency
 */
const formattedRequestedAmount = computed(() => {
  if (!props.output.requested_amount) return '$0'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(props.output.requested_amount)
})

/**
 * Format awarded amount as currency
 */
const formattedAwardedAmount = computed(() => {
  if (!props.output.awarded_amount) return '$0'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(props.output.awarded_amount)
})

/**
 * Format created date as relative time
 */
const formattedCreatedDate = computed(() => {
  const date = new Date(props.output.created_at)
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  // Less than a minute
  if (diffInSeconds < 60) return 'just now'

  // Less than an hour
  if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60)
    return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`
  }

  // Less than a day
  if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600)
    return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`
  }

  // Less than a week
  if (diffInSeconds < 604800) {
    const days = Math.floor(diffInSeconds / 86400)
    return `${days} ${days === 1 ? 'day' : 'days'} ago`
  }

  // More than a week - show formatted date
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  })
})

/**
 * Check if output has financial information to display
 */
const hasFinancialInfo = computed(() => {
  return !!(props.output.requested_amount || props.output.awarded_amount)
})
</script>

<style scoped>
.output-card {
  /* Smooth hover transition */
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.output-card:hover {
  /* Slight elevation on hover */
  transform: translateY(-2px);
}

.output-card:active {
  /* Slight press effect */
  transform: translateY(0);
}
</style>
