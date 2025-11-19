<template>
  <div class="context-panel h-full flex flex-col bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800">
    <!-- Header -->
    <div class="p-4 border-b border-gray-200 dark:border-gray-800">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Context Settings
        </h2>
        <UButton
          color="neutral"
          variant="ghost"
          size="xs"
          icon="i-heroicons-arrow-path"
          @click="resetContext"
        >
          Reset
        </UButton>
      </div>
    </div>

    <!-- Scrollable Content -->
    <div class="flex-1 overflow-y-auto p-4 space-y-6">
      <!-- Context Settings Section -->
      <section>
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          Generation Settings
        </h3>
        <div class="space-y-4">
          <!-- Writing Style -->
          <UFormField
            label="Writing Style"
            name="writing_style"
            help="Select a pre-defined writing style"
          >
            <USelectMenu
              v-model="localContext.writing_style_id"
              :options="writingStyleOptions"
              placeholder="Select style..."
              value-attribute="value"
              :loading="loadingStyles"
            >
              <template #default="{ open }">
                <UButton
                  :label="selectedStyleLabel"
                  trailing-icon="i-heroicons-chevron-down"
                  color="neutral"
                  variant="outline"
                  class="w-full justify-between"
                />
              </template>
            </USelectMenu>
          </UFormField>

          <!-- Audience -->
          <UFormField
            label="Target Audience"
            name="audience"
            help="Who will read this content?"
          >
            <UInput
              v-model="localContext.audience"
              placeholder="e.g., Foundation board members"
            />
          </UFormField>

          <!-- Section -->
          <UFormField
            label="Section/Purpose"
            name="section"
            help="What section or purpose?"
          >
            <UInput
              v-model="localContext.section"
              placeholder="e.g., Project description"
            />
          </UFormField>

          <!-- Tone Slider -->
          <UFormField
            label="Tone"
            name="tone"
            :help="`${toneLabel} (${toneValue}%)`"
          >
            <URange
              v-model="toneValue"
              :min="0"
              :max="100"
              :step="10"
              class="mt-2"
            />
            <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
              <span>Formal</span>
              <span>Balanced</span>
              <span>Casual</span>
            </div>
          </UFormField>
        </div>
      </section>

      <!-- Document Filters Section -->
      <section>
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
          Document Filters
        </h3>
        <div class="space-y-4">
          <!-- Programs Filter -->
          <UFormField
            label="Programs"
            name="programs"
            help="Filter by program(s)"
          >
            <USelectMenu
              v-model="selectedPrograms"
              :options="programOptions"
              multiple
              searchable
              placeholder="Select programs..."
            >
              <template #default="{ open }">
                <UButton
                  :label="selectedProgramsLabel"
                  trailing-icon="i-heroicons-chevron-down"
                  color="neutral"
                  variant="outline"
                  class="w-full justify-between"
                />
              </template>
            </USelectMenu>
          </UFormField>

          <!-- Document Types Filter -->
          <UFormField
            label="Document Types"
            name="doc_types"
            help="Filter by document type(s)"
          >
            <USelectMenu
              v-model="selectedDocTypes"
              :options="docTypeOptions"
              multiple
              searchable
              placeholder="Select types..."
            >
              <template #default="{ open }">
                <UButton
                  :label="selectedDocTypesLabel"
                  trailing-icon="i-heroicons-chevron-down"
                  color="neutral"
                  variant="outline"
                  class="w-full justify-between"
                />
              </template>
            </USelectMenu>
          </UFormField>

          <!-- Years Filter -->
          <UFormField
            label="Years"
            name="years"
            help="Filter by year(s)"
          >
            <USelectMenu
              v-model="selectedYears"
              :options="yearOptions"
              multiple
              searchable
              placeholder="Select years..."
            >
              <template #default="{ open }">
                <UButton
                  :label="selectedYearsLabel"
                  trailing-icon="i-heroicons-chevron-down"
                  color="neutral"
                  variant="outline"
                  class="w-full justify-between"
                />
              </template>
            </USelectMenu>
          </UFormField>
        </div>
      </section>

      <!-- Active Sources Section -->
      <section v-if="sources && sources.length > 0">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">
            Active Sources
          </h3>
          <UBadge color="info" variant="subtle" size="xs">
            {{ sources.length }}
          </UBadge>
        </div>

        <!-- Sources List -->
        <div class="space-y-2">
          <div
            v-for="(source, index) in sortedSources"
            :key="`${source.doc_id}-${source.chunk_id}`"
            class="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700"
          >
            <!-- Source Header -->
            <div class="flex items-start justify-between gap-2 mb-2">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <UIcon
                    name="i-heroicons-document-text"
                    class="w-4 h-4 text-gray-400 flex-shrink-0"
                  />
                  <span class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                    {{ source.filename }}
                  </span>
                </div>
                <div class="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-gray-400">
                  <span>{{ source.doc_type }}</span>
                  <span>•</span>
                  <span>{{ source.year }}</span>
                  <span v-if="source.programs.length > 0">•</span>
                  <span v-if="source.programs.length > 0">
                    {{ source.programs.join(', ') }}
                  </span>
                </div>
              </div>

              <!-- Relevance Score Badge -->
              <UBadge
                :color="getRelevanceColor(source.relevance_score)"
                variant="subtle"
                size="xs"
              >
                {{ (source.relevance_score * 100).toFixed(0) }}%
              </UBadge>
            </div>

            <!-- Source Text Preview -->
            <p class="text-xs text-gray-600 dark:text-gray-400 italic line-clamp-2">
              "{{ source.text }}"
            </p>
          </div>
        </div>
      </section>

      <!-- Empty State for Sources -->
      <section v-else-if="sources && sources.length === 0">
        <div class="text-center py-8">
          <UIcon
            name="i-heroicons-document-magnifying-glass"
            class="w-12 h-12 mx-auto text-gray-400 mb-2"
          />
          <p class="text-sm text-gray-500 dark:text-gray-400">
            No sources yet
          </p>
          <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
            Sources will appear after generating content
          </p>
        </div>
      </section>
    </div>

    <!-- Footer Actions -->
    <div class="p-4 border-t border-gray-200 dark:border-gray-800">
      <UButton
        color="primary"
        variant="solid"
        block
        @click="applyContext"
      >
        Apply Settings
      </UButton>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ContextPanel Component
 *
 * Right sidebar for chat interface with:
 * - Context settings (writing style, audience, section, tone)
 * - Document filters (programs, doc types, years)
 * - Active sources list with relevance scores
 */

