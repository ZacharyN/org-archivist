<template>
  <UCard>
    <template #header>
      <div class="flex items-center gap-2">
        <UIcon name="i-heroicons-clipboard-document-check" class="w-6 h-6" />
        <h2 class="text-xl font-semibold">Setup Progress</h2>
      </div>
    </template>

    <div class="space-y-3">
      <!-- Documents Checklist Item -->
      <div
        class="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer"
        @click="navigateTo('/documents')"
      >
        <div class="flex-shrink-0">
          <div
            :class="[
              'w-8 h-8 rounded-full flex items-center justify-center',
              documentsCount > 0
                ? 'bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-400'
            ]"
          >
            <UIcon
              :name="documentsCount > 0 ? 'i-heroicons-check' : 'i-heroicons-document-text'"
              class="w-5 h-5"
            />
          </div>
        </div>

        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between gap-2">
            <h3 class="font-medium text-gray-900 dark:text-white">
              Upload Documents
            </h3>
            <span
              :class="[
                'text-sm font-semibold px-2 py-0.5 rounded-full',
                documentsCount > 0
                  ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-500'
              ]"
            >
              {{ documentsCount }}
            </span>
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
            {{ documentsCount > 0 ? `${documentsCount} document${documentsCount !== 1 ? 's' : ''} uploaded` : 'Add your organization\'s documents' }}
          </p>
        </div>

        <div class="flex-shrink-0">
          <UIcon name="i-heroicons-arrow-right" class="w-5 h-5 text-gray-400" />
        </div>
      </div>

      <!-- Writing Styles Checklist Item -->
      <div
        class="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer"
        @click="navigateTo('/writing-styles')"
      >
        <div class="flex-shrink-0">
          <div
            :class="[
              'w-8 h-8 rounded-full flex items-center justify-center',
              writingStylesCount > 0
                ? 'bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-400'
            ]"
          >
            <UIcon
              :name="writingStylesCount > 0 ? 'i-heroicons-check' : 'i-heroicons-pencil-square'"
              class="w-5 h-5"
            />
          </div>
        </div>

        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between gap-2">
            <h3 class="font-medium text-gray-900 dark:text-white">
              Create Writing Styles
            </h3>
            <span
              :class="[
                'text-sm font-semibold px-2 py-0.5 rounded-full',
                writingStylesCount > 0
                  ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-500'
              ]"
            >
              {{ writingStylesCount }}
            </span>
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
            {{ writingStylesCount > 0 ? `${writingStylesCount} writing style${writingStylesCount !== 1 ? 's' : ''} configured` : 'Define your organization\'s voice' }}
          </p>
        </div>

        <div class="flex-shrink-0">
          <UIcon name="i-heroicons-arrow-right" class="w-5 h-5 text-gray-400" />
        </div>
      </div>

      <!-- Programs Checklist Item -->
      <div
        class="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer"
        @click="navigateTo('/programs')"
      >
        <div class="flex-shrink-0">
          <div
            :class="[
              'w-8 h-8 rounded-full flex items-center justify-center',
              programsCount > 0
                ? 'bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-400'
            ]"
          >
            <UIcon
              :name="programsCount > 0 ? 'i-heroicons-check' : 'i-heroicons-briefcase'"
              class="w-5 h-5"
            />
          </div>
        </div>

        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between gap-2">
            <h3 class="font-medium text-gray-900 dark:text-white">
              Configure Programs
            </h3>
            <span
              :class="[
                'text-sm font-semibold px-2 py-0.5 rounded-full',
                programsCount > 0
                  ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-500'
              ]"
            >
              {{ programsCount }}
            </span>
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
            {{ programsCount > 0 ? `${programsCount} program${programsCount !== 1 ? 's' : ''} set up` : 'Add your organization\'s programs' }}
          </p>
        </div>

        <div class="flex-shrink-0">
          <UIcon name="i-heroicons-arrow-right" class="w-5 h-5 text-gray-400" />
        </div>
      </div>

      <!-- Overall Progress Bar -->
      <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
            Overall Progress
          </span>
          <span class="text-sm font-semibold text-gray-900 dark:text-white">
            {{ completionPercentage }}%
          </span>
        </div>
        <UProgress
          :value="completionPercentage"
          :color="completionPercentage === 100 ? 'success' : 'primary'"
          size="sm"
        />
        <p v-if="completionPercentage === 100" class="text-xs text-green-600 dark:text-green-400 mt-2 flex items-center gap-1">
          <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
          Setup complete! You're ready to start using the AI assistant.
        </p>
      </div>
    </div>

    <template v-if="isLoading" #footer>
      <div class="flex items-center gap-2 text-sm text-gray-500">
        <UIcon name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
        <span>Loading setup status...</span>
      </div>
    </template>
  </UCard>
