<template>
  <div class="document-library-filter-sidebar">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
        Filters
      </h3>
      <UButton
        v-if="hasActiveFilters"
        color="neutral"
        variant="ghost"
        size="xs"
        label="Clear all"
        @click="clearAllFilters"
      />
    </div>

    <!-- Filter Controls -->
    <div class="space-y-4">
      <!-- Document Type Filter -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Document Type
        </label>
        <USelectMenu
          v-model="localFilters.doc_types"
          :items="documentTypeOptions"
          multiple
          placeholder="Select types..."
          class="w-full"
        >
          <template #default="{ open }">
            <UButton
              :label="docTypesLabel"
              trailing-icon="i-heroicons-chevron-down"
              color="neutral"
              variant="outline"
              class="w-full justify-between"
            />
          </template>
        </USelectMenu>
      </div>

      <!-- Programs Filter -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Programs
        </label>
        <USelectMenu
          v-model="localFilters.programs"
          :items="programOptions"
          :loading="loadingPrograms"
          multiple
          placeholder="Select programs..."
          class="w-full"
        >
          <template #default="{ open }">
            <UButton
              :label="programsLabel"
              trailing-icon="i-heroicons-chevron-down"
              color="neutral"
              variant="outline"
              class="w-full justify-between"
            />
          </template>
        </USelectMenu>
      </div>

      <!-- Year Filter -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Year
        </label>
        <USelectMenu
          v-model="localFilters.years"
          :items="yearOptions"
          multiple
          placeholder="Select years..."
          class="w-full"
        >
          <template #default="{ open }">
            <UButton
              :label="yearsLabel"
              trailing-icon="i-heroicons-chevron-down"
              color="neutral"
              variant="outline"
              class="w-full justify-between"
            />
          </template>
        </USelectMenu>
      </div>

      <!-- Outcome Filter -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Outcome
        </label>
        <USelectMenu
          v-model="localFilters.outcomes"
          :items="outcomeOptions"
          multiple
          placeholder="Select outcomes..."
          class="w-full"
        >
          <template #default="{ open }">
            <UButton
              :label="outcomesLabel"
              trailing-icon="i-heroicons-chevron-down"
              color="neutral"
              variant="outline"
              class="w-full justify-between"
            />
          </template>
        </USelectMenu>
      </div>
    </div>

    <!-- Active Filters Summary -->
    <div v-if="hasActiveFilters" class="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
      <div class="text-sm text-gray-600 dark:text-gray-400">
        <span class="font-medium">Active filters: </span>
        <span>{{ activeFilterCount }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DocumentType, DocumentOutcome, DocumentFilters } from '~/types/api'

/**
 * DocumentLibrary Filter Sidebar Component
 *
 * Provides multi-select filters for the document library:
 * - Document types
 * - Programs (loaded from API)
 * - Years
 * - Outcomes
 *
 * Features:
 * - Reactive two-way binding with parent component
 * - Clear all filters functionality
 * - Active filter count display
 * - Mobile-responsive (can be used in collapsible sidebars)
 */

// ============================================================================
// Props & Emits
// ============================================================================

interface Props {
  modelValue: DocumentFilters
}

interface Emits {
  (e: 'update:modelValue', value: DocumentFilters): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// ============================================================================
// Local State
// ============================================================================

const localFilters = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const loadingPrograms = ref(false)
const programOptions = ref<string[]>([])

// ============================================================================
// Filter Options
// ============================================================================

/**
 * Document type options (from API types)
 */
const documentTypeOptions: DocumentType[] = [
  'Grant Proposal',
  'Annual Report',
  'Program Description',
  'Impact Report',
  'Strategic Plan',
  'Other'
]

/**
 * Document outcome options (from API types)
 */
const outcomeOptions: DocumentOutcome[] = [
  'N/A',
  'Funded',
  'Not Funded',
  'Pending',
  'Final Report'
]

/**
 * Year options (last 10 years + current year + next year)
 */
const yearOptions = computed(() => {
  const currentYear = new Date().getFullYear()
  const years: number[] = []
  for (let i = currentYear + 1; i >= currentYear - 10; i--) {
    years.push(i)
  }
  return years
})

// ============================================================================
// Program Loading
// ============================================================================

/**
 * Load programs from API
 * Programs are organization-specific categories for documents
 */
const loadPrograms = async () => {
  loadingPrograms.value = true
  try {
    const { apiFetch } = useApi()

    // Fetch active programs from API
    // Note: Backend should have /api/programs/active endpoint returning string[]
    const programs = await apiFetch<string[]>('/api/programs/active', {
      method: 'GET'
    })

    if (programs && Array.isArray(programs)) {
      programOptions.value = programs
    }
  } catch (error) {
    console.error('Failed to load programs:', error)
    // Fallback to empty array - user can still use other filters
    programOptions.value = []
  } finally {
    loadingPrograms.value = false
  }
}

// Load programs on mount
onMounted(() => {
  loadPrograms()
})

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Check if any filters are active
 */
const hasActiveFilters = computed(() => {
  return (
    (localFilters.value.doc_types && localFilters.value.doc_types.length > 0) ||
    (localFilters.value.programs && localFilters.value.programs.length > 0) ||
    (localFilters.value.years && localFilters.value.years.length > 0) ||
    (localFilters.value.outcomes && localFilters.value.outcomes.length > 0)
  )
})

/**
 * Count of active filter selections
 */
const activeFilterCount = computed(() => {
  let count = 0
  if (localFilters.value.doc_types) count += localFilters.value.doc_types.length
  if (localFilters.value.programs) count += localFilters.value.programs.length
  if (localFilters.value.years) count += localFilters.value.years.length
  if (localFilters.value.outcomes) count += localFilters.value.outcomes.length
  return count
})

/**
 * Label for document types filter button
 */
const docTypesLabel = computed(() => {
  if (localFilters.value.doc_types && localFilters.value.doc_types.length > 0) {
    return `${localFilters.value.doc_types.length} selected`
  }
  return 'Select types...'
})

/**
 * Label for programs filter button
 */
const programsLabel = computed(() => {
  if (localFilters.value.programs && localFilters.value.programs.length > 0) {
    return `${localFilters.value.programs.length} selected`
  }
  return 'Select programs...'
})

/**
 * Label for years filter button
 */
const yearsLabel = computed(() => {
  if (localFilters.value.years && localFilters.value.years.length > 0) {
    return `${localFilters.value.years.length} selected`
  }
  return 'Select years...'
})

/**
 * Label for outcomes filter button
 */
const outcomesLabel = computed(() => {
  if (localFilters.value.outcomes && localFilters.value.outcomes.length > 0) {
    return `${localFilters.value.outcomes.length} selected`
  }
  return 'Select outcomes...'
})

// ============================================================================
// Actions
// ============================================================================

/**
 * Clear all active filters
 */
const clearAllFilters = () => {
  emit('update:modelValue', {
    doc_types: [],
    programs: [],
    years: [],
    outcomes: []
  })
}
</script>

<style scoped>
.document-library-filter-sidebar {
  /* Component is fully responsive and works in any container */
  /* Parent component should handle sidebar width and mobile collapsing */
}
</style>
