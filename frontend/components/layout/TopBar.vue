<template>
  <header class="sticky top-0 z-40 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
    <div class="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
      <!-- Left Section: Mobile Menu Toggle + Logo & Breadcrumbs -->
      <div class="flex items-center space-x-4 flex-1 min-w-0">
        <!-- Mobile Menu Button Slot -->
        <slot name="mobile-menu" />
        <!-- Organization Logo -->
        <NuxtLink to="/" class="flex-shrink-0 flex items-center space-x-2">
          <div class="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
            <UIcon name="i-heroicons-archive-box" class="w-5 h-5 text-white" />
          </div>
          <span class="hidden sm:inline text-lg font-semibold text-gray-900 dark:text-white">
            Org Archivist
          </span>
        </NuxtLink>

        <!-- Breadcrumb Navigation (Desktop only) -->
        <div class="hidden md:block flex-1 min-w-0">
          <UBreadcrumb
            v-if="breadcrumbItems.length > 0"
            :items="breadcrumbItems"
            :ui="{
              list: 'flex items-center space-x-1',
              separator: 'text-gray-400 dark:text-gray-500',
              item: 'text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
            }"
          />
        </div>
      </div>

      <!-- Right Section: Notifications & User Menu -->
      <div class="flex items-center space-x-3 sm:space-x-4">
        <!-- Notification Bell (Optional - future feature) -->
        <UButton
          v-if="showNotifications"
          icon="i-heroicons-bell"
          color="neutral"
          variant="ghost"
          size="lg"
          class="relative rounded-full"
          aria-label="Notifications"
        >
          <!-- Notification Badge -->
          <span
            v-if="notificationCount > 0"
            class="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white dark:ring-gray-800"
          />
        </UButton>

        <!-- User Menu Dropdown -->
        <UDropdownMenu
          v-if="user"
          :items="userMenuItems"
          :ui="{
            content: 'w-56'
          }"
        >
          <!-- User Avatar & Name Button -->
          <template #default>
            <UButton
              color="neutral"
              variant="ghost"
              class="flex items-center space-x-2 px-2 sm:px-3 rounded-full"
            >
              <!-- User Avatar -->
              <UAvatar
                :alt="user.full_name || user.email"
                size="sm"
                class="bg-primary-500"
              >
                <span class="text-xs font-medium text-white">
                  {{ userInitials }}
                </span>
              </UAvatar>

              <!-- User Name (Desktop only) -->
              <span class="hidden sm:inline text-sm font-medium text-gray-700 dark:text-gray-200">
                {{ userDisplayName }}
              </span>

              <!-- Dropdown Chevron -->
              <UIcon name="i-heroicons-chevron-down" class="w-4 h-4 text-gray-500" />
            </UButton>
          </template>

          <!-- Profile Menu Item -->
          <template #profile>
            <div class="flex flex-col gap-0.5 min-w-0">
              <p class="text-sm font-medium text-gray-900 dark:text-white truncate">
                {{ user.full_name || user.email }}
              </p>
              <p class="text-xs text-gray-500 dark:text-gray-400 truncate">
                {{ user.email }}
              </p>
              <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200">
                  {{ roleLabel }}
                </span>
              </p>
            </div>
          </template>
        </UDropdownMenu>

        <!-- Guest State (Not logged in) -->
        <NuxtLink
          v-else
          to="/login"
          class="text-sm font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300"
        >
          Sign In
        </NuxtLink>
      </div>
    </div>

    <!-- Mobile Breadcrumb (Below header on small screens) -->
    <div v-if="breadcrumbItems.length > 0" class="md:hidden px-4 py-2 border-t border-gray-200 dark:border-gray-700">
      <UBreadcrumb
        :items="breadcrumbItems"
        :ui="{
          list: 'flex items-center flex-wrap gap-1',
          separator: 'text-gray-400 dark:text-gray-500 text-sm',
          item: 'text-sm font-medium text-gray-500 dark:text-gray-400'
        }"
      />
    </div>
  </header>
</template>