import type {
  ConversationContext,
  WritingStyle,
  DocumentType,
  Source
} from '~/types/api'

// Define BadgeColor type locally (Nuxt UI v4 colors)
type BadgeColor = 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'error' | 'neutral'

// ============================================================================
// Props & Emits
// ============================================================================

interface Props {
  /** Current conversation context */
  context?: ConversationContext
  /** Sources from last generation */
  sources?: Source[]
  /** Available programs for filtering */
  programs?: string[]
  /** Available writing styles */
  writingStyles?: WritingStyle[]
}

const props = withDefaults(defineProps<Props>(), {
  context: undefined,
  sources: undefined,
  programs: () => [],
  writingStyles: () => []
})

interface Emits {
  /** Emitted when user applies context changes */
  (e: 'update:context', context: ConversationContext): void
}

const emit = defineEmits<Emits>()

// ============================================================================
// State
// ============================================================================

/**
 * Local context state (editable copy)
 */
const localContext = ref<ConversationContext>({
  writing_style_id: props.context?.writing_style_id,
  audience: props.context?.audience || '',
  section: props.context?.section || '',
  tone: props.context?.tone || 'balanced',
  filters: props.context?.filters || {}
})

/**
 * Tone slider value (0-100)
 */
const toneValue = ref(50)

/**
 * Selected programs for filters
 */
const selectedPrograms = ref<string[]>(props.context?.filters?.programs || [])

/**
 * Selected document types for filters
 */
const selectedDocTypes = ref<DocumentType[]>(props.context?.filters?.doc_types || [])

/**
 * Selected years for filters
 */
const selectedYears = ref<number[]>(props.context?.filters?.years || [])

/**
 * Loading state for writing styles
 */
const loadingStyles = ref(false)

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Writing style options for select menu
 */
const writingStyleOptions = computed(() => {
  return props.writingStyles
    .filter(style => style.active)
    .map(style => ({
      label: style.name,
      value: style.style_id,
      description: style.description
    }))
})

/**
 * Selected writing style label
 */
const selectedStyleLabel = computed(() => {
  if (!localContext.value.writing_style_id) return 'Select style...'

  const selected = props.writingStyles.find(
    s => s.style_id === localContext.value.writing_style_id
  )
  return selected?.name || 'Select style...'
})

/**
 * Program options for select menu
 */
const programOptions = computed(() => {
  return props.programs.map(program => ({
    label: program,
    value: program
  }))
})

