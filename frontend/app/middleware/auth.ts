/**
 * Authentication Middleware
 *
 * Protects routes that require authentication by checking for valid access tokens
 * and validating the user session with the backend.
 *
 * Features:
 * - Checks for access token presence
 * - Validates session with backend
 * - Redirects to login if unauthenticated
 * - Supports role-based access control (RBAC)
 * - Handles automatic token refresh
 *
 * Usage:
 * ```ts
 * // In page component
 * definePageMeta({
 *   middleware: 'auth'
 * })
 *
 * // Or with role restriction
 * definePageMeta({
 *   middleware: 'auth',
 *   auth: {
 *     roles: ['admin', 'editor']
 *   }
 * })
 * ```
 */

import type { UserRole } from '~/types/api'

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

  const { isAuthenticated, validateSession, user, hasRole } = useAuth()

  // ============================================================================
  // Check if user is authenticated
  // ============================================================================

  // If no access token present, redirect to login
  if (!isAuthenticated.value) {
    return navigateTo({
      path: '/login',
      query: {
        // Preserve the intended destination for redirect after login
        redirect: to.fullPath
      }
    })
  }

  // ============================================================================
  // Validate session with backend
  // ============================================================================

  try {
    const sessionValid = await validateSession()

    if (!sessionValid) {
      // Session is invalid (token expired or revoked)
      // Clear local state and redirect to login
      return navigateTo({
        path: '/login',
        query: {
          redirect: to.fullPath,
          reason: 'session_expired'
        }
      })
    }
  } catch (error) {
    // Session validation failed (network error, server error, etc.)
    console.error('Session validation error:', error)

    return navigateTo({
      path: '/login',
      query: {
        redirect: to.fullPath,
        reason: 'validation_failed'
      }
    })
  }

  // ============================================================================
  // Role-Based Access Control (RBAC)
  // ============================================================================

  // Check if route requires specific roles
  const routeMeta = to.meta.auth as { roles?: UserRole[] } | undefined

  if (routeMeta?.roles && routeMeta.roles.length > 0) {
    const hasRequiredRole = hasRole(routeMeta.roles)

    if (!hasRequiredRole) {
      // User doesn't have required role - redirect to home with error
      console.warn(`User ${user.value?.email} attempted to access ${to.path} without required role`)

      return navigateTo({
        path: '/',
        query: {
          error: 'insufficient_permissions'
        }
      })
    }
  }

  // ============================================================================
  // Session validated and authorized - allow navigation
  // ============================================================================
})
