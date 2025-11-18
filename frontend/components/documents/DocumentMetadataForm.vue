<template>
  <UCard
    :ui="{
      body: 'p-4',
      root: hasValidationErrors ? 'ring-2 ring-red-500' : ''
    }"
  >
    <template #header>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <UIcon name="i-heroicons-document" class="text-gray-500" />
          <div>
            <h4 class="font-semibold text-gray-900 dark:text-white">
              {{ fileIndex !== undefined ? `Document ${fileIndex + 1}` : 'Document Metadata' }}
            </h4>
            <p class="text-sm text-gray-500 dark:text-gray-400 truncate max-w-md">
              {{ filename }}
            </p>
          </div>
        </div>

        <UButton
          v-if="showApplyAll"
          label="Apply to All"
          color="primary"
          variant="ghost"
          size="xs"
          icon="i-heroicons-document-duplicate"
          @click="$emit('applyToAll')"
        />
      </div>
    </template>

    <UForm :state="formState" @submit="handleSubmit">
      <div class="space-y-4">
        <!-- Document Type (Required) -->
        <UFormField
          label="Document Type"
          name="doc_type"
          required
          :error="validationErrors?.doc_type"
          :help="!validationErrors?.doc_type ? 'Select the type of document' : undefined"
        >
          <USelect
            v-model="formState.doc_type"
            :options="documentTypeOptions"
            placeholder="Select document type..."
            size="md"
            @update:model-value="handleFieldChange"
          />
        </UFormField>

        <!-- Year (Required) -->
        <UFormField
          label="Year"
          name="year"
          required
          :error="validationErrors?.year"
          :help="!validationErrors?.year ? 'Year the document was created or submitted' : undefined"
        >
          <UInput
            v-model.number="formState.year"
            type="number"
            :min="1900"
            :max="maxYear"
            placeholder="2024"
            size="md"
            icon="i-heroicons-calendar"
            @update:model-value="handleFieldChange"
          />
        </UFormField>

        <!-- Programs (Multi-select) -->
        <UFormField
          label="Programs"
          name="programs"
          :error="validationErrors?.programs"
          :help="!validationErrors?.programs ? 'Select all applicable programs (optional)' : undefined"
        >
          <USelectMenu
            v-model="formState.programs"
            :options="programOptions"
            multiple
            placeholder="Select programs..."
            size="md"
            searchable
            @update:model-value="handleFieldChange"
          />

          <!-- Display selected programs as badges -->
          <div v-if="formState.programs.length > 0" class="flex flex-wrap gap-2 mt-2">
            <UBadge
              v-for="program in formState.programs"
              :key="program"
              color="primary"
              variant="soft"
              size="sm"
            >
              {{ program }}
              <UButton
                icon="i-heroicons-x-mark"
                size="xs"
                color="primary"
                variant="link"
                :padded="false"
                class="ml-1"
                @click="removeProgram(program)"
              />
            </UBadge>
          </div>
        </UFormField>

        <!-- Tags (Chip input) -->
        <UFormField
          label="Tags"
          name="tags"
          :error="validationErrors?.tags"
          :help="!validationErrors?.tags ? 'Add tags to categorize this document (press Enter or comma to add)' : undefined"
        >
          <UInput
            v-model="tagInput"
            placeholder="Type a tag and press Enter..."
            size="md"
            icon="i-heroicons-tag"
            @keydown.enter.prevent="addTag"
            @keydown.188.prevent="addTag"
          />

          <!-- Display tags as chips -->
          <div v-if="formState.tags.length > 0" class="flex flex-wrap gap-2 mt-2">
            <UBadge
              v-for="tag in formState.tags"
              :key="tag"
              color="neutral"
              variant="soft"
              size="sm"
            >
              {{ tag }}
              <UButton
                icon="i-heroicons-x-mark"
                size="xs"
                color="neutral"
                variant="link"
                :padded="false"
                class="ml-1"
                @click="removeTag(tag)"
              />
            </UBadge>
          </div>
        </UFormField>

        <!-- Outcome (Required) -->
        <UFormField
          label="Outcome"
          name="outcome"
          required
          :error="validationErrors?.outcome"
          :help="!validationErrors?.outcome ? 'Result or status of the document' : undefined"
        >
          <USelect
            v-model="formState.outcome"
            :options="outcomeOptions"
            placeholder="Select outcome..."
            size="md"
            @update:model-value="handleFieldChange"
          />
        </UFormField>

        <!-- Notes (Optional) -->
        <UFormField
          label="Notes"
          name="notes"
          :error="validationErrors?.notes"
          :help="!validationErrors?.notes ? 'Additional context or information about this document (optional)' : undefined"
        >
          <UTextarea
            v-model="formState.notes"
            placeholder="Add any additional notes about this document..."
            :rows="3"
            size="md"
            @update:model-value="handleFieldChange"
          />
        </UFormField>
      </div>
    </UForm>
  </UCard>
