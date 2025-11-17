# Authentication Middleware Guide

## Overview

The Org Archivist frontend includes two middleware components for managing authentication and route protection:

1. **`auth.ts`** - Protects authenticated routes
2. **`guest.ts`** - Redirects authenticated users away from login/register pages

## Middleware Location

Both middleware files are located in:
```
frontend/middleware/
├── auth.ts
└── guest.ts
```

Nuxt 4 automatically discovers and registers middleware in this directory.

---

## Auth Middleware (`auth.ts`)

### Purpose

Protects routes that require authentication by:
- Checking for valid access tokens
- Validating session with backend
- Redirecting unauthenticated users to login
- Supporting role-based access control (RBAC)

### Basic Usage

To protect a page, add the middleware to `definePageMeta`:

```vue
<script setup lang="ts">
// Protect this route - require authentication
definePageMeta({
  middleware: 'auth'
})
</script>

<template>
  <div>
    <h1>Protected Dashboard</h1>
    <p>Only authenticated users can see this.</p>
  </div>
</template>
```

### Role-Based Access Control

To restrict access to specific user roles:

```vue
<script setup lang="ts">
// Only allow admin and editor roles
definePageMeta({
  middleware: 'auth',
  auth: {
    roles: ['admin', 'editor']
  }
})
</script>

<template>
  <div>
    <h1>Admin Dashboard</h1>
    <p>Only admins and editors can access this page.</p>
  </div>
</template>
```

### Available Roles

- `admin` - Administrator (full system access)
- `editor` - Editor (extended access without user management)
- `writer` - Writer (basic user access)

### Behavior

1. **No Access Token**
   - Redirects to `/login`
   - Preserves intended destination in query parameter
   - Example: `/login?redirect=/dashboard`

2. **Invalid/Expired Session**
   - Validates session with backend
   - If invalid, redirects to `/login?reason=session_expired`
   - Clears local authentication state

3. **Insufficient Permissions**
   - If user lacks required role
   - Redirects to home (`/`)
   - Shows error: `?error=insufficient_permissions`

4. **Successful Authentication**
   - Allows navigation to protected route
   - User and session data available via `useAuth()`

---

## Guest Middleware (`guest.ts`)

### Purpose

Prevents authenticated users from accessing guest-only pages (like login or register).

### Usage

Used on pages that should only be accessible to unauthenticated users:

```vue
<script setup lang="ts">
// Only allow unauthenticated users
definePageMeta({
  middleware: 'guest',
  layout: false  // Login pages typically don't use the default layout
})
</script>

<template>
  <div>
    <h1>Login</h1>
    <form><!-- Login form --></form>
  </div>
</template>
```

### Behavior

1. **User is Authenticated**
   - Validates session with backend
   - If valid, redirects to home (`/`) or intended destination
   - Checks for `redirect` query parameter from auth middleware
   - Example: User goes to `/login?redirect=/dashboard` → redirects to `/dashboard`

2. **User is Not Authenticated**
   - Allows access to the page (login, register, etc.)

3. **Session Validation Fails**
   - Allows access to the page
   - User can attempt to login again

---

## Implementation Details

### How Auth Middleware Works

```typescript
// 1. Check if access token exists
if (!isAuthenticated.value) {
  return navigateTo('/login?redirect=' + to.fullPath)
}

// 2. Validate session with backend
const sessionValid = await validateSession()
if (!sessionValid) {
  return navigateTo('/login?reason=session_expired')
}

// 3. Check role-based permissions
if (routeMeta?.roles && !hasRole(routeMeta.roles)) {
  return navigateTo('/?error=insufficient_permissions')
}

// 4. Allow navigation
```

### How Guest Middleware Works

```typescript
// 1. Check if user is authenticated
if (isAuthenticated.value) {
  // 2. Validate session
  const sessionValid = await validateSession()

  if (sessionValid) {
    // 3. Redirect to home or intended destination
    const redirect = to.query.redirect
    return navigateTo(redirect || '/')
  }
}

// 4. Allow access to guest page
```

---

## Example Page Configurations

### Public Home Page (No Auth Required)

```vue
<script setup lang="ts">
// No middleware - accessible to everyone
</script>

<template>
  <div>
    <h1>Welcome to Org Archivist</h1>
  </div>
</template>
```

### Protected Dashboard (Auth Required)

```vue
<script setup lang="ts">
definePageMeta({
  middleware: 'auth'
})

const { user } = useAuth()
</script>

<template>
  <div>
    <h1>Welcome, {{ user?.full_name }}</h1>
  </div>
</template>
```

### Admin-Only Settings Page

```vue
<script setup lang="ts">
definePageMeta({
  middleware: 'auth',
  auth: {
    roles: ['admin']
  }
})
</script>

<template>
  <div>
    <h1>System Settings</h1>
    <p>Admin access only</p>
  </div>
</template>
```

### Editor or Admin Page

```vue
<script setup lang="ts">
definePageMeta({
  middleware: 'auth',
  auth: {
    roles: ['admin', 'editor']
  }
})
</script>

<template>
  <div>
    <h1>Document Library</h1>
    <p>Upload and manage documents</p>
  </div>
</template>
```

### Login Page (Guest Only)

```vue
<script setup lang="ts">
definePageMeta({
  middleware: 'guest',
  layout: false
})
</script>

<template>
  <div>
    <h1>Login</h1>
    <form><!-- Login form --></form>
  </div>
</template>
```

---

## Common Scenarios

### Redirect After Login