/**
 * Document type options for select menu
 */
const docTypeOptions = computed(() => {
  const types: DocumentType[] = [
    'Grant Proposal',
    'Annual Report',
    'Program Description',
    'Impact Report',
    'Strategic Plan',
    'Other'
  ]
  return types.map(type => ({
    label: type,
    value: type
  }))
})

/**
 * Year options (last 10 years)
 */
const yearOptions = computed(() => {
  const currentYear = new Date().getFullYear()
  const years: number[] = []
  for (let i = 0; i < 10; i++) {
    years.push(currentYear - i)
  }
  return years.map(year => ({
    label: year.toString(),
    value: year
  }))
})

/**
 * Tone label based on slider value
 */
const toneLabel = computed(() => {
  if (toneValue.value <= 30) return 'Formal'
  if (toneValue.value <= 70) return 'Balanced'
  return 'Casual'
})

/**
 * Selected programs display label
 */
const selectedProgramsLabel = computed(() => {
  if (selectedPrograms.value.length === 0) return 'All programs'
  if (selectedPrograms.value.length === 1) return selectedPrograms.value[0]
  return `${selectedPrograms.value.length} programs`
})

/**
 * Selected doc types display label
 */
const selectedDocTypesLabel = computed(() => {
  if (selectedDocTypes.value.length === 0) return 'All types'
  if (selectedDocTypes.value.length === 1) return selectedDocTypes.value[0]
  return `${selectedDocTypes.value.length} types`
})

/**
 * Selected years display label
 */
const selectedYearsLabel = computed(() => {
  if (selectedYears.value.length === 0) return 'All years'
  if (selectedYears.value.length === 1) return selectedYears.value[0]?.toString() || 'All years'
  return `${selectedYears.value.length} years`
})

/**
 * Sort sources by relevance score (highest first)
 */
const sortedSources = computed(() => {
  if (!props.sources) return []
  return [...props.sources].sort((a, b) => b.relevance_score - a.relevance_score)
})

// ============================================================================
// Watchers
// ============================================================================

/**
 * Update local context when prop changes
 */
watch(() => props.context, (newContext) => {
  if (newContext) {
    localContext.value = {
      writing_style_id: newContext.writing_style_id,
      audience: newContext.audience || '',
      section: newContext.section || '',
      tone: newContext.tone || 'balanced',
      filters: newContext.filters || {}
    }

    // Update filter selections
    selectedPrograms.value = newContext.filters?.programs || []
    selectedDocTypes.value = newContext.filters?.doc_types || []
    selectedYears.value = newContext.filters?.years || []
  }
}, { deep: true })

/**
 * Update tone string based on slider value
 */
watch(toneValue, (newValue) => {
  if (newValue <= 30) {
    localContext.value.tone = 'formal'
  } else if (newValue <= 70) {
    localContext.value.tone = 'balanced'
  } else {
    localContext.value.tone = 'casual'
  }
})

// ============================================================================
// Methods
// ============================================================================

/**
 * Apply context changes and emit to parent
 */
const applyContext = () => {
  // Update filters
  localContext.value.filters = {
    programs: selectedPrograms.value.length > 0 ? selectedPrograms.value : undefined,
    doc_types: selectedDocTypes.value.length > 0 ? selectedDocTypes.value : undefined,
    years: selectedYears.value.length > 0 ? selectedYears.value : undefined
  }

  emit('update:context', localContext.value)
}

/**
 * Reset context to default values
 */
const resetContext = () => {
  localContext.value = {
    writing_style_id: undefined,
    audience: '',
    section: '',
    tone: 'balanced',
    filters: {}
  }
  toneValue.value = 50
  selectedPrograms.value = []
  selectedDocTypes.value = []
  selectedYears.value = []
}

/**
 * Get badge color based on relevance score
 */
const getRelevanceColor = (score: number): BadgeColor => {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'info'
  if (score >= 0.4) return 'warning'
  return 'neutral'
}
</script>

<style scoped>
@reference "~/assets/css/main.css";

/* Custom scrollbar styling */
.context-panel ::-webkit-scrollbar {
  width: 8px;
}

.context-panel ::-webkit-scrollbar-track {
  @apply bg-gray-100 dark:bg-gray-800;
}

.context-panel ::-webkit-scrollbar-thumb {
  @apply bg-gray-300 dark:bg-gray-600 rounded;
}

.context-panel ::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-400 dark:bg-gray-500;
}
</style>