<script setup lang="ts">
/**
 * TopBar Component
 *
 * Application top navigation bar with:
 * - Organization logo
 * - Breadcrumb navigation
 * - User avatar and name
 * - User dropdown menu (Profile, Settings, Logout)
 * - Optional notification bell
 * - Responsive design for mobile/tablet
 *
 * @example
 * ```vue
 * <TopBar :show-notifications="true" />
 * ```
 */

import type { DropdownMenuItem } from '@nuxt/ui'

// ============================================================================
// Props
// ============================================================================

interface Props {
  /**
   * Whether to show the notification bell icon
   * @default false
   */
  showNotifications?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showNotifications: false,
})

// ============================================================================
// Composables & State
// ============================================================================

const { user, logout, hasRole } = useAuth()
const route = useRoute()
const router = useRouter()

// Notification state (future feature)
const notificationCount = ref(0)

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * User initials for avatar
 * Extracts first letter of first and last name, or first two letters of email
 */
const userInitials = computed(() => {
  if (!user.value) return '?'

  if (user.value.full_name) {
    const names = user.value.full_name.split(' ')
    if (names.length >= 2) {
      return `${names[0][0]}${names[names.length - 1][0]}`.toUpperCase()
    }
    return user.value.full_name.substring(0, 2).toUpperCase()
  }

  return user.value.email.substring(0, 2).toUpperCase()
})

/**
 * Display name for user
 * Shows full name if available, otherwise email
 */
const userDisplayName = computed(() => {
  if (!user.value) return 'Guest'
  return user.value.full_name || user.value.email.split('@')[0]
})

/**
 * User role label for display
 * Capitalizes the role name
 */
const roleLabel = computed(() => {
  if (!user.value) return ''
  return user.value.role.charAt(0).toUpperCase() + user.value.role.slice(1)
})

/**
 * Breadcrumb items based on current route
 * Automatically generates breadcrumbs from route path
 */
const breadcrumbItems = computed(() => {
  const items: Array<{ label: string; icon?: string; to?: string }> = []

  // Always start with home
  items.push({
    label: 'Home',
    icon: 'i-heroicons-home',
    to: '/',
  })

  // Parse route path into breadcrumb segments
  const pathSegments = route.path.split('/').filter(segment => segment.length > 0)

  // Build breadcrumb items from path
  pathSegments.forEach((segment, index) => {
    const isLast = index === pathSegments.length - 1
    const path = '/' + pathSegments.slice(0, index + 1).join('/')

    // Format segment label (capitalize and replace hyphens)
    const label = segment
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')

    items.push({
      label,
      to: isLast ? undefined : path, // Last item is not a link
    })
  })

  // Don't show breadcrumbs on home page
  return route.path === '/' ? [] : items
})

/**
 * User menu dropdown items
 * Different items shown based on user role
 */
const userMenuItems = computed<DropdownMenuItem[][]>(() => {
  if (!user.value) return []

  const items: DropdownMenuItem[][] = [
    // Profile section
    [
      {
        label: 'Profile Info',
        slot: 'profile',
      },
    ],
    // Navigation items
    [
      {
        label: 'Profile',
        icon: 'i-heroicons-user',
        click: () => router.push('/profile'),
      },
      {
        label: 'Settings',
        icon: 'i-heroicons-cog-6-tooth',
        click: () => router.push('/settings'),
      },
    ],
  ]

  // Admin-only items
  if (hasRole('admin')) {
    items.push([
      {
        label: 'Admin Dashboard',
        icon: 'i-heroicons-shield-check',
        click: () => router.push('/admin'),
      },
    ])
  }

  // Logout item
  items.push([
    {
      label: 'Logout',
      icon: 'i-heroicons-arrow-right-on-rectangle',
      click: handleLogout,
      class: 'text-red-600 dark:text-red-400',
    },
  ])

  return items
})

// ============================================================================
// Methods
// ============================================================================

/**
 * Handle user logout
 * Calls auth logout and clears session
 */
const handleLogout = async () => {
  try {
    await logout()
  } catch (error) {
    console.error('Logout error:', error)
  }
}
</script>

<style scoped>
/* Additional styles if needed - Nuxt UI handles most styling */
</style>
