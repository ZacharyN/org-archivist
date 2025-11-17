<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4 py-12">
    <UCard class="w-full max-w-md">
      <template #header>
        <div class="text-center space-y-2">
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
            Welcome to Org Archivist
          </h1>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Sign in to your account to continue
          </p>
        </div>
      </template>

      <!-- Error Alert -->
      <UAlert
        v-if="error"
        color="red"
        variant="soft"
        icon="i-heroicons-exclamation-triangle"
        :title="error"
        :close-button="{ icon: 'i-heroicons-x-mark', color: 'red', variant: 'link' }"
        @close="error = null"
        class="mb-4"
      />

      <!-- Login Form -->
      <UForm :state="form" :validate="validate" @submit="handleSubmit" class="space-y-4">
        <!-- Email Field -->
        <UFormGroup label="Email" name="email" required>
          <UInput
            v-model="form.email"
            type="email"
            placeholder="your.email@example.com"
            icon="i-heroicons-envelope"
            :disabled="loading"
            autocomplete="email"
            size="lg"
          />
        </UFormGroup>

        <!-- Password Field -->
        <UFormGroup label="Password" name="password" required>
          <UInput
            v-model="form.password"
            :type="showPassword ? 'text' : 'password'"
            placeholder="Enter your password"
            icon="i-heroicons-lock-closed"
            :disabled="loading"
            autocomplete="current-password"
            size="lg"
            :ui="{
              icon: { trailing: { pointer: '' } }
            }"
          >
            <template #trailing>
              <UButton
                :icon="showPassword ? 'i-heroicons-eye-slash' : 'i-heroicons-eye'"
                color="gray"
                variant="link"
                :padded="false"
                @click="showPassword = !showPassword"
                tabindex="-1"
              />
            </template>
          </UInput>
        </UFormGroup>

        <!-- Remember Me Checkbox -->
        <div class="flex items-center justify-between">
          <UCheckbox
            v-model="form.rememberMe"
            label="Remember me"
            :disabled="loading"
          />

          <!-- Future: Password reset link -->
          <!-- <NuxtLink
            to="/forgot-password"
            class="text-sm text-primary-600 hover:text-primary-500"
          >
            Forgot password?
          </NuxtLink> -->
        </div>

        <!-- Submit Button -->
        <UButton
          type="submit"
          color="primary"
          size="lg"
          block
          :loading="loading"
          :disabled="loading"
        >
          {{ loading ? 'Signing in...' : 'Sign in' }}
        </UButton>
      </UForm>

      <template #footer>
        <div class="text-center text-sm text-gray-500 dark:text-gray-400">
          <p>
            Org Archivist helps nonprofit organizations manage documents and create grant proposals with AI assistance.
          </p>
        </div>
      </template>
    </UCard>
  </div>
</template>

<script setup lang="ts">
/**
 * Login Page Component
 *
 * Provides user authentication with email and password.
 * Features:
 * - Form validation
 * - Loading states
 * - Error handling
 * - Password visibility toggle
 * - Remember me option (cosmetic - token management is automatic)
 * - Redirect to dashboard on success
 */

// SEO and Meta
definePageMeta({
  layout: false, // Login page doesn't use the default layout with sidebar
  middleware: ['guest'], // Only allow unauthenticated users (to be created)
})

useHead({
  title: 'Sign In - Org Archivist',
  meta: [
    {
      name: 'description',
      content: 'Sign in to Org Archivist to manage your nonprofit documents and create AI-powered grant proposals.'
    }
  ]
})

// ============================================================================
// State Management
// ============================================================================

const { login } = useAuth()
const router = useRouter()

// Form state
const form = ref({
  email: '',
  password: '',
  rememberMe: false
})

// UI state
const loading = ref(false)
const error = ref<string | null>(null)
const showPassword = ref(false)

// ============================================================================
// Form Validation
// ============================================================================

/**
 * Validate form inputs
 * Returns validation errors for each field
 */
const validate = (state: typeof form.value) => {
  const errors: any = []

  // Email validation
  if (!state.email) {
    errors.push({
      path: 'email',
      message: 'Email is required'
    })
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(state.email)) {
    errors.push({
      path: 'email',
      message: 'Please enter a valid email address'
    })
  }

  // Password validation
  if (!state.password) {
    errors.push({
      path: 'password',
      message: 'Password is required'
    })
  } else if (state.password.length < 6) {
    errors.push({
      path: 'password',
      message: 'Password must be at least 6 characters'
    })
  }

  return errors
}

// ============================================================================
// Form Submission
// ============================================================================

/**
 * Handle form submission
 * Attempts to log in the user and redirects to dashboard on success
 */
const handleSubmit = async () => {
  // Clear previous errors
  error.value = null
  loading.value = true

  try {
    // Attempt login
    const result = await login(form.value.email, form.value.password)

    if (result.success) {
      // Login successful - redirect to dashboard
      await router.push('/')
    } else {
      // Login failed - show error message
      error.value = result.error || 'Login failed. Please try again.'
    }
  } catch (err: any) {
    // Unexpected error occurred
    console.error('Login error:', err)
    error.value = 'An unexpected error occurred. Please try again later.'
  } finally {
    loading.value = false
  }
}

// ============================================================================
// Keyboard Shortcuts
// ============================================================================

/**
 * Handle Enter key press for form submission
 * This is handled automatically by UForm, but we can add additional shortcuts here if needed
 */
onMounted(() => {
  // Auto-focus email field on mount
  const emailInput = document.querySelector('input[type="email"]') as HTMLInputElement
  if (emailInput) {
    emailInput.focus()
  }
})
</script>

<style scoped>
/* Additional custom styles if needed */
/* Nuxt UI handles most styling through Tailwind classes */
</style>
