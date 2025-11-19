<template>
  <div class="container mx-auto px-4 py-8 max-w-5xl">
    <!-- Page Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
        Upload Documents
      </h1>
      <p class="text-gray-600 dark:text-gray-400">
        Add new documents to your organization's library for AI-powered writing assistance
      </p>
    </div>

    <!-- Progress Steps -->
    <div class="mb-8">
      <UStepper
        v-model="currentStepIndex"
        :items="steps"
        :linear="true"
        :disabled="isUploadInProgress"
        class="w-full"
        @update:model-value="handleStepChange"
      />
    </div>

    <!-- Step Content -->
    <div class="min-h-[600px]">
      <!-- Step 1: File Upload -->
      <div v-show="currentStep === 1">
        <FileUploadStep
          ref="fileUploadStepRef"
          @continue="handleFileUploadContinue"
          @cancel="handleCancel"
        />
      </div>

      <!-- Step 2: Metadata -->
      <div v-show="currentStep === 2">
        <MetadataFormStep
          v-if="selectedFiles.length > 0"
          ref="metadataFormStepRef"
          :files="selectedFiles"
          :programs="availablePrograms"
          @continue="handleMetadataContinue"
          @back="handleBack"
        />
      </div>

      <!-- Step 3: Sensitivity Confirmation -->
      <div v-show="currentStep === 3">
        <SensitivityConfirmationStep
          ref="sensitivityStepRef"
          :file-count="selectedFiles.length"
          @continue="handleSensitivityContinue"
          @back="handleBack"
        />
      </div>

      <!-- Step 4: Upload Progress -->
      <div v-show="currentStep === 4">
        <UploadProgressStep
          v-if="selectedFiles.length > 0 && documentMetadata"
          ref="uploadProgressStepRef"
          :files="selectedFiles"
          :metadata="documentMetadata"
          @complete="handleUploadComplete"
          @upload-more="handleUploadMore"
          @go-to-library="handleGoToLibrary"
          @back="handleBack"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Document Upload Wizard Page
 *
 * Multi-step wizard for uploading documents to the organization's library.
 *
 * Steps:
 * 1. File Upload - Select files with drag-and-drop
 * 2. Metadata - Add metadata for each document
 * 3. Sensitivity Confirmation - Confirm documents are public-facing
 * 4. Upload Progress - Real-time upload status and completion
 *
 * Features:
 * - USteps progress indicator
 * - Step validation before progression
 * - Back navigation (except during upload)
 * - State management across steps
 * - Integration with useDocuments composable
 */

import type { DocumentMetadata } from '~/types/api'

// ============================================================================
// Page Metadata
// ============================================================================

definePageMeta({
  title: 'Upload Documents',
  description: 'Upload new documents to your organization library',
  middleware: 'auth',
  auth: {
    roles: ['admin', 'editor']
  },
  layout: 'default',
})

// ============================================================================
// Composables
// ============================================================================

const router = useRouter()
const toast = useToast()

// ============================================================================
// State
// ============================================================================

/**
 * Current wizard step index (0-3 for UStepper)
 */
const currentStepIndex = ref(0)

/**
 * Current wizard step (1-4 for display/logic)
 */
const currentStep = computed(() => currentStepIndex.value + 1)

/**
 * Track if upload is in progress
 */
const isUploadInProgress = ref(false)

/**
 * Selected files from step 1
 */
const selectedFiles = ref<File[]>([])

/**
 * Document metadata from step 2
 */
const documentMetadata = ref<Record<string, DocumentMetadata> | null>(null)

/**
 * Sensitivity confirmed flag from step 3
 */
const sensitivityConfirmed = ref(false)

/**
 * Available programs for metadata form
 * TODO: Fetch from programs API when available
 */
const availablePrograms = ref<string[]>([
  'Education',
  'Youth Development',
  'Community Health',
  'Environmental Justice',
  'Arts & Culture',
])

// ============================================================================
// Component Refs
// ============================================================================

const fileUploadStepRef = ref<any>(null)
const metadataFormStepRef = ref<any>(null)
const sensitivityStepRef = ref<any>(null)
const uploadProgressStepRef = ref<any>(null)

// ============================================================================
// Steps Configuration
// ============================================================================

/**
 * UStepper configuration
 */
const steps = computed(() => [
  {
    title: 'Upload Files',
    description: 'Select documents to upload',
    icon: 'i-heroicons-arrow-up-tray',
    disabled: false,
  },
  {
    title: 'Add Metadata',
    description: 'Provide document information',
    icon: 'i-heroicons-document-text',
    disabled: selectedFiles.value.length === 0,
  },
  {
    title: 'Confirm Sensitivity',
    description: 'Verify document appropriateness',
    icon: 'i-heroicons-shield-check',
    disabled: !documentMetadata.value,
  },
  {
    title: 'Upload',
    description: 'Processing documents',
    icon: 'i-heroicons-cloud-arrow-up',
    disabled: !sensitivityConfirmed.value,
  },
])

// ============================================================================
// Navigation Handlers
// ============================================================================

/**
 * Handle step change from UStepper click
 * Only allow navigation to completed or current step
 */
