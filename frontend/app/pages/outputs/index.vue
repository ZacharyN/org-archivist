<template>
  <div class="outputs-page">
    <!-- Page Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
          Outputs
        </h1>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Manage your saved content and grant proposals
        </p>
      </div>

      <!-- Header Actions -->
      <div class="flex items-center gap-3">
        <!-- Filter Toggle (Mobile) -->
        <UButton
          icon="i-heroicons-funnel"
          color="neutral"
          variant="outline"
          size="md"
          label="Filters"
          class="lg:hidden"
          @click="mobileFiltersOpen = !mobileFiltersOpen"
        />

        <!-- Create New Output Button -->
        <UButton
          icon="i-heroicons-plus"
          color="primary"
          variant="solid"
          size="md"
          label="New Output"
          @click="navigateTo('/outputs/create')"
        />
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="outputs-content-wrapper flex gap-6">
      <!-- Filter Sidebar (Desktop) -->
      <aside class="outputs-sidebar hidden lg:block w-64 flex-shrink-0">
        <div class="sticky top-4">
          <OutputsFilterSidebar v-model="filters" />
        </div>
      </aside>

      <!-- Mobile Filters Drawer -->
      <USlideover v-model="mobileFiltersOpen" side="left">
        <div class="p-4">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
              Filters
            </h2>
            <UButton
              icon="i-heroicons-x-mark"
              color="neutral"
              variant="ghost"
              size="sm"
              @click="mobileFiltersOpen = false"
            />
          </div>
          <OutputsFilterSidebar v-model="filters" />
        </div>
      </USlideover>

      <!-- Main Content: Grid and Pagination -->
      <main class="outputs-main flex-1 min-w-0">
        <!-- Search Bar -->
        <div class="mb-6">
          <UInput
            v-model="searchQuery"
            placeholder="Search outputs..."
            icon="i-heroicons-magnifying-glass"
            size="lg"
            class="w-full"
          />
        </div>

        <!-- Results Summary -->
        <div
          v-if="!loading && hasOutputs"
          class="mb-4 text-sm text-gray-600 dark:text-gray-400"
        >
          Showing {{ outputs.length }} of {{ totalOutputs }} outputs
        </div>

        <!-- Loading State -->
        <div
          v-if="loading"
          class="flex items-center justify-center py-12"
        >
          <div class="text-center">
            <UIcon
              name="i-heroicons-arrow-path"
              class="w-8 h-8 text-primary-500 animate-spin mx-auto mb-3"
            />
            <p class="text-sm text-gray-600 dark:text-gray-400">
              Loading outputs...
            </p>
          </div>
        </div>

        <!-- Error State -->
        <UAlert
          v-else-if="error"
          color="error"
          variant="soft"
          icon="i-heroicons-exclamation-triangle"
          :title="error.message"
          :description="error.detail"
          class="mb-6"
        >
          <template #actions>
            <UButton
              color="error"
              variant="outline"
              size="sm"
              label="Retry"
              @click="fetchOutputs"
            />
          </template>
        </UAlert>

        <!-- Empty State -->
        <div
          v-else-if="!hasOutputs"
          class="flex flex-col items-center justify-center py-12"
        >
          <UIcon
            name="i-heroicons-document-text"
            class="w-16 h-16 text-gray-400 dark:text-gray-600 mb-4"
          />
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            No outputs found
          </h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-6 text-center max-w-md">
            {{ hasActiveFilters ? 'Try adjusting your filters or search query.' : 'Get started by creating your first output.' }}
          </p>
          <UButton
            v-if="hasActiveFilters"
            color="neutral"
            variant="outline"
            size="md"
            label="Clear Filters"
            @click="clearFilters"
          />
          <UButton
            v-else
            icon="i-heroicons-plus"
            color="primary"
            variant="solid"
            size="md"
            label="Create First Output"
            @click="navigateTo('/outputs/create')"
          />
        </div>

        <!-- Outputs Grid -->
        <div
          v-else
          class="outputs-grid grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
        >
          <OutputCard
            v-for="output in outputs"
            :key="output.output_id"
            :output="output"
          />
        </div>

        <!-- Pagination -->
        <div
          v-if="!loading && hasOutputs && totalPages > 1"
          class="mt-8 flex items-center justify-between"
        >
          <div class="text-sm text-gray-600 dark:text-gray-400">
            Page {{ currentPage }} of {{ totalPages }}
          </div>

          <div class="flex items-center gap-2">
            <UButton
              icon="i-heroicons-chevron-left"
              color="neutral"
              variant="outline"
              size="sm"
              :disabled="!hasPreviousPage"
              @click="goToPreviousPage"
            />

            <!-- Page Numbers (show 5 pages max) -->
            <div class="hidden sm:flex items-center gap-1">
              <UButton
                v-for="page in visiblePages"
                :key="page"
                :label="page.toString()"
                :color="page === currentPage ? 'primary' : 'neutral'"
                :variant="page === currentPage ? 'solid' : 'ghost'"
                size="sm"
                @click="goToPage(page)"
              />
            </div>

            <UButton
              icon="i-heroicons-chevron-right"
              color="neutral"
              variant="outline"
              size="sm"
              :disabled="!hasNextPage"
              @click="goToNextPage"
            />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { OutputFilters } from '~/composables/useOutputs'

