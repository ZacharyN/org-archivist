<template>
  <UCard>
    <template #header>
      <div class="flex items-center gap-3">
        <UIcon name="i-heroicons-arrow-up-tray" class="text-primary" />
        <div class="flex-1">
          <h3 class="text-lg font-semibold">Upload Documents</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Step 1: Select files to upload
          </p>
        </div>
      </div>
    </template>

    <div class="space-y-6">
      <!-- File Upload Area -->
      <div>
        <UFormField
          name="files"
          label="Documents"
          :error="validationError || undefined"
          :help="!validationError ? 'PDF, DOCX, or TXT files. Max 50MB per file.' : undefined"
        >
          <UFileUpload
            v-model="selectedFiles"
            multiple
            :accept="acceptedFileTypes"
            :disabled="isUploading"
            icon="i-heroicons-document-text"
            label="Drop your documents here"
            description="PDF, DOCX, or TXT (max 50MB per file)"
            layout="list"
            position="outside"
            class="min-h-48"
            :highlight="!!validationError"
            :color="validationError ? 'error' : 'primary'"
            @change="handleFileChange"
          >
            <template #files-top="{ files, open }">
              <div v-if="files && files.length > 0" class="mb-3 flex items-center justify-between">
                <p class="font-semibold text-sm text-gray-700 dark:text-gray-300">
                  Selected Files ({{ files.length }})
                </p>
                <UButton
                  icon="i-heroicons-plus"
                  label="Add more"
                  color="neutral"
                  variant="outline"
                  size="xs"
                  @click="open()"
                />
              </div>
            </template>

            <template #files-bottom="{ files, removeFile }">
              <div v-if="files && files.length > 0" class="mt-3 flex items-center justify-between">
                <p class="text-xs text-gray-500 dark:text-gray-400">
                  Total size: {{ formatTotalSize(files) }}
                </p>
                <UButton
                  label="Remove all"
                  color="error"
                  variant="link"
                  size="xs"
                  @click="removeFile()"
                />
              </div>
            </template>
          </UFileUpload>
        </UFormField>
      </div>

      <!-- File Validation Messages -->
      <div v-if="fileValidationMessages.length > 0" class="space-y-2">
        <UAlert
          v-for="(msg, index) in fileValidationMessages"
          :key="index"
          :color="msg.type === 'error' ? 'error' : 'warning'"
          :icon="msg.type === 'error' ? 'i-heroicons-exclamation-circle' : 'i-heroicons-exclamation-triangle'"
          :title="msg.title"
          :description="msg.description"
          variant="soft"
        />
      </div>

      <!-- Sensitivity Confirmation (MVP Requirement) -->
      <UFormField
        v-if="selectedFiles && selectedFiles.length > 0"
        name="sensitivity_confirmation"
        :error="sensitivityError || undefined"
      >
        <UCard
          :ui="{
            body: 'p-4',
            root: sensitivityError ? 'ring-2 ring-red-500' : ''
          }"
        >
          <div class="space-y-3">
            <div class="flex items-start gap-3">
              <UIcon
                name="i-heroicons-shield-exclamation"
                class="text-yellow-500 mt-0.5 shrink-0"
                size="20"
              />
              <div class="flex-1 space-y-2">
                <p class="text-sm font-semibold text-gray-900 dark:text-white">
                  Document Sensitivity Notice
                </p>
                <p class="text-sm text-gray-600 dark:text-gray-400">
                  Only upload <strong>public-facing documents</strong>. Do not upload confidential,
                  financial, or sensitive operational documents.
                </p>
                <UAlert
                  color="warning"
                  variant="soft"
                  icon="i-heroicons-information-circle"
                  class="mt-2"
                >
                  <template #description>
                    <p class="text-xs">
                      Appropriate: Published grant proposals, annual reports, public program descriptions, impact reports
                    </p>
                    <p class="text-xs mt-1">
                      <strong>Not appropriate:</strong> Financial documents, client information, confidential donor data, internal personnel documents
                    </p>
                  </template>
                </UAlert>
              </div>
            </div>

            <UCheckbox
              v-model="sensitivityConfirmed"
              label="I confirm these documents are public-facing and appropriate for AI processing"
              :required="true"
            />
          </div>
        </UCard>
      </UFormField>

      <!-- Upload Statistics -->
      <div v-if="selectedFiles && selectedFiles.length > 0" class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <div class="flex items-center gap-4">
          <div>
            <p class="text-xs text-gray-500 dark:text-gray-400">Total Files</p>
            <p class="text-lg font-semibold text-gray-900 dark:text-white">{{ selectedFiles.length }}</p>
          </div>
          <UDivider orientation="vertical" class="h-10" />
          <div>
            <p class="text-xs text-gray-500 dark:text-gray-400">Total Size</p>
            <p class="text-lg font-semibold text-gray-900 dark:text-white">{{ formatTotalSize(selectedFiles) }}</p>
          </div>
          <UDivider orientation="vertical" class="h-10" />
          <div>
            <p class="text-xs text-gray-500 dark:text-gray-400">Valid Files</p>
            <p class="text-lg font-semibold" :class="allFilesValid ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'">
              {{ validFileCount }} / {{ selectedFiles.length }}
            </p>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-between pt-4 border-t">
        <UButton
          label="Cancel"
          color="neutral"
          variant="ghost"
          icon="i-heroicons-x-mark"
          @click="handleCancel"
        />

        <UButton
          label="Continue to Metadata"
          color="primary"
          icon="i-heroicons-arrow-right"
          trailing
          :disabled="!canContinue"
          :loading="isUploading"
          @click="handleContinue"
        />
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
/**
 * FileUploadStep Component
 *
 * Step 1 of the document upload wizard. Handles file selection with:
 * - Drag-and-drop zone
 * - File type validation (PDF, DOCX, TXT)
 * - File size validation (max 50MB)
 * - Multiple file support
 * - File preview list with remove option
 * - Sensitivity confirmation (MVP requirement)
 *
 * @emits continue - Emitted when user clicks continue with valid files
 * @emits cancel - Emitted when user cancels upload
 */

