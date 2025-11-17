<template>
  <aside
    :class="[
      'flex flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700',
      'transition-all duration-300',
      isCollapsed ? 'w-16' : 'w-64',
    ]"
  >
    <!-- Sidebar Header with Toggle/Close -->
    <div class="flex items-center justify-between h-16 px-4 border-b border-gray-200 dark:border-gray-700">
      <span
        v-if="!isCollapsed"
        class="text-sm font-semibold text-gray-700 dark:text-gray-200"
      >
        Navigation
      </span>

      <!-- Desktop/Tablet: Toggle button -->
      <UButton
        icon="i-heroicons-bars-3"
        color="gray"
        variant="ghost"
        size="sm"
        :ui="{ rounded: 'rounded-full' }"
        :aria-label="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        class="hidden lg:flex"
        @click="toggleSidebar"
      />

      <!-- Mobile: Close button -->
      <UButton
        icon="i-heroicons-x-mark"
        color="gray"
        variant="ghost"
        size="sm"
        :ui="{ rounded: 'rounded-full' }"
        aria-label="Close sidebar"
        class="lg:hidden"
        @click="emit('closeMobile')"
      />
    </div>

    <!-- Navigation Items -->
    <nav class="flex-1 overflow-y-auto py-4 px-2 space-y-1">
      <template v-for="item in visibleNavigationItems" :key="item.to">
        <!-- Navigation Link -->
        <NuxtLink
          :to="item.to"
          :class="[
            'group flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
            'hover:bg-gray-100 dark:hover:bg-gray-700',
            isActiveRoute(item.to)
              ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 font-medium'
              : 'text-gray-700 dark:text-gray-300',
          ]"
          :aria-label="item.label"
          :title="isCollapsed ? item.label : undefined"
        >
          <!-- Icon -->
          <UIcon
            :name="item.icon"
            :class="[
              'w-5 h-5 flex-shrink-0',
              isActiveRoute(item.to)
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-gray-500 dark:text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-200',
            ]"
          />

          <!-- Label (hidden when collapsed) -->
          <span
            v-if="!isCollapsed"
            class="flex-1 text-sm"
          >
            {{ item.label }}
          </span>

          <!-- Badge (hidden when collapsed) -->
          <UBadge
            v-if="!isCollapsed && item.badge"
            :color="item.badgeColor || 'primary'"
            size="xs"
            variant="subtle"
          >
            {{ item.badge }}
          </UBadge>
        </NuxtLink>
      </template>
    </nav>

    <!-- Sidebar Footer (Optional) -->
    <div
      v-if="!isCollapsed"
      class="p-4 border-t border-gray-200 dark:border-gray-700"
    >
      <div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
        <UIcon name="i-heroicons-information-circle" class="w-4 h-4" />
        <span>Org Archivist v1.0</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
/**
 * Sidebar Component
 *
 * Main navigation sidebar with:
 * - Role-based navigation items (admin/editor/writer)
 * - Active route highlighting
 * - Collapsible design (desktop/tablet)
 * - Mobile drawer overlay with close button
 * - Badge support for highlighting features
 *
 * @example
 * ```vue
 * <Sidebar :is-mobile-open="false" @close-mobile="handleClose" />
 * ```
 */

// ============================================================================
// Props & Emits
// ============================================================================

interface Props {
  /**
   * Whether the mobile sidebar drawer is open
   * Only relevant on mobile screens
   */
  isMobileOpen?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isMobileOpen: false,
})

/**
 * Emitted when the mobile sidebar should close
 * Parent component should update isMobileOpen
 */
const emit = defineEmits<{
  closeMobile: []
}>()

// ============================================================================
// Types
// ============================================================================

interface NavigationItem {
  label: string
  icon: string
  to: string
  badge?: string
  badgeColor?: 'primary' | 'green' | 'yellow' | 'red'
  roles?: Array<'admin' | 'editor' | 'writer'>
}

