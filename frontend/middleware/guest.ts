/**
 * Guest Middleware
 *
 * Redirects authenticated users away from guest-only pages (like login).
 * This prevents logged-in users from accessing the login page.
 *
 * Usage:
 * ```ts
 * // In login.vue or register.vue
 * definePageMeta({
 *   middleware: 'guest'
 * })
 * ```
 */

export default defineNuxtRouteMiddleware(async (to, from) => {
  // ============================================================================
  // Skip middleware on server-side rendering (handled by client)
  // ============================================================================

  if (import.meta.server) {
    return
  }

  // ============================================================================
  // Get authentication state
  // ============================================================================

  const { isAuthenticated, validateSession } = useAuth()

  // ============================================================================
  // Check if user is already authenticated
  // ============================================================================

  if (isAuthenticated.value) {
    // Validate session to ensure token is still valid
    try {
      const sessionValid = await validateSession()

      if (sessionValid) {
        // User is authenticated and session is valid
        // Check if there's a redirect query parameter (from auth middleware)
        const redirect = to.query.redirect as string

        if (redirect && redirect !== '/login') {
          // Redirect to intended destination
          return navigateTo(redirect)
        }

        // No redirect specified - go to home page
        return navigateTo('/')
      }
    } catch (error) {
      // Session validation failed - allow access to login page
      console.error('Guest middleware: Session validation error:', error)
    }
  }

  // ============================================================================
  // User is not authenticated or session is invalid - allow access to guest page
  // ============================================================================
})
