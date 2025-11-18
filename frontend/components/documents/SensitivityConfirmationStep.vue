<template>
  <UCard>
    <template #header>
      <div class="flex items-center gap-3">
        <UIcon name="i-heroicons-shield-exclamation" class="text-yellow-500" />
        <div class="flex-1">
          <h3 class="text-lg font-semibold">Document Sensitivity Confirmation</h3>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Step 3: Confirm document appropriateness for AI processing
          </p>
        </div>
      </div>
    </template>

    <div class="space-y-6">
      <!-- Warning Alert -->
      <UAlert
        color="warning"
        variant="soft"
        icon="i-heroicons-exclamation-triangle"
        title="Important: Public Documents Only"
      >
        <template #description>
          <div class="space-y-2">
            <p class="text-sm">
              This system is designed to process <strong>public-facing documents only</strong>.
              Please ensure that you do not upload confidential, financial, or sensitive operational documents.
            </p>
          </div>
        </template>
      </UAlert>

      <!-- Information Card -->
      <UCard
        :ui="{
          body: 'p-5',
          root: sensitivityError ? 'ring-2 ring-red-500' : ''
        }"
      >
        <div class="space-y-4">
          <div class="flex items-start gap-3">
            <UIcon
              name="i-heroicons-check-circle"
              class="text-green-500 mt-1 shrink-0"
              size="20"
            />
            <div class="flex-1">
              <p class="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                Appropriate Documents
              </p>
              <ul class="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-disc list-inside">
                <li>Published grant proposals</li>
                <li>Annual reports</li>
                <li>Public program descriptions</li>
                <li>Impact reports and case studies</li>
                <li>Public newsletters and communications</li>
                <li>Published research and white papers</li>
              </ul>
            </div>
          </div>

          <UDivider />

          <div class="flex items-start gap-3">
            <UIcon
              name="i-heroicons-x-circle"
              class="text-red-500 mt-1 shrink-0"
              size="20"
            />
            <div class="flex-1">
              <p class="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                <strong>Do NOT Upload</strong>
              </p>
              <ul class="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-disc list-inside">
                <li>Financial statements or budgets</li>
                <li>Client or beneficiary personal information</li>
                <li>Confidential donor data</li>
                <li>Internal personnel documents</li>
                <li>Strategic plans not yet public</li>
                <li>Legal documents or contracts</li>
              </ul>
            </div>
          </div>
        </div>
      </UCard>

      <!-- Document Summary -->
      <div class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <div class="flex items-center gap-3">
          <UIcon name="i-heroicons-document-text" class="text-primary" size="24" />
          <div>
            <p class="text-sm font-semibold text-gray-900 dark:text-white">
              Ready to upload
            </p>
            <p class="text-xs text-gray-500 dark:text-gray-400">
              {{ fileCount }} {{ fileCount === 1 ? 'document' : 'documents' }}
            </p>
          </div>
        </div>
      </div>

      <!-- Confirmation Checkbox -->
      <UFormField
        name="sensitivity_confirmation"
        :error="sensitivityError || undefined"
      >
        <div
          class="p-4 rounded-lg border-2"
          :class="sensitivityError ? 'border-red-500 bg-red-50 dark:bg-red-950/20' : 'border-gray-200 dark:border-gray-700'"
        >
          <UCheckbox
            v-model="confirmed"
            :required="true"
          >
            <template #label>
              <span class="text-sm font-medium text-gray-900 dark:text-white">
                I confirm that these documents are public-facing and appropriate for AI processing
              </span>
            </template>
          </UCheckbox>

          <p v-if="!confirmed" class="text-xs text-gray-500 dark:text-gray-400 mt-2 ml-6">
            You must confirm to proceed with the upload
          </p>
        </div>
      </UFormField>

      <!-- Additional Information -->
      <UAlert
        color="info"
        variant="soft"
        icon="i-heroicons-information-circle"
      >
        <template #description>
          <p class="text-xs">
            By confirming, you acknowledge that you have reviewed the documents and they meet the
            criteria for public document processing. If you have questions about whether a document
            is appropriate, please contact your administrator.
          </p>
        </template>
      </UAlert>

      <!-- Actions -->
      <div class="flex items-center justify-between pt-4 border-t">
        <UButton
          label="Back to Metadata"
          color="neutral"
          variant="ghost"
          icon="i-heroicons-arrow-left"
          @click="handleBack"
        />

        <UButton
          label="Continue to Upload"
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
 * SensitivityConfirmationStep Component
 *
 * Step 3 of the document upload wizard. Ensures users confirm that:
 * - Documents are public-facing
 * - Documents are appropriate for AI processing
 * - No confidential or sensitive information is being uploaded
 *
 * This is a critical security and compliance step to prevent accidental
 * upload of sensitive organizational information.
 *
 * @emits continue - Emitted when user confirms and clicks continue
 * @emits back - Emitted when user clicks back button
 */

// ============================================================================
// Props & Emits
// ============================================================================

interface Props {
  fileCount: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  continue: []
  back: []
}>()

// ============================================================================
// State
// ============================================================================

const confirmed = ref(false)
const sensitivityError = ref<string | null>(null)

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Check if user can continue to next step
 */
const canContinue = computed(() => {
  return confirmed.value
})

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
 * Handle continue button click
 */
const handleContinue = () => {
  // Reset error
  sensitivityError.value = null

  // Validate confirmation
  if (!confirmed.value) {
    sensitivityError.value = 'You must confirm that these documents are public-facing and appropriate for AI processing.'
    return
  }

  // Emit continue event
  emit('continue')
}

/**
 * Reset component state
 */
const reset = () => {
  confirmed.value = false
  sensitivityError.value = null
}

// ============================================================================
// Watch for confirmation changes
// ============================================================================

watch(confirmed, (newValue) => {
  if (newValue) {
    sensitivityError.value = null
  }
})

// ============================================================================
// Expose public API
// ============================================================================

defineExpose({
  reset,
  confirmed,
  canContinue,
})
</script>
