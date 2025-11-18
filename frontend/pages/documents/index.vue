<template>
  <div class="document-library-page h-screen flex flex-col">
    <!-- Page Header -->
    <div class="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
      <div class="px-6 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <UIcon name="i-heroicons-document-text" class="text-2xl text-primary" />
            <div>
              <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
                Document Library
              </h1>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                {{ totalDocuments }} documents
                <span v-if="hasActiveFilters" class="text-primary">
                  ({{ documents.length }} filtered)
                </span>
              </p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <!-- Mobile Filter Toggle -->
            <UButton
              color="neutral"
              variant="outline"
              icon="i-heroicons-adjustments-horizontal"
              class="lg:hidden"
              @click="mobileFilterOpen = !mobileFilterOpen"
            >
              Filters
              <UBadge v-if="activeFilterCount > 0" color="primary" size="xs" class="ml-2">
                {{ activeFilterCount }}
              </UBadge>
            </UButton>

            <!-- Upload Button (Admin/Editor only) -->
            <UButton
              v-if="canEdit"
              color="primary"
              icon="i-heroicons-arrow-up-tray"
              to="/documents/upload"
            >
              Upload Documents
            </UButton>
          </div>
        </div>

        <!-- Search Bar -->
        <div class="mt-4">
          <UInput
            v-model="searchQuery"
            icon="i-heroicons-magnifying-glass"
            placeholder="Search documents by filename or content..."
            size="lg"
            :loading="loading"
            @update:model-value="debouncedSearch"
          />
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Filter Sidebar (Desktop) -->
      <aside class="hidden lg:block w-64 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-y-auto">
        <div class="p-6">
          <DocumentLibraryFilterSidebar
            v-model="filters"
            @update:model-value="handleFilterChange"
          />
        </div>
      </aside>

      <!-- Mobile Filter Sidebar (Slide-over) -->
      <USlideover v-model="mobileFilterOpen" side="left">
        <div class="p-6">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold">Filters</h2>
            <UButton
              color="neutral"
              variant="ghost"
              icon="i-heroicons-x-mark"
              @click="mobileFilterOpen = false"
            />
          </div>
          <DocumentLibraryFilterSidebar
            v-model="filters"
            @update:model-value="handleFilterChange"
          />
        </div>
      </USlideover>

      <!-- Documents List -->
      <main class="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-950">
        <div class="p-6">
          <!-- Loading State -->
          <div v-if="loading && !documents.length" class="flex items-center justify-center py-12">
            <div class="text-center">
              <UIcon name="i-heroicons-arrow-path" class="text-4xl text-gray-400 animate-spin" />
              <p class="mt-2 text-sm text-gray-500">Loading documents...</p>
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
            class="mb-4"
          />

          <!-- Empty State -->
          <div v-else-if="!documents.length" class="flex items-center justify-center py-12">
            <div class="text-center max-w-md">
              <UIcon name="i-heroicons-document-text" class="text-6xl text-gray-300 dark:text-gray-700 mb-4" />
              <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                No documents found
              </h3>
              <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">
                {{ hasActiveFilters || searchQuery
                  ? 'Try adjusting your filters or search query.'
                  : 'Get started by uploading your first document.' }}
              </p>
              <UButton
                v-if="canEdit && !hasActiveFilters && !searchQuery"
                color="primary"
                icon="i-heroicons-arrow-up-tray"
                to="/documents/upload"
              >
                Upload Document
              </UButton>
              <UButton
                v-else-if="hasActiveFilters || searchQuery"
                color="neutral"
                variant="outline"
                @click="clearAllFiltersAndSearch"
              >
                Clear Filters
              </UButton>
            </div>
          </div>

          <!-- Documents Table -->
          <div v-else>
            <UTable :data="documents" :columns="columns" class="w-full">
              <!-- Filename Cell -->
              <template #filename-cell="{ row }">
                <div class="flex items-center gap-2 min-w-0">
                  <UIcon
                    :name="getDocumentTypeIcon(row.original.metadata.doc_type)"
                    class="text-lg text-gray-400 flex-shrink-0"
                  />
                  <span class="font-medium text-gray-900 dark:text-white truncate">
                    {{ row.original.filename }}
                  </span>
                </div>
              </template>

              <!-- Document Type Cell -->
              <template #doc_type-cell="{ row }">
                <UBadge color="primary" variant="soft" size="xs">
                  {{ row.original.metadata.doc_type }}
                </UBadge>
              </template>

              <!-- Programs Cell - Max 3 badges + "N more" -->
              <template #programs-cell="{ row }">
                <div v-if="row.original.metadata.programs.length > 0" class="flex flex-wrap gap-1">
                  <UBadge
                    v-for="program in row.original.metadata.programs.slice(0, 3)"
                    :key="program"
                    color="info"
                    variant="soft"
                    size="xs"
                  >
                    {{ program }}
                  </UBadge>
                  <UBadge
                    v-if="row.original.metadata.programs.length > 3"
                    color="neutral"
                    variant="soft"
                    size="xs"
                  >
                    +{{ row.original.metadata.programs.length - 3 }} more
                  </UBadge>
                </div>
                <span v-else class="text-sm text-gray-400">—</span>
              </template>

              <!-- Year Cell -->
              <template #year-cell="{ row }">
                <span class="text-sm text-gray-700 dark:text-gray-300">
                  {{ row.original.metadata.year }}
                </span>
              </template>

              <!-- Outcome Cell - Color-coded -->
              <template #outcome-cell="{ row }">
                <UBadge
                  v-if="row.original.metadata.outcome !== 'N/A'"
                  :color="getOutcomeColor(row.original.metadata.outcome)"
                  variant="soft"
                  size="xs"
                >
                  {{ row.original.metadata.outcome }}
                </UBadge>
                <span v-else class="text-sm text-gray-400">N/A</span>
              </template>

              <!-- Upload Date Cell -->
              <template #upload_date-cell="{ row }">
                <span class="text-sm text-gray-600 dark:text-gray-400">
                  {{ formatDate(row.original.upload_date) }}
                </span>
              </template>

              <!-- Actions Cell - Dropdown Menu -->
              <template #actions-cell="{ row }">
                <UDropdownMenu :items="getDropdownActions(row.original)">
                  <UButton
                    icon="i-heroicons-ellipsis-vertical"
                    color="neutral"
                    variant="ghost"
                    size="sm"
                    aria-label="Actions"
                  />
                </UDropdownMenu>
              </template>
            </UTable>

            <!-- Pagination Controls -->
            <div v-if="pagination" class="flex flex-col sm:flex-row items-center justify-between gap-4 mt-6">
              <!-- Page Size Selector -->
              <div class="flex items-center gap-2">
                <span class="text-sm text-gray-600 dark:text-gray-400">Show:</span>
                <USelectMenu
                  v-model="pageSize"
                  :items="pageSizeOptions"
                  value-key="value"
                  class="w-36"
                />
              </div>

              <!-- Pagination -->
              <div v-if="totalPages > 1">
                <UPagination
                  v-model="localCurrentPage"
                  :total="totalDocuments"
                  :page-count="pagination.per_page"
                  show-first
                  show-last
                />
              </div>

              <!-- Results Info -->
              <div class="text-sm text-gray-600 dark:text-gray-400">
                Showing {{ ((localCurrentPage - 1) * pageSize) + 1 }} to
                {{ Math.min(localCurrentPage * pageSize, totalDocuments) }} of
                {{ totalDocuments }} results
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DocumentResponse, DocumentType, DocumentOutcome, DocumentFilters } from '~/types/api'
import type { TableColumn, DropdownMenuItem } from '@nuxt/ui'