interface ValidationMessage {
  type: 'error' | 'warning'
  title: string
  description: string
  filename?: string
}

// ============================================================================
// Props & Emits
// ============================================================================

const emit = defineEmits<{
  continue: [files: File[]]
  cancel: []
}>()

// ============================================================================
// State
// ============================================================================

const selectedFiles = ref<File[] | null>(null)
const sensitivityConfirmed = ref(false)
const validationError = ref<string | null>(null)
const sensitivityError = ref<string | null>(null)
const fileValidationMessages = ref<ValidationMessage[]>([])
const isUploading = ref(false)

// ============================================================================
// Constants
// ============================================================================

const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB in bytes
const ACCEPTED_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
  'application/msword', // .doc
  'text/plain',
]
const ACCEPTED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.txt']
const acceptedFileTypes = ACCEPTED_MIME_TYPES.join(',') + ',' + ACCEPTED_EXTENSIONS.join(',')

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Check if all selected files are valid
 */
const allFilesValid = computed(() => {
  if (!selectedFiles.value || selectedFiles.value.length === 0) return false
  return fileValidationMessages.value.every(msg => msg.type !== 'error')
})

/**
 * Count of valid files
 */
const validFileCount = computed(() => {
  if (!selectedFiles.value) return 0
  const errorFiles = new Set(
    fileValidationMessages.value
      .filter(msg => msg.type === 'error' && msg.filename)
      .map(msg => msg.filename)
  )
  return selectedFiles.value.filter(file => !errorFiles.has(file.name)).length
})

/**
 * Check if user can continue to next step
 */
const canContinue = computed(() => {
  return (
    selectedFiles.value &&
    selectedFiles.value.length > 0 &&
    sensitivityConfirmed.value &&
    allFilesValid.value &&
    !isUploading.value
  )
})

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format file size in human-readable format
 */
const formatBytes = (bytes: number, decimals = 2): string => {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
}

/**
 * Format total size of all files
 */
const formatTotalSize = (files: File[]): string => {
  const totalBytes = files.reduce((sum, file) => sum + file.size, 0)
  return formatBytes(totalBytes)
}