const handleStepChange = (value: string | number | undefined) => {
  const newStepIndex = typeof value === 'string' ? parseInt(value, 10) : value
  if (newStepIndex === undefined) return

  // Don't allow navigation during upload (step 4, index 3)
  if (currentStepIndex.value === 3 && isUploadInProgress.value) {
    return
  }

  // UStepper with linear:true handles forward navigation restrictions
  // We just need to prevent navigation during upload
  currentStepIndex.value = newStepIndex
}

/**
 * Navigate to previous step
 */
const handleBack = () => {
  if (currentStepIndex.value > 0 && currentStepIndex.value < 3) {
    currentStepIndex.value--
  }
}

/**
 * Cancel upload and return to library
 */
const handleCancel = () => {
  // Show confirmation dialog
  if (selectedFiles.value.length > 0) {
    // TODO: Add confirmation modal
    // For now, just navigate away
  }

  router.push('/documents')
}

// ============================================================================
// Step 1: File Upload Handlers
// ============================================================================

/**
 * Handle file upload step completion
 */
const handleFileUploadContinue = (files: File[]) => {
  selectedFiles.value = files

  toast.add({
    title: 'Files Selected',
    description: `${files.length} ${files.length === 1 ? 'file' : 'files'} ready for upload`,
    color: 'success',
    icon: 'i-heroicons-check-circle',
  })

  // Move to metadata step (index 1)
  currentStepIndex.value = 1
}

// ============================================================================
// Step 2: Metadata Handlers
// ============================================================================

/**
 * Handle metadata form step completion
 */
const handleMetadataContinue = (metadata: Record<string, DocumentMetadata>) => {
  documentMetadata.value = metadata

  toast.add({
    title: 'Metadata Added',
    description: 'Document information saved successfully',
    color: 'success',
    icon: 'i-heroicons-check-circle',
  })

  // Move to sensitivity confirmation step (index 2)
  currentStepIndex.value = 2
}

// ============================================================================
// Step 3: Sensitivity Confirmation Handlers
// ============================================================================

/**
 * Handle sensitivity confirmation step completion
 */
const handleSensitivityContinue = () => {
  sensitivityConfirmed.value = true

  toast.add({
    title: 'Confirmed',
    description: 'Document sensitivity confirmed',
    color: 'success',
    icon: 'i-heroicons-check-circle',
  })

  // Move to upload step (index 3)
  currentStepIndex.value = 3
  isUploadInProgress.value = true
}

// ============================================================================
// Step 4: Upload Progress Handlers
// ============================================================================

/**
 * Handle upload completion
 */
const handleUploadComplete = (results: { successful: string[]; failed: string[] }) => {
  const { successful, failed } = results

  // Mark upload as no longer in progress
  isUploadInProgress.value = false

  if (failed.length === 0) {
    // All uploads successful
    toast.add({
      title: 'Upload Complete',
      description: `Successfully uploaded ${successful.length} ${successful.length === 1 ? 'document' : 'documents'}`,
      color: 'success',
      icon: 'i-heroicons-check-circle',
    })
  } else if (successful.length === 0) {
    // All uploads failed
    toast.add({
      title: 'Upload Failed',
      description: 'All documents failed to upload. Please check the errors and try again.',
      color: 'error',
      icon: 'i-heroicons-x-circle',
    })
  } else {
    // Partial success
    toast.add({
      title: 'Upload Completed with Errors',
      description: `${successful.length} successful, ${failed.length} failed`,
      color: 'warning',
      icon: 'i-heroicons-exclamation-triangle',
    })
  }
}

/**
 * Handle "Upload More Documents" action
 */
const handleUploadMore = () => {
  // Reset wizard state
  resetWizard()

  toast.add({
    title: 'Ready for New Upload',
    description: 'You can now select new documents to upload',
    color: 'info',
    icon: 'i-heroicons-information-circle',
  })
}

/**
 * Handle "Go to Library" action
 */
const handleGoToLibrary = () => {
  router.push('/documents')
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Reset wizard to initial state
 */
const resetWizard = () => {
  currentStepIndex.value = 0
  selectedFiles.value = []
  documentMetadata.value = null
  sensitivityConfirmed.value = false
  isUploadInProgress.value = false

  // Reset child components
  fileUploadStepRef.value?.reset()
  metadataFormStepRef.value?.reset()
  sensitivityStepRef.value?.reset()
  uploadProgressStepRef.value?.reset()
}

// ============================================================================
// Lifecycle Hooks
// ============================================================================

/**
 * Cleanup on unmount
 */
onUnmounted(() => {
  // Clear any temporary state
})

/**
 * Handle browser back button / navigation guard
 */
onBeforeRouteLeave((to, from, next) => {
  // If upload is in progress, confirm before leaving
  if (isUploadInProgress.value) {
    const confirmed = confirm('Upload is in progress. Are you sure you want to leave?')
    if (!confirmed) {
      next(false)
      return
    }
  }

  next()
})
</script>

<style scoped>
/* Add any custom styles here if needed */

/* Smooth transitions between steps */
[v-show] {
  transition: opacity 0.2s ease-in-out;
}
</style>