/**
 * Outputs Index Page
 *
 * Main page for viewing and managing outputs in a responsive grid layout.
 *
 * Features:
 * - Responsive grid (1 column mobile, 2 columns tablet, 3 columns desktop)
 * - Filter sidebar (collapsible on mobile)
 * - Search functionality
 * - Pagination
 * - Loading and error states
 * - Empty state with call-to-action
 *
 * Layout:
 * - Desktop: Filter sidebar (left) + Grid (right)
 * - Mobile: Full-width grid with filter drawer
 */

// ============================================================================
// Meta & SEO
// ============================================================================

definePageMeta({
  title: 'Outputs',
  description: 'Manage your saved content and grant proposals',
})

// ============================================================================
// Composables
// ============================================================================

const {
  outputs,
  pagination,
  loading,
  error,
  hasOutputs,
  totalOutputs,
  hasNextPage,
  hasPreviousPage,
  currentPage,
  totalPages,
  getOutputs,
} = useOutputs()

// ============================================================================
// State Management
// ============================================================================

/**
 * Filter state (two-way binding with sidebar)
 */
const filters = ref<OutputFilters>({
  output_types: undefined,
  statuses: undefined,
  writing_style_ids: undefined,
  funder_names: undefined,
  date_from: undefined,
  date_to: undefined,
})

/**
 * Search query state
 */
const searchQuery = ref('')

/**
 * Mobile filters drawer state
 */
const mobileFiltersOpen = ref(false)

/**
 * Current page number for pagination
 */
const page = ref(1)

/**
 * Items per page
 */
const perPage = ref(25)

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Check if any filters are active
 */
const hasActiveFilters = computed(() => {
  return (
    (filters.value.output_types && filters.value.output_types.length > 0) ||
    (filters.value.statuses && filters.value.statuses.length > 0) ||
    (filters.value.writing_style_ids && filters.value.writing_style_ids.length > 0) ||
    (filters.value.funder_names && filters.value.funder_names.length > 0) ||
    !!filters.value.date_from ||
    !!filters.value.date_to ||
    !!searchQuery.value
  )
})

/**
 * Calculate visible page numbers for pagination
 * Shows up to 5 page numbers centered around current page
 */
const visiblePages = computed(() => {
  const pages: number[] = []
  const maxVisible = 5
  const half = Math.floor(maxVisible / 2)

  let start = Math.max(1, currentPage.value - half)
  let end = Math.min(totalPages.value, start + maxVisible - 1)

  // Adjust start if we're near the end
  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1)
  }

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  return pages
})

// ============================================================================
// Data Fetching
// ============================================================================

/**
 * Fetch outputs with current filters and pagination
 */
const fetchOutputs = async () => {
  await getOutputs({
    page: page.value,
    per_page: perPage.value,
    search: searchQuery.value || undefined,
    filters: filters.value,
    sort_by: 'created_at',
    sort_order: 'desc',
  })
}

/**
 * Debounced search to avoid excessive API calls
 */
let searchTimeout: ReturnType<typeof setTimeout> | null = null

watch(searchQuery, (newValue) => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }

  searchTimeout = setTimeout(() => {
    page.value = 1 // Reset to first page on search
    fetchOutputs()
  }, 300)
})

/**
 * Watch filters and re-fetch when they change
 */
watch(
  filters,
  () => {
    page.value = 1 // Reset to first page on filter change
    fetchOutputs()
  },
  { deep: true }
)

// ============================================================================
// Pagination Actions
// ============================================================================

/**
 * Go to previous page
 */
const goToPreviousPage = () => {
  if (hasPreviousPage.value) {
    page.value--
    fetchOutputs()
  }
}

/**
 * Go to next page
 */
const goToNextPage = () => {
  if (hasNextPage.value) {
    page.value++
    fetchOutputs()
  }
}

/**
 * Go to specific page
 */
const goToPage = (pageNumber: number) => {
  if (pageNumber >= 1 && pageNumber <= totalPages.value) {
    page.value = pageNumber
    fetchOutputs()
  }
}

// ============================================================================
// Filter Actions
// ============================================================================

/**
 * Clear all filters and search
 */
const clearFilters = () => {
  filters.value = {
    output_types: undefined,
    statuses: undefined,
    writing_style_ids: undefined,
    funder_names: undefined,
    date_from: undefined,
    date_to: undefined,
  }
  searchQuery.value = ''
  page.value = 1
  fetchOutputs()
}

// ============================================================================
// Lifecycle
// ============================================================================

/**
 * Fetch outputs on mount
 */
onMounted(() => {
  fetchOutputs()
})
</script>

<style scoped>
.outputs-page {
  /* Full height container */
  min-height: calc(100vh - 4rem);
}

.outputs-content-wrapper {
  /* Ensure proper layout */
  align-items: flex-start;
}

.outputs-grid {
  /* Smooth grid transitions */
  transition: all 0.3s ease;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .outputs-grid {
    gap: 1rem;
  }
}

/* Pagination hover effects */
.outputs-page button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.outputs-page button:active:not(:disabled) {
  transform: translateY(0);
}
</style>
