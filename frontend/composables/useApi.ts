/**
 * API Client Composable
 *
 * Provides a configured $fetch instance for making API requests to the backend.
 *
 * Features:
 * - Automatically includes base URL from runtime config
 * - Sets default Content-Type header
 * - Handles authentication tokens (JWT Bearer)
 * - Provides centralized error handling
 * - Type-safe API responses
 *
 * @example
 * ```ts
 * const { apiFetch } = useApi()
 *
 * // GET request
 * const data = await apiFetch<HealthCheckResponse>('/health')
 *
 * // POST request with body
 * const response = await apiFetch<LoginResponse>('/auth/login', {
 *   method: 'POST',
 *   body: { email: 'user@example.com', password: 'password' }
 * })
 *
 * // Authenticated request
 * const docs = await apiFetch<DocumentResponse[]>('/documents', {
 *   headers: { Authorization: `Bearer ${token}` }
 * })
 * ```
 */

import type { ApiError } from '~/types/api'

/**
 * API client configuration options
 */
export interface ApiClientOptions {
  /**
   * Whether to include credentials (cookies) with requests
   * @default false
   */
  credentials?: boolean

  /**
   * Custom headers to include with all requests
   */
  headers?: Record<string, string>

  /**
   * Custom error handler function
   */
  onError?: (error: ApiError) => void
}

/**
 * Create and configure API client
 */
export const useApi = (options: ApiClientOptions = {}) => {
  const config = useRuntimeConfig()
  const { credentials = false, headers: customHeaders = {}, onError } = options

  /**
   * Configured fetch instance for API requests
   *
   * Automatically includes:
   * - Base URL from runtime config
   * - Content-Type: application/json header
   * - Error handling with onResponseError
   */
  const apiFetch = $fetch.create({
    // Base URL from runtime config (e.g., http://localhost:8000 or production URL)
    baseURL: config.public.apiBase,

    // Include credentials if needed (for cookie-based auth)
    credentials: credentials ? 'include' : 'same-origin',

    // Default headers
    headers: {
      'Content-Type': 'application/json',
      ...customHeaders,
    },

    // Response error handler
    onResponseError({ request, response, options }) {
      // Build error object
      const error: ApiError = {
        status: response.status,
        message: response.statusText || 'An error occurred',
        detail: response._data?.detail || response._data?.message,
        errors: response._data?.errors,
      }

      // Log error in development
      if (config.public.environment === 'development') {
        console.error('API Error:', {
          url: request,
          status: error.status,
          message: error.message,
          detail: error.detail,
          errors: error.errors,
        })
      }

      // Call custom error handler if provided
      if (onError) {
        onError(error)
      }

      // Common error handling
      switch (response.status) {
        case 401:
          // Unauthorized - clear auth state and redirect to login
          // Note: This will be implemented when auth composable is created
          if (config.public.environment === 'development') {
            console.warn('401 Unauthorized - auth handling not yet implemented')
          }
          break

        case 403:
          // Forbidden - user doesn't have permission
          if (config.public.environment === 'development') {
            console.warn('403 Forbidden - insufficient permissions')
          }
          break

        case 404:
          // Not found
          if (config.public.environment === 'development') {
            console.warn('404 Not Found:', request)
          }
          break

        case 422:
          // Validation error
          if (config.public.environment === 'development') {
            console.warn('422 Validation Error:', error.errors)
          }
          break

        case 500:
          // Server error
          if (config.public.environment === 'development') {
            console.error('500 Server Error:', error.detail)
          }
          break
      }
    },
  })

  return {
    /**
     * Configured fetch instance for making API requests
     *
     * @example
     * ```ts
     * // Simple GET request
     * const data = await apiFetch<User>('/auth/me')
     *
     * // POST with body
     * const result = await apiFetch('/documents/upload', {
     *   method: 'POST',
     *   body: formData
     * })
     *
     * // With custom headers
     * const docs = await apiFetch('/documents', {
     *   headers: { Authorization: `Bearer ${token}` }
     * })
     * ```
     */
    apiFetch,
  }
}

/**
 * Helper function to create authenticated API fetch instance
 *
 * @param token - JWT access token
 * @returns Configured API fetch instance with Authorization header
 *
 * @example
 * ```ts
 * const { apiFetch } = useAuthenticatedApi(accessToken)
 * const user = await apiFetch<UserResponse>('/auth/me')
 * ```
 */
export const useAuthenticatedApi = (token: string, options: ApiClientOptions = {}) => {
  return useApi({
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  })
}

/**
 * Type helper for extracting response type from API endpoints
 *
 * Usage with composables:
 * ```ts
 * type HealthData = Awaited<ReturnType<typeof apiFetch<HealthCheckResponse>>>
 * ```
 */
export type ApiResponse<T> = Promise<T>
