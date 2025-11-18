<template>
  <UCard>
    <template #header>
      <div class="flex items-center gap-3">
        <UIcon name="i-heroicons-document-check" class="text-primary" />
        <div class="flex-1">
          <h3 class="text-lg font-semibold">Document Metadata</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Step 2: Add metadata for {{ files.length }} {{ files.length === 1 ? 'document' : 'documents' }}
          </p>
        </div>
      </div>
    </template>

    <div class="space-y-6">
      <!-- Apply to All Section (if multiple files) -->
      <div v-if="files.length > 1" class="space-y-4">
        <UAlert
          color="info"
          variant="soft"
          icon="i-heroicons-information-circle"
        >
          <template #description>
            You can apply the same metadata to all documents, or customize each one individually below.
          </template>
        </UAlert>

        <div class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div>
            <p class="font-semibold text-sm">Apply same metadata to all documents</p>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Fill out the form below once and apply to all {{ files.length }} documents
            </p>
          </div>
          <UButton
            v-if="!applyToAll"
            label="Apply to All"
            color="primary"
            variant="outline"
            icon="i-heroicons-document-duplicate"
            @click="enableApplyToAll"
          />
          <UButton
            v-else
            label="Customize Each"
            color="neutral"
            variant="outline"
            icon="i-heroicons-pencil-square"
            @click="disableApplyToAll"
          />
        </div>
      </div>

      <!-- Document Forms -->
      <div v-if="applyToAll" class="space-y-6">
        <!-- Single form for all files -->
        <DocumentMetadataForm
          :file-index="0"
          :filename="'All Documents'"
          :metadata="metadataForms[0]"
          :programs="availablePrograms"
          :validation-errors="validationErrors[0]"
          :show-apply-all="false"
          @update="updateMetadata(0, $event)"
        />
      </div>
      <div v-else class="space-y-6">
        <!-- Individual form for each file -->
        <div v-for="(file, index) in files" :key="file.name" class="space-y-4">
          <UDivider v-if="index > 0" />
          <DocumentMetadataForm
            :file-index="index"
            :filename="file.name"
            :metadata="metadataForms[index]"
            :programs="availablePrograms"
            :validation-errors="validationErrors[index]"
            :show-apply-all="files.length > 1"
            @update="updateMetadata(index, $event)"
            @apply-to-all="applyMetadataToAll(index)"
          />
        </div>
      </div>

      <!-- Validation Summary -->
      <div v-if="showValidationErrors" class="space-y-2">
        <UAlert
          color="error"
          variant="soft"
          icon="i-heroicons-exclamation-triangle"
          title="Please fix validation errors"
        >
          <template #description>
            <ul class="list-disc list-inside space-y-1">
              <li v-for="(error, index) in allValidationErrors" :key="index">
                {{ error }}
              </li>
            </ul>
          </template>
        </UAlert>
      </div>

      <!-- Actions -->
      <div class="flex items-center justify-between pt-4 border-t">
        <UButton
          label="Back to Files"
          color="neutral"
          variant="ghost"
          icon="i-heroicons-arrow-left"
          @click="handleBack"
        />

        <UButton
          label="Continue"
          color="primary"
          icon="i-heroicons-arrow-right"
          trailing
          :disabled="!canContinue"
          @click="handleContinue"
        />
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
/**
 * MetadataFormStep Component
 *
 * Step 2 of the document upload wizard. Collects metadata for each uploaded file:
 * - Document type (USelect)
 * - Year (UInput with validation)
 * - Programs (USelectMenu - multi-select)
 * - Tags (chip input)
 * - Outcome (USelect)
 * - Notes (UTextarea)
 *
 * Features:
 * - "Apply to all" functionality for multiple files
 * - Individual forms for each file
 * - Required field validation
 * - Year validation (1900-current year+1)
 *
 * @emits continue - Emitted when user clicks continue with valid metadata
 * @emits back - Emitted when user clicks back button
 */

import type { DocumentMetadata, DocumentType, DocumentOutcome } from '~/types/api'

// ============================================================================
// Props & Emits
// ============================================================================

interface Props {
  files: File[]
  programs?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  programs: () => [],
})

const emit = defineEmits<{
  continue: [metadata: Record<string, DocumentMetadata>]
  back: []
}>()

// ============================================================================
// State
// ============================================================================

const applyToAll = ref(false)
const showValidationErrors = ref(false)

/**
 * Available programs for multi-select
 * TODO: This should be fetched from the programs API when available
 */
const availablePrograms = computed(() => {
  // If programs are provided via props, use them
  if (props.programs.length > 0) {
    return props.programs
  }

  // Otherwise, return some default examples for development
  return [
    'Education',
    'Youth Development',
    'Community Health',
    'Environmental Justice',
    'Arts & Culture',
  ]
})

/**
 * Metadata form for each file
 */
const metadataForms = ref<DocumentMetadata[]>(
  props.files.map(() => ({
    doc_type: 'Grant Proposal',
    year: new Date().getFullYear(),
    programs: [],
    tags: [],
    outcome: 'N/A',
    notes: '',
  }))
)