// Define BadgeColor type based on Nuxt UI color tokens
type BadgeColor = 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'error' | 'neutral'

/**
 * Document Library Page
 *
 * Main page for browsing and managing documents in the Org Archivist system.
 *
 * Features:
 * - Filter sidebar for doc types, programs, years, outcomes
 * - Search functionality
 * - UTable with custom cell rendering
 * - Pagination
 * - Document actions (view, delete) via dropdown
 * - Upload button for admin/editor roles
 *
 * Access Control:
 * - All roles can view documents
 * - Admin and Editor can upload/delete documents
 */

// ============================================================================
// Page Configuration
// ============================================================================

definePageMeta({
  middleware: 'auth',
  layout: 'default'
})

useHead({
  title: 'Document Library - Org Archivist',
  meta: [
    {
      name: 'description',
      content: 'Browse and manage organizational documents for AI-powered grant writing.'
    }
  ]
})

// ============================================================================
// Composables
// ============================================================================

const { user, canEdit } = useAuth()
const {
  documents,
  pagination,
  loading,
  error,
  getDocuments,
  deleteDocument,
  totalDocuments,
  totalPages
} = useDocuments()

// ============================================================================
// State
// ============================================================================

// Local page state (can't use currentPage from composable as it's readonly computed)
const localCurrentPage = ref(1)