// ============================================================================
// Composables & State
// ============================================================================

const { user, hasRole } = useAuth()
const route = useRoute()

/**
 * Sidebar collapsed state
 * Persisted in localStorage for user preference
 */
const isCollapsed = ref(false)

// ============================================================================
// Navigation Items Configuration
// ============================================================================

/**
 * All navigation items with role-based visibility
 * Items without 'roles' property are visible to all authenticated users
 */
const navigationItems = computed<NavigationItem[]>(() => {
  const items: NavigationItem[] = [
    {
      label: 'Dashboard',
      icon: 'i-heroicons-home',
      to: '/',
    },
    {
      label: 'Chat',
      icon: 'i-heroicons-chat-bubble-left-right',
      to: '/chat',
      badge: 'New',
      badgeColor: 'primary',
    },
    {
      label: 'Documents',
      icon: 'i-heroicons-document-text',
      to: '/documents',
    },
    {
      label: 'Programs',
      icon: 'i-heroicons-rectangle-stack',
      to: '/programs',
      roles: ['admin', 'editor'], // Only admin and editor can see this
    },
    {
      label: 'Writing Styles',
      icon: 'i-heroicons-pencil-square',
      to: '/writing-styles',
    },
    {
      label: 'Past Outputs',
      icon: 'i-heroicons-archive-box',
      to: '/outputs',
    },
  ]

  // Add admin-only items at the end
  if (hasRole('admin')) {
    items.push({
      label: 'Manage Users',
      icon: 'i-heroicons-users',
      to: '/admin/users',
      roles: ['admin'],
    })
  }

  return items
})

/**
 * Filtered navigation items based on user role
 * Only shows items the current user has permission to see
 */
const visibleNavigationItems = computed(() => {
  if (!user.value) {
    return []
  }

  return navigationItems.value.filter((item) => {
    // If item has no role restrictions, show to all
    if (!item.roles || item.roles.length === 0) {
      return true
    }

    // Check if user has at least one of the required roles
    return hasRole(item.roles)
  })
})

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Check if a route is currently active
 * Supports exact match and parent route matching
 *
 * @param to - Route path to check
 * @returns True if route is active
 */
const isActiveRoute = (to: string): boolean => {
  // Exact match for home page
  if (to === '/' && route.path === '/') {
    return true
  }

  // Don't match home for other routes
  if (to === '/' && route.path !== '/') {
    return false
  }

  // Match current route or child routes
  return route.path === to || route.path.startsWith(to + '/')
}

// ============================================================================
// Methods
// ============================================================================

/**
 * Toggle sidebar collapsed state
 */
const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

// ============================================================================
// Lifecycle
// ============================================================================

/**
 * Load collapsed state from localStorage on mount
 */
onMounted(() => {
  if (process.client) {
    const savedState = localStorage.getItem('sidebar-collapsed')
    if (savedState !== null) {
      isCollapsed.value = JSON.parse(savedState)
    }
  }
})

/**
 * Save collapsed state to localStorage when it changes
 */
watch(isCollapsed, (newValue) => {
  if (process.client) {
    localStorage.setItem('sidebar-collapsed', JSON.stringify(newValue))
  }
})
</script>

<style scoped>
/* Additional styles if needed - Nuxt UI handles most styling */

/* Smooth transitions for sidebar width changes */
aside {
  transition: width 0.3s ease;
}

/* Ensure navigation items have consistent height */
nav a {
  min-height: 40px;
}

/* Custom scrollbar for navigation */
nav::-webkit-scrollbar {
  width: 4px;
}

nav::-webkit-scrollbar-track {
  @apply bg-gray-100 dark:bg-gray-800;
}

nav::-webkit-scrollbar-thumb {
  @apply bg-gray-300 dark:bg-gray-600 rounded-full;
}

nav::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-400 dark:bg-gray-500;
}
</style>