/**
 * Check if file type is valid
 */
const isValidFileType = (file: File): boolean => {
  // Check MIME type
  if (ACCEPTED_MIME_TYPES.includes(file.type)) {
    return true
  }

  // Check file extension as fallback
  const fileName = file.name.toLowerCase()
  return ACCEPTED_EXTENSIONS.some(ext => fileName.endsWith(ext))
}

/**
 * Check if file size is valid
 */
const isValidFileSize = (file: File): boolean => {
  return file.size <= MAX_FILE_SIZE
}

/**
 * Validate a single file
 */
const validateFile = (file: File): ValidationMessage | null => {
  // Check file type
  if (!isValidFileType(file)) {
    return {
      type: 'error',
      title: `Invalid file type: ${file.name}`,
      description: 'Only PDF, DOCX, and TXT files are accepted.',
      filename: file.name,
    }
  }

  // Check file size
  if (!isValidFileSize(file)) {
    return {
      type: 'error',
      title: `File too large: ${file.name}`,
      description: `File size is ${formatBytes(file.size)}. Maximum allowed size is ${formatBytes(MAX_FILE_SIZE)}.`,
      filename: file.name,
    }
  }

  return null
}

/**
 * Validate all selected files
 */
const validateFiles = (files: File[]): ValidationMessage[] => {
  const messages: ValidationMessage[] = []

  // Validate each file
  files.forEach(file => {
    const error = validateFile(file)
    if (error) {
      messages.push(error)
    }
  })

  // Check for duplicate filenames
  const filenames = new Set<string>()
  files.forEach(file => {
    if (filenames.has(file.name)) {
      messages.push({
        type: 'warning',
        title: `Duplicate filename: ${file.name}`,
        description: 'Multiple files with the same name detected. Consider renaming before upload.',
        filename: file.name,
      })
    }
    filenames.add(file.name)
  })

  return messages
}

// ============================================================================
// Event Handlers
// ============================================================================

/**
 * Handle file selection change
 */
const handleFileChange = (event: Event) => {
  validationError.value = null
  sensitivityError.value = null
  fileValidationMessages.value = []

  if (!selectedFiles.value || selectedFiles.value.length === 0) {
    return
  }

  // Validate files
  const messages = validateFiles(selectedFiles.value)
  fileValidationMessages.value = messages

  // Set general validation error if any critical errors
  const hasErrors = messages.some(msg => msg.type === 'error')
  if (hasErrors) {
    validationError.value = 'Some files are invalid. Please remove or replace them.'
  }
}

/**
 * Handle continue button click
 */
const handleContinue = () => {
  // Reset errors
  validationError.value = null
  sensitivityError.value = null

  // Validate files are selected
  if (!selectedFiles.value || selectedFiles.value.length === 0) {
    validationError.value = 'Please select at least one file to upload.'
    return
  }

  // Validate sensitivity confirmation
  if (!sensitivityConfirmed.value) {
    sensitivityError.value = 'You must confirm that these documents are public-facing.'
    return
  }

  // Validate all files
  if (!allFilesValid.value) {
    validationError.value = 'Please fix all validation errors before continuing.'
    return
  }

  // Emit continue event with valid files
  emit('continue', selectedFiles.value)
}

/**
 * Handle cancel button click
 */
const handleCancel = () => {
  // Reset state
  selectedFiles.value = null
  sensitivityConfirmed.value = false
  validationError.value = null
  sensitivityError.value = null
  fileValidationMessages.value = []

  emit('cancel')
}

/**
 * Reset component state (callable by parent)
 */
const reset = () => {
  selectedFiles.value = null
  sensitivityConfirmed.value = false
  validationError.value = null
  sensitivityError.value = null
  fileValidationMessages.value = []
  isUploading.value = false
}

// ============================================================================
// Watch for sensitivity confirmation changes
// ============================================================================

watch(sensitivityConfirmed, (newValue) => {
  if (newValue) {
    sensitivityError.value = null
  }
})

// ============================================================================
// Expose public API
// ============================================================================

defineExpose({
  reset,
  selectedFiles,
  sensitivityConfirmed,
  canContinue,
})
</script>