When a user tries to access a protected route while unauthenticated:

1. User navigates to `/dashboard`
2. Auth middleware redirects to `/login?redirect=/dashboard`
3. User logs in successfully
4. Guest middleware checks for `redirect` parameter
5. User is redirected to `/dashboard`

### Session Expiration

When a user's session expires:

1. User tries to access `/documents`
2. Auth middleware validates session
3. Backend returns 401 Unauthorized
4. Middleware redirects to `/login?redirect=/documents&reason=session_expired`
5. Login page shows "Your session has expired" message
6. User logs in again
7. Redirected back to `/documents`

### Insufficient Permissions

When a writer tries to access an admin-only page:

1. Writer navigates to `/admin/users`
2. Auth middleware validates authentication (passes)
3. Middleware checks role requirements: `['admin']`
4. Writer doesn't have admin role
5. Redirects to `/?error=insufficient_permissions`
6. Home page shows "You don't have permission to access that page"

---

## Testing Middleware

### Manual Testing

1. **Test Auth Middleware:**
   ```bash
   # 1. Clear cookies/localStorage (logout)
   # 2. Navigate to /
   # Expected: Redirected to /login

   # 3. Login with valid credentials
   # 4. Navigate to /
   # Expected: Dashboard loads
   ```

2. **Test Guest Middleware:**
   ```bash
   # 1. Login with valid credentials
   # 2. Navigate to /login
   # Expected: Redirected to /
   ```

3. **Test RBAC:**
   ```bash
   # 1. Login as Writer
   # 2. Navigate to admin-only page
   # Expected: Redirected to / with error

   # 3. Login as Admin
   # 4. Navigate to same admin-only page
   # Expected: Page loads successfully
   ```

### Automated Testing

Create tests for middleware behavior:

```typescript
// tests/middleware/auth.spec.ts
import { describe, it, expect } from 'vitest'
import { mountSuspended } from '@nuxt/test-utils/runtime'

describe('Auth Middleware', () => {
  it('redirects unauthenticated users to login', async () => {
    // Test implementation
  })

  it('allows authenticated users to access protected routes', async () => {
    // Test implementation
  })

  it('enforces role-based access control', async () => {
    // Test implementation
  })
})
```

---

## Integration with useAuth Composable

The middleware relies on the `useAuth()` composable which provides:

```typescript
const {
  user,              // Current user object
  isAuthenticated,   // Boolean: is user authenticated?
  validateSession,   // Function: validate session with backend
  hasRole,           // Function: check user roles
  login,             // Function: authenticate user
  logout,            // Function: log out user
  isAdmin,           // Computed: is user admin?
  canEdit            // Computed: can user edit (admin or editor)?
} = useAuth()
```

---

## Best Practices

1. **Always protect sensitive routes**
   - Add `middleware: 'auth'` to any page with user data
   - Use RBAC for admin/editor-only features

2. **Provide clear feedback**
   - Show error messages on permission denied
   - Display session expiration warnings
   - Guide users to login when needed

3. **Handle edge cases**
   - Network errors during session validation
   - Expired tokens
   - Revoked sessions
   - Role changes while logged in

4. **Optimize performance**
   - Cache session validation results
   - Use computed properties for role checks
   - Minimize API calls in middleware

5. **Security considerations**
   - Never trust client-side role checks alone
   - Always validate on backend
   - Use HTTPS in production
   - Implement proper CORS policies

---

## Troubleshooting

### Infinite Redirect Loop

**Problem:** Page keeps redirecting between `/` and `/login`

**Solution:**
- Ensure login page has `middleware: 'guest'`
- Check that home page has `middleware: 'auth'` only if it requires auth
- Verify `isAuthenticated` is working correctly

### Session Validation Fails Silently

**Problem:** Session validation errors not showing to user

**Solution:**
- Check console for errors
- Verify backend `/api/auth/session` endpoint is working
- Ensure error handling in middleware catches all cases

### Role-Based Access Not Working

**Problem:** Users can access pages they shouldn't

**Solution:**
- Verify `auth.roles` in `definePageMeta` is correct
- Check that `user.role` matches expected values
- Ensure backend is returning correct role in user object
- Remember: Backend should also enforce RBAC

---

## Migration from Streamlit

### Previous Implementation

Streamlit used session state for authentication:

```python
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    show_login()
    st.stop()
```

### New Nuxt 4 Implementation

Now using declarative middleware:

```vue
<script setup lang="ts">
definePageMeta({
  middleware: 'auth'
})
</script>
```

**Benefits:**
- Automatic route protection
- Centralized authentication logic
- Better type safety with TypeScript
- Easier to test and maintain
- Supports role-based access control

---

## Related Documentation

- **Authentication Composable:** `frontend/composables/useAuth.ts`
- **API Types:** `frontend/types/api.ts`
- **Frontend Requirements:** `context/frontend-requirements.md`
- **Backend API Guide:** `docs/backend-api-guide.md`
- **Security Improvements:** `docs/security-improvements.md`

---

## Summary

The authentication middleware provides a robust, declarative way to protect routes in the Org Archivist frontend:

✅ Simple `middleware: 'auth'` for authenticated routes
✅ Simple `middleware: 'guest'` for login/register pages
✅ Role-based access control with `auth.roles`
✅ Automatic session validation
✅ Graceful error handling and redirects
✅ Integration with `useAuth()` composable
✅ TypeScript type safety throughout

For questions or issues, refer to the main frontend requirements document or the useAuth composable source code.