</template>

<script setup lang="ts">
/**
 * SetupChecklist Dashboard Widget
 *
 * Displays organization setup progress with checklist items for:
 * - Documents uploaded
 * - Writing styles created
 * - Programs configured
 *
 * Each item shows count, completion status, and links to relevant page.
 */

import type { DocumentResponse, WritingStyle, ProgramResponse } from '~/types/api'

// ============================================================================
// State Management
// ============================================================================

// Counts for each setup item
const documentsCount = ref(0)
const writingStylesCount = ref(0)
const programsCount = ref(0)

// Loading state
const isLoading = ref(true)

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Calculate overall completion percentage
 * Each item is worth 33.33% of total progress
 */
const completionPercentage = computed(() => {
  let completed = 0
  if (documentsCount.value > 0) completed++
  if (writingStylesCount.value > 0) completed++
  if (programsCount.value > 0) completed++

  return Math.round((completed / 3) * 100)
})

// ============================================================================
// Data Fetching
// ============================================================================

/**
 * Fetch documents count
 */
const fetchDocumentsCount = async () => {
  try {
    const { apiFetch } = useApi()

    const response = await apiFetch<DocumentResponse[]>('/api/documents', {
      params: {
        limit: 1 // We only need the count, not the data
      }
    })

    // In a real API, this would return pagination metadata with total count
    // For now, we'll assume the response includes a count or we get all docs
    if (Array.isArray(response)) {
      documentsCount.value = response.length
    }
  } catch (error) {
    console.error('Failed to fetch documents count:', error)
    // Set to 0 on error - non-critical for dashboard widget
    documentsCount.value = 0
  }
}

/**
 * Fetch writing styles count
 */
const fetchWritingStylesCount = async () => {
  try {
    const { apiFetch } = useApi()

    const response = await apiFetch<WritingStyle[]>('/api/writing-styles', {
      params: {
        active: true
      }
    })

    if (Array.isArray(response)) {
      writingStylesCount.value = response.length
    }
  } catch (error) {
    console.error('Failed to fetch writing styles count:', error)
    writingStylesCount.value = 0
  }
}

/**
 * Fetch programs count
 */
const fetchProgramsCount = async () => {
  try {
    const { apiFetch } = useApi()

    const response = await apiFetch<ProgramResponse[]>('/api/programs', {
      params: {
        is_active: true
      }
    })

    if (Array.isArray(response)) {
      programsCount.value = response.length
    }
  } catch (error) {
    console.error('Failed to fetch programs count:', error)
    programsCount.value = 0
  }
}

/**
 * Fetch all setup data
 */
const fetchSetupData = async () => {
  isLoading.value = true

  try {
    // Fetch all counts in parallel
    await Promise.all([
      fetchDocumentsCount(),
      fetchWritingStylesCount(),
      fetchProgramsCount()
    ])
  } finally {
    isLoading.value = false
  }
}

// ============================================================================
// Lifecycle Hooks
// ============================================================================

/**
 * Fetch data on component mount
 */
onMounted(() => {
  fetchSetupData()
})
</script>