</template>

<script setup lang="ts">
/**
 * DocumentMetadataForm Component
 *
 * Individual metadata form for a single document in the upload wizard.
 *
 * Includes:
 * - Document type (USelect) - Required
 * - Year (UInput) - Required
 * - Programs (USelectMenu multi-select) - Optional
 * - Tags (Chip input) - Optional
 * - Outcome (USelect) - Required
 * - Notes (UTextarea) - Optional
 *
 * @emits update - Emitted when any field changes with updated metadata
 * @emits applyToAll - Emitted when "Apply to All" button is clicked
 */

import type { DocumentMetadata, DocumentType, DocumentOutcome } from '~/types/api'

// ============================================================================
// Props & Emits
// ============================================================================

interface Props {
  fileIndex?: number
  filename: string
  metadata: DocumentMetadata
  programs: string[]
  validationErrors?: Record<string, string>
  showApplyAll?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  fileIndex: undefined,
  validationErrors: () => ({}),
  showApplyAll: true,
})

const emit = defineEmits<{
  update: [metadata: DocumentMetadata]
  applyToAll: []
}>()

// ============================================================================
// State
// ============================================================================

/**
 * Form state (local copy of metadata)
 */
const formState = ref<DocumentMetadata>({
  ...props.metadata,
})

/**
 * Tag input field value
 */
const tagInput = ref('')

// ============================================================================
// Constants
// ============================================================================

/**
 * Document type options
 */
const documentTypeOptions: DocumentType[] = [
  'Grant Proposal',
  'Annual Report',
  'Program Description',
  'Impact Report',
  'Strategic Plan',
  'Other',
]

/**
 * Document outcome options
 */
const outcomeOptions: DocumentOutcome[] = [
  'N/A',
  'Funded',
  'Not Funded',
  'Pending',
  'Final Report',
]

/**
 * Current year (for year validation)
 */
const maxYear = new Date().getFullYear() + 1

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Program options for multi-select
 */
const programOptions = computed(() => {
  return props.programs.map((program) => ({
    label: program,
    value: program,
  }))
})

/**
 * Check if there are validation errors
 */
const hasValidationErrors = computed(() => {
  return Object.keys(props.validationErrors || {}).length > 0
})

// ============================================================================
// Event Handlers
// ============================================================================

/**
 * Handle field change - emit update to parent
 */
const handleFieldChange = () => {
  emit('update', {
    ...formState.value,
  })
}

/**
 * Add a tag to the tags array
 */
const addTag = () => {
  const tag = tagInput.value.trim().replace(/,$/, '') // Remove trailing comma

  if (tag && !formState.value.tags.includes(tag)) {
    formState.value.tags.push(tag)
    tagInput.value = ''
    handleFieldChange()
  }
}

/**
 * Remove a tag from the tags array
 */
const removeTag = (tagToRemove: string) => {
  formState.value.tags = formState.value.tags.filter((tag) => tag !== tagToRemove)
  handleFieldChange()
}

/**
 * Remove a program from the programs array
 */
const removeProgram = (programToRemove: string) => {
  formState.value.programs = formState.value.programs.filter((program) => program !== programToRemove)
  handleFieldChange()
}

/**
 * Handle form submit (not used, but required for UForm)
 */
const handleSubmit = () => {
  // Form submission is handled by parent component
  handleFieldChange()
}

// ============================================================================
// Watch for metadata changes from parent
// ============================================================================

watch(
  () => props.metadata,
  (newMetadata) => {
    formState.value = {
      ...newMetadata,
    }
  },
  { deep: true }
)
</script>