const filters = ref<DocumentFilters>({
  doc_types: [],
  programs: [],
  years: [],
  outcomes: []
})

const searchQuery = ref('')
const mobileFilterOpen = ref(false)
const pageSize = ref(25)
const pageSizeOptions = [
  { label: '10 per page', value: 10 },
  { label: '25 per page', value: 25 },
  { label: '50 per page', value: 50 },
  { label: '100 per page', value: 100 }
]

// ============================================================================
// Table Configuration
// ============================================================================

/**
 * Table columns definition with custom cell rendering
 */
const columns: TableColumn<DocumentResponse>[] = [
  {
    accessorKey: 'filename',
    header: 'Filename',
    meta: {
      class: {
        th: 'w-1/4'
      }
    }
  },
  {
    accessorKey: 'doc_type',
    header: 'Type',
    meta: {
      class: {
        th: 'w-32'
      }
    }
  },
  {
    accessorKey: 'programs',
    header: 'Programs',
    meta: {
      class: {
        th: 'w-1/4'
      }
    }
  },
  {
    accessorKey: 'year',
    header: 'Year',
    meta: {
      class: {
        th: 'w-20'
      }
    }
  },
  {
    accessorKey: 'outcome',
    header: 'Outcome',
    meta: {
      class: {
        th: 'w-32'
      }
    }
  },
  {
    accessorKey: 'upload_date',
    header: 'Uploaded',
    meta: {
      class: {
        th: 'w-32'
      }
    }
  },
  {
    id: 'actions',
    header: '',
    meta: {
      class: {
        th: 'w-16'
      }
    }
  }
]

// ============================================================================
// Computed
// ============================================================================

const hasActiveFilters = computed(() => {
  return (
    (filters.value.doc_types && filters.value.doc_types.length > 0) ||
    (filters.value.programs && filters.value.programs.length > 0) ||
    (filters.value.years && filters.value.years.length > 0) ||
    (filters.value.outcomes && filters.value.outcomes.length > 0)
  )
})

const activeFilterCount = computed(() => {
  let count = 0
  if (filters.value.doc_types) count += filters.value.doc_types.length
  if (filters.value.programs) count += filters.value.programs.length
  if (filters.value.years) count += filters.value.years.length
  if (filters.value.outcomes) count += filters.value.outcomes.length
  return count
})

// ============================================================================
// Methods
// ============================================================================

/**
 * Load documents with current filters and search query
 */
const loadDocuments = async () => {
  await getDocuments({
    page: localCurrentPage.value,
    per_page: pageSize.value,
    search: searchQuery.value || undefined,
    filters: hasActiveFilters.value ? filters.value : undefined,
    sort_by: 'upload_date',
    sort_order: 'desc'
  })
}

/**
 * Handle filter changes
 */
const handleFilterChange = () => {
  localCurrentPage.value = 1 // Reset to first page when filters change
  loadDocuments()
  mobileFilterOpen.value = false // Close mobile filter on selection
}