/**
 * Validation errors for each file
 */
const validationErrors = ref<Record<string, string>[]>(
  props.files.map(() => ({}))
)

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Check if all forms are valid
 */
const allFormsValid = computed(() => {
  return metadataForms.value.every((metadata, index) => {
    const errors = validateMetadata(metadata, index)
    return Object.keys(errors).length === 0
  })
})

/**
 * Check if user can continue to next step
 */
const canContinue = computed(() => {
  return allFormsValid.value
})

/**
 * Get all validation errors across all forms
 */
const allValidationErrors = computed(() => {
  const errors: string[] = []

  validationErrors.value.forEach((fileErrors, index) => {
    const filename = applyToAll.value ? 'All Documents' : props.files[index]?.name || `Document ${index + 1}`

    Object.values(fileErrors).forEach((error) => {
      errors.push(`${filename}: ${error}`)
    })
  })

  return errors
})

// ============================================================================
// Validation Functions
// ============================================================================

/**
 * Validate a single metadata form
 */
const validateMetadata = (metadata: DocumentMetadata, index: number): Record<string, string> => {
  const errors: Record<string, string> = {}

  // Validate doc_type (required)
  if (!metadata.doc_type) {
    errors.doc_type = 'Document type is required'
  }

  // Validate year (required, must be reasonable)
  const currentYear = new Date().getFullYear()
  if (!metadata.year) {
    errors.year = 'Year is required'
  } else if (metadata.year < 1900 || metadata.year > currentYear + 1) {
    errors.year = `Year must be between 1900 and ${currentYear + 1}`
  }

  // Validate outcome (required)
  if (!metadata.outcome) {
    errors.outcome = 'Outcome is required'
  }

  return errors
}

/**
 * Validate all forms
 */
const validateAllForms = () => {
  let hasErrors = false

  if (applyToAll.value) {
    // Validate single form for all files
    const errors = validateMetadata(metadataForms.value[0], 0)
    validationErrors.value[0] = errors
    hasErrors = Object.keys(errors).length > 0
  } else {
    // Validate each form
    metadataForms.value.forEach((metadata, index) => {
      const errors = validateMetadata(metadata, index)
      validationErrors.value[index] = errors
      if (Object.keys(errors).length > 0) {
        hasErrors = true
      }
    })
  }

  showValidationErrors.value = hasErrors
  return !hasErrors
}

// ============================================================================
// Event Handlers
// ============================================================================

/**
 * Update metadata for a specific file
 */
const updateMetadata = (index: number, metadata: DocumentMetadata) => {
  metadataForms.value[index] = metadata

  // Clear validation errors for this form when user makes changes
  validationErrors.value[index] = {}
  showValidationErrors.value = false
}

/**
 * Apply metadata from one form to all files
 */
const applyMetadataToAll = (sourceIndex: number) => {
  const sourceMetadata = metadataForms.value[sourceIndex]

  metadataForms.value = metadataForms.value.map(() => ({
    ...sourceMetadata,
  }))

  // Clear all validation errors
  validationErrors.value = props.files.map(() => ({}))
  showValidationErrors.value = false
}

/**
 * Enable "apply to all" mode
 */
const enableApplyToAll = () => {
  applyToAll.value = true

  // Keep the first form as the template
  // All other forms will use this metadata when submitting
}

/**
 * Disable "apply to all" mode
 */
const disableApplyToAll = () => {
  applyToAll.value = false

  // Copy the template metadata to all forms
  const templateMetadata = metadataForms.value[0]
  metadataForms.value = metadataForms.value.map(() => ({
    ...templateMetadata,
  }))
}

/**
 * Handle back button click
 */
const handleBack = () => {
  emit('back')
}

/**
 * Handle continue button click
 */
const handleContinue = () => {
  // Validate all forms
  if (!validateAllForms()) {
    return
  }

  // Build metadata map for each file
  const metadataMap: Record<string, DocumentMetadata> = {}

  props.files.forEach((file, index) => {
    // If "apply to all" is enabled, use the first form's metadata for all files
    const metadata = applyToAll.value ? metadataForms.value[0] : metadataForms.value[index]

    metadataMap[file.name] = {
      ...metadata,
    }
  })

  emit('continue', metadataMap)
}

/**
 * Reset component state
 */
const reset = () => {
  applyToAll.value = false
  showValidationErrors.value = false

  metadataForms.value = props.files.map(() => ({
    doc_type: 'Grant Proposal',
    year: new Date().getFullYear(),
    programs: [],
    tags: [],
    outcome: 'N/A',
    notes: '',
  }))

  validationErrors.value = props.files.map(() => ({}))
}

// ============================================================================
// Watch for file changes
// ============================================================================

watch(
  () => props.files.length,
  (newLength, oldLength) => {
    if (newLength !== oldLength) {
      // Reset forms when files change
      reset()
    }
  }
)

// ============================================================================
// Expose public API
// ============================================================================

defineExpose({
  reset,
  validateAllForms,
  metadataForms,
})
</script>

