/**
 * Authentication Composable
 *
 * Provides authentication state management and operations for the Org Archivist application.
 *
 * Features:
 * - JWT token management with secure httpOnly cookies
 * - User session state tracking
 * - Login/logout operations
 * - Session validation
 * - Role-based access control (RBAC)
 * - Automatic token refresh (handled by useApi)
 *
 * @example
 * ```ts
 * const { user, isAuthenticated, login, logout, validateSession, hasRole } = useAuth()
 *
 * // Login
 * const result = await login('user@example.com', 'password')
 * if (result.success) {
 *   console.log('Logged in as:', user.value.email)
 * }
 *
 * // Check authentication
 * if (isAuthenticated.value) {
 *   console.log('User is authenticated')
 * }
 *
 * // Check role
 * if (hasRole('admin')) {
 *   console.log('User is an admin')
 * }
 *
 * // Logout
 * await logout()
 * ```
 */

import type { UserRole, UserResponse, LoginResponse, SessionResponse } from '~/types/api'

/**
 * Login result type
 */
export interface LoginResult {
  success: boolean
  error?: string
}

/**
 * Authentication composable for managing user authentication and session state
 */
export const useAuth = () => {
  // ============================================================================
  // Token Management (Secure httpOnly Cookies)
  // ============================================================================

  /**
   * Access token cookie (5 hours expiration)
   */
  const accessToken = useCookie('access_token', {
    maxAge: 5 * 60 * 60, // 5 hours
    secure: true,
    sameSite: 'strict',
  })

  /**
   * Refresh token cookie (7 days expiration)
   */
  const refreshToken = useCookie('refresh_token', {
    maxAge: 7 * 24 * 60 * 60, // 7 days
    secure: true,
    sameSite: 'strict',
  })

  // ============================================================================
  // User State Management
  // ============================================================================

  /**
   * Current authenticated user state
   * Persisted across page refreshes using useState
   */
  const user = useState<UserResponse | null>('user', () => null)

  /**
   * Computed property indicating if user is authenticated
   * User is authenticated if both access token exists and user object is set
   */
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)

  // ============================================================================
  // Authentication Operations
  // ============================================================================

  /**
   * Login user with email and password
   *
   * @param email - User email address
   * @param password - User password
   * @returns Login result with success status and optional error message
   *
   * @example
   * ```ts
   * const { login } = useAuth()
   * const result = await login('user@example.com', 'password')
   *
   * if (result.success) {
   *   navigateTo('/dashboard')
   * } else {
   *   showError(result.error)
   * }
   * ```
   */
  const login = async (email: string, password: string): Promise<LoginResult> => {
    const { apiFetch } = usePublicApi()

    try {
      const response = await apiFetch<LoginResponse>('/api/auth/login', {
        method: 'POST',
        body: { email, password },
      })

      // Store tokens in secure cookies
      accessToken.value = response.access_token
      refreshToken.value = response.refresh_token

      // Store user information in state
      user.value = response.user

      return { success: true }
    } catch (error: any) {
      // Extract error message from API response
      const errorMessage = error.data?.detail || error.message || 'Login failed'

      return {
        success: false,
        error: errorMessage,
      }
    }
  }

  /**
   * Logout current user and clear authentication state
   *
   * Calls the backend logout endpoint to invalidate the session,
   * then clears all local authentication state and redirects to login.
   *
   * @example
   * ```ts
   * const { logout } = useAuth()
   * await logout()
   * ```
   */
  const logout = async () => {
    const { apiFetch } = useApi()

    try {
      // Call backend logout endpoint to invalidate session
      await apiFetch('/api/auth/logout', {
        method: 'POST',
      })
    } catch (error) {
      // Log error but continue with local cleanup
      console.error('Logout error:', error)
    } finally {
      // Clear all authentication state
      accessToken.value = null
      refreshToken.value = null
      user.value = null

      // Redirect to login page
      navigateTo('/login')
    }
  }

  /**
   * Validate current session with backend
   *
   * Checks if the current access token is valid and retrieves
   * fresh user data from the backend. Updates user state if valid.
   *
   * @returns True if session is valid, false otherwise
   *
   * @example
   * ```ts
   * const { validateSession } = useAuth()
   *
   * // Validate on app mount or route change
   * onMounted(async () => {
   *   const isValid = await validateSession()
   *   if (!isValid) {
   *     navigateTo('/login')
   *   }
   * })
   * ```
   */
  const validateSession = async (): Promise<boolean> => {
    // No access token means not authenticated
    if (!accessToken.value) {
      return false
    }

    const { apiFetch } = useApi()

    try {
      const response = await apiFetch<SessionResponse>('/api/auth/session', {
        method: 'GET',
      })

      // Session is valid and user data returned
      if (response.valid && response.user) {
        user.value = response.user
        return true
      }

      return false
    } catch (error) {
      // Session validation failed (likely 401 Unauthorized)
      // Token refresh will be attempted automatically by useApi
      return false
    }
  }

  /**
   * Check if current user has specified role(s)
   *
   * @param role - Single role or array of roles to check
   * @returns True if user has at least one of the specified roles
   *
   * @example
   * ```ts
   * const { hasRole } = useAuth()
   *
   * // Check single role
   * if (hasRole('admin')) {
   *   // Show admin menu
   * }
   *
   * // Check multiple roles (OR logic)
   * if (hasRole(['admin', 'editor'])) {
   *   // Allow editing
   * }
   * ```
   */
  const hasRole = (role: UserRole | UserRole[]): boolean => {
    if (!user.value) {
      return false
    }

    const roles = Array.isArray(role) ? role : [role]
    return roles.includes(user.value.role)
  }

  /**
   * Check if current user is admin
   *
   * Convenience method for checking admin role
   *
   * @returns True if user has admin role
   *
   * @example
   * ```ts
   * const { isAdmin } = useAuth()
   *
   * if (isAdmin.value) {
   *   // Show admin settings
   * }
   * ```
   */
  const isAdmin = computed(() => hasRole('admin'))

  /**
   * Check if current user is editor or admin
   *
   * Convenience method for checking editor permissions
   *
   * @returns True if user has editor or admin role
   *
   * @example
   * ```ts
   * const { canEdit } = useAuth()
   *
   * if (canEdit.value) {
   *   // Allow document editing
   * }
   * ```
   */
  const canEdit = computed(() => hasRole(['admin', 'editor']))

  // ============================================================================
  // Return Public API
  // ============================================================================

  return {
    // State
    user,
    isAuthenticated,
    accessToken,
    refreshToken,

    // Computed helpers
    isAdmin,
    canEdit,

    // Operations
    login,
    logout,
    validateSession,
    hasRole,
  }
}
