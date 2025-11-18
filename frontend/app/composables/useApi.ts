/**
 * API Client Composable
 *
 * Provides a configured $fetch instance for making API requests to the backend.
 *
 * Features:
 * - Automatically includes base URL from runtime config
 * - Automatic JWT token injection from cookies
 * - Token refresh on 401 errors
 * - Centralized error handling
 * - Request/response interceptors
 * - Type-safe API responses
 *
 * @example
 * ```ts
 * const { apiFetch } = useApi()
 *
 * // GET request (auth token automatically injected if available)
 * const data = await apiFetch<HealthCheckResponse>('/api/health')
 *
 * // POST request with body
 * const response = await apiFetch<LoginResponse>('/api/auth/login', {
 *   method: 'POST',
 *   body: { email: 'user@example.com', password: 'password' }
 * })
 *
 * // Authenticated request (token auto-injected)
 * const docs = await apiFetch<DocumentResponse[]>('/api/documents')
 * ```
 */

import type { ApiError, LoginResponse } from '~/types/api'

/**
 * API client configuration options
 */
export interface ApiClientOptions {
  /**
   * Whether to skip automatic token injection
   * @default false
   */
  skipAuth?: boolean

  /**
   * Custom headers to include with all requests
   */
  headers?: Record<string, string>

  /**
   * Custom error handler function
   */
  onError?: (error: ApiError) => void

  /**
   * Whether to skip automatic token refresh on 401
   * @default false
   */
  skipRefresh?: boolean
}

/**
 * Global flag to prevent refresh loops
 */
let isRefreshing = false
let refreshPromise: Promise<string | null> | null = null

/**
 * Refresh access token using refresh token
 */
async function refreshAccessToken(): Promise<string | null> {
  // If already refreshing, wait for the existing refresh to complete
  if (isRefreshing && refreshPromise) {
    return refreshPromise
  }

  isRefreshing = true
  const config = useRuntimeConfig()
  const refreshToken = useCookie('refresh_token')

  refreshPromise = (async () => {
    try {
      if (!refreshToken.value) {
        throw new Error('No refresh token available')
      }

      const response = await $fetch<LoginResponse>('/api/auth/refresh', {
        baseURL: config.public.apiBase,
        method: 'POST',
        body: { refresh_token: refreshToken.value },
      })

      // Update tokens in cookies
      const accessToken = useCookie('access_token', {
        maxAge: 5 * 60 * 60, // 5 hours
        secure: true,
        sameSite: 'strict',
      })

      const newRefreshToken = useCookie('refresh_token', {
        maxAge: 7 * 24 * 60 * 60, // 7 days
        secure: true,
        sameSite: 'strict',
      })

      accessToken.value = response.access_token
      newRefreshToken.value = response.refresh_token

      return response.access_token
    } catch (error) {
      // Refresh failed - clear auth state
      const accessToken = useCookie('access_token')
      const refreshToken = useCookie('refresh_token')
      accessToken.value = null
      refreshToken.value = null

      // Redirect to login if not already there
      if (process.client && window.location.pathname !== '/login') {
        navigateTo('/login')
      }

      return null
    } finally {
      isRefreshing = false
      refreshPromise = null
    }
  })()

  return refreshPromise
}

/**
 * Create and configure API client with automatic auth token injection and refresh
 */
export const useApi = (options: ApiClientOptions = {}) => {
  const config = useRuntimeConfig()
  const { skipAuth = false, headers: customHeaders = {}, onError, skipRefresh = false } = options

  /**
   * Configured fetch instance for API requests
   *
   * Automatically includes:
   * - Base URL from runtime config
   * - Content-Type: application/json header
   * - Authorization header with JWT token (if available)
   * - Error handling with automatic token refresh on 401
   */
  const apiFetch = $fetch.create({
    // Base URL from runtime config
    baseURL: config.public.apiBase,

    // Request interceptor - inject auth token
    async onRequest({ options }) {
      // Skip auth injection if explicitly requested (e.g., for login endpoint)
      if (skipAuth) {
        return
      }

      // Initialize headers as a plain object if needed
      const headers: Record<string, string> = {}

      // Copy existing headers
      if (options.headers) {
        Object.assign(headers, options.headers)
      }

      // Get access token from cookie
      const accessToken = useCookie('access_token')

      // Inject Authorization header if token exists
      if (accessToken.value) {
        headers.Authorization = `Bearer ${accessToken.value}`
      }

      // Merge custom headers
      if (customHeaders) {
        Object.assign(headers, customHeaders)
      }

      // Always set Content-Type for JSON requests if not already set
      if (!headers['Content-Type']) {
        headers['Content-Type'] = 'application/json'
      }

      // Set the headers back to options
      options.headers = headers as any
    },

    // Response error handler
    async onResponseError({ request, response, options: fetchOptions }) {
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

      // Handle 401 Unauthorized - attempt token refresh
      if (response.status === 401 && !skipRefresh && !skipAuth) {
        try {
          const newToken = await refreshAccessToken()

          if (newToken) {
            // Build retry headers
            const retryHeaders: Record<string, string> = {}
            if (fetchOptions.headers) {
              Object.assign(retryHeaders, fetchOptions.headers)
            }
            retryHeaders.Authorization = `Bearer ${newToken}`

            // Retry the original request with new token
            const retryOptions = {
              ...fetchOptions,
              headers: retryHeaders as any,
            }

            // Return the retry promise - this will become the response
            return $fetch(request, retryOptions as any)
          }
        } catch (refreshError) {
          // Refresh failed, let it fall through to normal error handling
          if (config.public.environment === 'development') {
            console.error('Token refresh failed:', refreshError)
          }
        }
      }

      // Call custom error handler if provided
      if (onError) {
        onError(error)
      }

      // Common error handling for other status codes
      switch (response.status) {
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
     * // Simple GET request (auth token auto-injected)
     * const data = await apiFetch<User>('/api/auth/me')
     *
     * // POST with body
     * const result = await apiFetch('/api/documents/upload', {
     *   method: 'POST',
     *   body: formData
     * })
     *
     * // With custom headers
     * const docs = await apiFetch('/api/documents', {
     *   headers: { 'X-Custom-Header': 'value' }
     * })
     * ```
     */
    apiFetch,
  }
}

/**
 * Create unauthenticated API client (for login, register, etc.)
 *
 * @example
 * ```ts
 * const { apiFetch } = usePublicApi()
 * const response = await apiFetch<LoginResponse>('/api/auth/login', {
 *   method: 'POST',
 *   body: { email, password }
 * })
 * ```
 */
export const usePublicApi = (options: ApiClientOptions = {}) => {
  return useApi({
    ...options,
    skipAuth: true,
    skipRefresh: true,
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