/**
 * Simple debounce implementation
 */
let searchTimeout: ReturnType<typeof setTimeout> | null = null
const debouncedSearch = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    localCurrentPage.value = 1 // Reset to first page when searching
    loadDocuments()
  }, 500)
}

/**
 * Clear all filters and search
 */
const clearAllFiltersAndSearch = () => {
  filters.value = {
    doc_types: [],
    programs: [],
    years: [],
    outcomes: []
  }
  searchQuery.value = ''
  loadDocuments()
}

/**
 * View document details
 */
const viewDocument = (document: DocumentResponse) => {
  // TODO: Implement document detail view/modal
  console.log('View document:', document)
}

/**
 * Confirm and delete document
 */
const confirmDelete = async (document: DocumentResponse) => {
  // TODO: Add confirmation modal
  const confirmed = confirm(`Are you sure you want to delete "${document.filename}"?`)
  if (confirmed) {
    const success = await deleteDocument(document.document_id)
    if (success) {
      // Refresh the list
      loadDocuments()
    }
  }
}

/**
 * Get dropdown menu actions for a document
 */
const getDropdownActions = (document: DocumentResponse): DropdownMenuItem[][] => {
  const actions: DropdownMenuItem[][] = [
    [
      {
        label: 'View',
        icon: 'i-heroicons-eye',
        onSelect: () => viewDocument(document)
      }
    ]
  ]

  // Add delete action for users with edit permissions
  if (canEdit) {
    actions.push([
      {
        label: 'Delete',
        icon: 'i-heroicons-trash',
        color: 'error',
        onSelect: () => confirmDelete(document)
      }
    ])
  }

  return actions
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Get icon for document type
 */
const getDocumentTypeIcon = (type: DocumentType): string => {
  const icons: Record<DocumentType, string> = {
    'Grant Proposal': 'i-heroicons-document-text',
    'Annual Report': 'i-heroicons-document-chart-bar',
    'Program Description': 'i-heroicons-document',
    'Impact Report': 'i-heroicons-chart-bar',
    'Strategic Plan': 'i-heroicons-light-bulb',
    'Other': 'i-heroicons-document'
  }
  return icons[type] || 'i-heroicons-document'
}

/**
 * Get color for outcome badge
 */
const getOutcomeColor = (outcome: DocumentOutcome): BadgeColor => {
  const colors: Record<DocumentOutcome, BadgeColor> = {
    'N/A': 'neutral',
    'Funded': 'success',
    'Not Funded': 'error',
    'Pending': 'warning',
    'Final Report': 'info'
  }
  return colors[outcome] || 'neutral'
}

/**
 * Get processing status icon
 */
const getProcessingStatusIcon = (status: string): string => {
  const icons: Record<string, string> = {
    pending: 'i-heroicons-clock',
    processing: 'i-heroicons-arrow-path',
    completed: 'i-heroicons-check-circle',
    failed: 'i-heroicons-x-circle'
  }
  return icons[status] || 'i-heroicons-question-mark-circle'
}

/**
 * Get processing status CSS class
 */
const getProcessingStatusClass = (status: string): string => {
  const classes: Record<string, string> = {
    pending: 'text-yellow-600 dark:text-yellow-400',
    processing: 'text-blue-600 dark:text-blue-400',
    completed: 'text-green-600 dark:text-green-400',
    failed: 'text-red-600 dark:text-red-400'
  }
  return classes[status] || 'text-gray-600 dark:text-gray-400'
}

/**
 * Format date for display
 */
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  }).format(date)
}

/**
 * Format file size for display
 */
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ============================================================================
// Lifecycle
// ============================================================================

// Load documents on mount
onMounted(() => {
  loadDocuments()
})

// Watch page changes
watch(localCurrentPage, () => {
  loadDocuments()
})

// Watch page size changes - reset to first page
watch(pageSize, () => {
  localCurrentPage.value = 1
  loadDocuments()
})
</script>

<style scoped>
.document-library-page {
  /* Full height layout with sticky header */
}
</style>
