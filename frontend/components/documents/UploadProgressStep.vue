<template>
  <UCard>
    <template #header>
      <div class="flex items-center gap-3">
        <UIcon
          :name="overallStatus === 'completed' ? 'i-heroicons-check-circle' : overallStatus === 'error' ? 'i-heroicons-exclamation-circle' : 'i-heroicons-arrow-up-tray'"
          :class="overallStatus === 'completed' ? 'text-green-500' : overallStatus === 'error' ? 'text-red-500' : 'text-primary'"
        />
        <div class="flex-1">
          <h3 class="text-lg font-semibold">{{ headerTitle }}</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {{ headerSubtitle }}
          </p>
        </div>
      </div>
    </template>

    <div class="space-y-6">
      <!-- Overall Progress Summary -->
      <div v-if="overallStatus !== 'completed'" class="space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-sm font-semibold text-gray-900 dark:text-white">
            Overall Progress
          </span>
          <span class="text-sm text-gray-600 dark:text-gray-400">
            {{ successCount + errorCount }} / {{ totalFiles }} completed
          </span>
        </div>
        <UProgress
          :value="overallProgress"
          :color="overallStatus === 'error' ? 'error' : 'primary'"
          size="lg"
        />
      </div>

      <!-- Upload Status Summary -->
      <div class="grid grid-cols-3 gap-4">
        <UCard :ui="{ body: 'p-4' }">
          <div class="flex items-center gap-3">
            <UIcon name="i-heroicons-document-text" class="text-gray-500" size="20" />
            <div>
              <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ totalFiles }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400">Total Files</p>
            </div>
          </div>
        </UCard>

        <UCard :ui="{ body: 'p-4' }">
          <div class="flex items-center gap-3">
            <UIcon name="i-heroicons-check-circle" class="text-green-500" size="20" />
            <div>
              <p class="text-2xl font-bold text-green-600 dark:text-green-400">{{ successCount }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400">Successful</p>
            </div>
          </div>
        </UCard>

        <UCard :ui="{ body: 'p-4' }">
          <div class="flex items-center gap-3">
            <UIcon name="i-heroicons-x-circle" class="text-red-500" size="20" />
            <div>
              <p class="text-2xl font-bold text-red-600 dark:text-red-400">{{ errorCount }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400">Failed</p>
            </div>
          </div>
        </UCard>
      </div>

      <!-- Individual File Progress -->
      <div class="space-y-3">
        <h4 class="text-sm font-semibold text-gray-900 dark:text-white">
          File Upload Status
        </h4>

        <div class="space-y-3">
          <div
            v-for="(fileStatus, index) in fileUploadStatuses"
            :key="fileStatus.filename"
            class="space-y-2"
          >
            <!-- File header -->
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 flex-1 min-w-0">
                <UIcon
                  :name="getStatusIcon(fileStatus.status)"
                  :class="getStatusColor(fileStatus.status)"
                  size="16"
                />
                <span class="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {{ fileStatus.filename }}
                </span>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-xs text-gray-500 dark:text-gray-400">
                  {{ getStatusLabel(fileStatus.status) }}
                </span>
                <span v-if="fileStatus.status === 'uploading'" class="text-xs font-semibold text-primary">
                  {{ fileStatus.progress }}%
                </span>
              </div>
            </div>

            <!-- Progress bar -->
            <UProgress
              v-if="fileStatus.status === 'uploading' || fileStatus.status === 'processing'"
              :value="fileStatus.progress"
              :color="getProgressColor(fileStatus.status)"
              size="sm"
            />

            <!-- Error message -->
            <UAlert
              v-if="fileStatus.status === 'error' && fileStatus.error"
              color="error"
              variant="soft"
              icon="i-heroicons-exclamation-triangle"
              :description="fileStatus.error"
              :ui="{ description: 'text-xs' }"
            />

            <!-- Success details -->
            <div v-if="fileStatus.status === 'success'" class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
              <UIcon name="i-heroicons-check" class="text-green-500" size="14" />
              <span>Uploaded and processed successfully</span>
              <span v-if="fileStatus.documentId" class="text-gray-400">• ID: {{ fileStatus.documentId.slice(0, 8) }}...</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Completion Summary -->
      <div v-if="overallStatus === 'completed'" class="space-y-4">
        <UAlert
          :color="hasErrors ? 'warning' : 'success'"
          variant="soft"
          :icon="hasErrors ? 'i-heroicons-exclamation-triangle' : 'i-heroicons-check-circle'"
        >
          <template #title>
            <span v-if="hasErrors">Upload completed with errors</span>
            <span v-else>All documents uploaded successfully!</span>
          </template>
          <template #description>
            <div class="space-y-1">
              <p v-if="successCount > 0">
                Successfully uploaded {{ successCount }} {{ successCount === 1 ? 'document' : 'documents' }}.
              </p>
              <p v-if="errorCount > 0" class="text-red-600 dark:text-red-400">
                {{ errorCount }} {{ errorCount === 1 ? 'document' : 'documents' }} failed to upload.
              </p>
            </div>
          </template>
        </UAlert>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-between pt-4 border-t">
        <UButton
          v-if="overallStatus !== 'completed'"
          label="Back"
          color="neutral"
          variant="ghost"
          icon="i-heroicons-arrow-left"
          :disabled="isUploading"
          @click="handleBack"
        />
        <div v-else />

        <div class="flex items-center gap-2">
          <UButton
            v-if="overallStatus === 'completed'"
            label="Upload More Documents"
            color="neutral"
            variant="outline"
            icon="i-heroicons-arrow-up-tray"
            @click="handleUploadMore"
          />

          <UButton
            v-if="overallStatus === 'completed'"
            label="Go to Library"
            color="primary"
            icon="i-heroicons-folder-open"
            trailing
            @click="handleGoToLibrary"
          />

          <UButton
            v-if="overallStatus !== 'completed' && canRetry"
            label="Retry Failed Uploads"
            color="error"
            variant="outline"
            icon="i-heroicons-arrow-path"
            @click="handleRetry"
          />
        </div>
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
/**
 * UploadProgressStep Component
 *
 * Step 4 of the document upload wizard. Shows real-time upload progress:
 * - Individual UProgress bars for each file
 * - Success/error indicators per file
 * - Overall upload summary
 * - Real-time status updates
 * - Actions: Upload More, Go to Library, Retry Failed
 *
 * @emits complete - Emitted when all uploads are complete (success or error)
 * @emits uploadMore - Emitted when user clicks "Upload More Documents"
 * @emits goToLibrary - Emitted when user clicks "Go to Library"
 * @emits back - Emitted when user clicks back button
 */

import type { DocumentMetadata } from '~/types/api'

// ============================================================================
// Types
// ============================================================================

type UploadStatus = 'pending' | 'uploading' | 'processing' | 'success' | 'error'

interface FileUploadStatus {
  filename: string
  status: UploadStatus
  progress: number
  error?: string
  documentId?: string
}

// ============================================================================
// Props & Emits
// ============================================================================

interface Props {
  files: File[]
  metadata: Record<string, DocumentMetadata>
}

const props = defineProps<Props>()

const emit = defineEmits<{
  complete: [results: { successful: string[]; failed: string[] }]
  uploadMore: []
  goToLibrary: []
  back: []
}>()

// ============================================================================
// Composables
// ============================================================================

const { uploadDocuments } = useDocuments()

// ============================================================================
// State
// ============================================================================

const fileUploadStatuses = ref<FileUploadStatus[]>([])
const overallStatus = ref<'pending' | 'uploading' | 'completed' | 'error'>('pending')

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Total number of files
 */
const totalFiles = computed(() => props.files.length)

/**
 * Number of successfully uploaded files
 */
const successCount = computed(() => {
  return fileUploadStatuses.value.filter(f => f.status === 'success').length
})

/**
 * Number of failed uploads
 */
const errorCount = computed(() => {
  return fileUploadStatuses.value.filter(f => f.status === 'error').length
})

/**
 * Number of pending/uploading files
 */
const uploadingCount = computed(() => {
  return fileUploadStatuses.value.filter(f =>
    f.status === 'pending' || f.status === 'uploading' || f.status === 'processing'
  ).length
})

/**
 * Overall progress percentage (0-100)
 */
const overallProgress = computed(() => {
  if (totalFiles.value === 0) return 0

  const totalProgress = fileUploadStatuses.value.reduce((sum, file) => {
    return sum + file.progress
  }, 0)

  return Math.round(totalProgress / totalFiles.value)
})

/**
 * Check if any uploads are in progress
 */
const isUploading = computed(() => {
  return uploadingCount.value > 0
})

/**
 * Check if there are errors
 */
const hasErrors = computed(() => {
  return errorCount.value > 0
})

/**
 * Check if user can retry failed uploads
 */
const canRetry = computed(() => {
  return errorCount.value > 0 && uploadingCount.value === 0
})

/**
 * Dynamic header title based on status
 */
const headerTitle = computed(() => {
  switch (overallStatus.value) {
    case 'pending':
      return 'Preparing Upload'
    case 'uploading':
      return 'Uploading Documents'
    case 'completed':
      return hasErrors.value ? 'Upload Completed with Errors' : 'Upload Complete'
    case 'error':
      return 'Upload Failed'
    default:
      return 'Upload Status'
  }
})

/**
 * Dynamic header subtitle based on status
 */
const headerSubtitle = computed(() => {
  switch (overallStatus.value) {
    case 'pending':
      return 'Step 4: Starting document upload...'
    case 'uploading':
      return `Step 4: Uploading ${uploadingCount.value} of ${totalFiles.value} documents`
    case 'completed':
      return `Step 4: ${successCount.value} successful, ${errorCount.value} failed`
    case 'error':
      return 'Step 4: Upload process encountered errors'
    default:
      return 'Step 4: Upload status'
  }
})

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get icon name for upload status
 */
const getStatusIcon = (status: UploadStatus): string => {
  switch (status) {
    case 'pending':
      return 'i-heroicons-clock'
    case 'uploading':
      return 'i-heroicons-arrow-up-tray'
    case 'processing':
      return 'i-heroicons-cog-6-tooth'
    case 'success':
      return 'i-heroicons-check-circle'
    case 'error':
      return 'i-heroicons-x-circle'
    default:
      return 'i-heroicons-document'
  }
}

/**
 * Get color class for upload status (returns CSS classes, not BadgeColor)
 */
const getStatusColor = (status: UploadStatus): string => {
  switch (status) {
    case 'success':
      return 'text-green-500'
    case 'error':
      return 'text-red-500'
    case 'uploading':
    case 'processing':
      return 'text-primary animate-spin'
    case 'pending':
      return 'text-gray-400'
    default:
      return 'text-gray-500'
  }
}

/**
 * Get label text for upload status
 */
const getStatusLabel = (status: UploadStatus): string => {
  switch (status) {
    case 'pending':
      return 'Waiting...'
    case 'uploading':
      return 'Uploading...'
    case 'processing':
      return 'Processing...'
    case 'success':
      return 'Complete'
    case 'error':
      return 'Failed'
    default:
      return 'Unknown'
  }
}

/**
 * Get progress bar color for upload status
 * Returns valid Nuxt UI color tokens
 */
const getProgressColor = (status: UploadStatus): 'primary' | 'info' | 'neutral' => {
  switch (status) {
    case 'uploading':
      return 'primary'
    case 'processing':
      return 'info'  // ✅ Changed from 'blue' to 'info'
    default:
      return 'neutral'  // ✅ Changed from 'gray' to 'neutral'
  }
}

/**
 * Initialize file upload statuses
 */
const initializeStatuses = () => {
  fileUploadStatuses.value = props.files.map(file => ({
    filename: file.name,
    status: 'pending' as UploadStatus,
    progress: 0,
  }))
}

/**
 * Update individual file status
 */
const updateFileStatus = (
  filename: string,
  status: UploadStatus,
  progress?: number,
  error?: string,
  documentId?: string
) => {
  const fileStatus = fileUploadStatuses.value.find(f => f.filename === filename)
  if (fileStatus) {
    fileStatus.status = status
    if (progress !== undefined) {
      fileStatus.progress = progress
    }
    if (error) {
      fileStatus.error = error
    }
    if (documentId) {
      fileStatus.documentId = documentId
    }
  }
}

/**
 * Check if all uploads are complete
 */
const checkIfComplete = () => {
  const allComplete = fileUploadStatuses.value.every(
    f => f.status === 'success' || f.status === 'error'
  )

  if (allComplete) {
    overallStatus.value = 'completed'

    // Emit complete event with results
    const successful = fileUploadStatuses.value
      .filter(f => f.status === 'success')
      .map(f => f.filename)

    const failed = fileUploadStatuses.value
      .filter(f => f.status === 'error')
      .map(f => f.filename)

    emit('complete', { successful, failed })
  }
}

/**
 * Start uploading all files
 */
const startUploads = async () => {
  overallStatus.value = 'uploading'

  // Upload each file sequentially (could be parallel with Promise.all)
  for (const file of props.files) {
    try {
      // Update status to uploading
      updateFileStatus(file.name, 'uploading', 10)

      // Get metadata for this file
      const fileMetadata = props.metadata[file.name]

      // Simulate upload progress (in real implementation, this would come from API)
      updateFileStatus(file.name, 'uploading', 30)

      // Upload the document using composable
      const result = await uploadDocuments([file], {
        [file.name]: fileMetadata,
      })

      // Update progress during processing
      updateFileStatus(file.name, 'processing', 70)

      // Simulate processing time
      await new Promise(resolve => setTimeout(resolve, 500))

      // Check if upload was successful
      if (result.successful.includes(file.name)) {
        updateFileStatus(file.name, 'success', 100, undefined, result.documentIds?.[file.name])
      } else {
        const errorMsg = result.errors?.[file.name] || 'Unknown error occurred'
        updateFileStatus(file.name, 'error', 0, errorMsg)
      }
    } catch (error: any) {
      // Handle upload error
      const errorMsg = error.message || 'Upload failed'
      updateFileStatus(file.name, 'error', 0, errorMsg)
    }

    // Check if all uploads are complete
    checkIfComplete()
  }
}

/**
 * Retry failed uploads
 */
const handleRetry = async () => {
  // Get failed files
  const failedFiles = fileUploadStatuses.value
    .filter(f => f.status === 'error')
    .map(f => f.filename)

  // Reset their status
  failedFiles.forEach(filename => {
    updateFileStatus(filename, 'pending', 0)
  })

  // Restart uploads for failed files only
  overallStatus.value = 'uploading'

  for (const filename of failedFiles) {
    const file = props.files.find(f => f.name === filename)
    if (!file) continue

    try {
      updateFileStatus(file.name, 'uploading', 10)

      const fileMetadata = props.metadata[file.name]
      updateFileStatus(file.name, 'uploading', 30)

      const result = await uploadDocuments([file], {
        [file.name]: fileMetadata,
      })

      updateFileStatus(file.name, 'processing', 70)
      await new Promise(resolve => setTimeout(resolve, 500))

      if (result.successful.includes(file.name)) {
        updateFileStatus(file.name, 'success', 100, undefined, result.documentIds?.[file.name])
      } else {
        const errorMsg = result.errors?.[file.name] || 'Unknown error occurred'
        updateFileStatus(file.name, 'error', 0, errorMsg)
      }
    } catch (error: any) {
      const errorMsg = error.message || 'Upload failed'
      updateFileStatus(file.name, 'error', 0, errorMsg)
    }

    checkIfComplete()
  }
}

// ============================================================================
// Event Handlers
// ============================================================================

/**
 * Handle back button click
 */
const handleBack = () => {
  emit('back')
}

/**
 * Handle "Upload More Documents" button click
 */
const handleUploadMore = () => {
  emit('uploadMore')
}

/**
 * Handle "Go to Library" button click
 */
const handleGoToLibrary = () => {
  emit('goToLibrary')
}

/**
 * Reset component state
 */
const reset = () => {
  fileUploadStatuses.value = []
  overallStatus.value = 'pending'
}

// ============================================================================
// Lifecycle
// ============================================================================

/**
 * Initialize on mount
 */
onMounted(() => {
  initializeStatuses()
  // Start uploads automatically when component mounts
  startUploads()
})

// ============================================================================
// Expose public API
// ============================================================================

defineExpose({
  reset,
  startUploads,
  fileUploadStatuses,
  overallStatus,
})
</script>
