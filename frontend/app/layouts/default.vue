<template>
  <div class="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-900">
    <!-- Mobile Sidebar Backdrop -->
    <div
      v-if="isMobileSidebarOpen"
      class="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 transition-opacity lg:hidden"
      @click="closeMobileSidebar"
    />

    <!-- Sidebar -->
    <!-- Desktop: Always visible, collapsible -->
    <!-- Tablet: Collapsible -->
    <!-- Mobile: Drawer overlay -->
    <aside
      :class="[
        'fixed inset-y-0 left-0 z-50 flex flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700',
        'transition-all duration-300 ease-in-out',
        // Mobile: drawer that slides in from left
        'lg:relative lg:translate-x-0',
        isMobileSidebarOpen ? 'translate-x-0' : '-translate-x-full',
        // Width based on collapsed state (desktop/tablet)
        isSidebarCollapsed ? 'lg:w-16' : 'lg:w-64',
        // Mobile: always full width when open
        'w-64',
      ]"
    >
      <LayoutSidebar
        :is-mobile-open="isMobileSidebarOpen"
        @close-mobile="closeMobileSidebar"
      />
    </aside>

    <!-- Main Content Area -->
    <div class="flex flex-col flex-1 overflow-hidden">
      <!-- TopBar with Mobile Menu Toggle -->
      <header class="relative z-30">
        <LayoutTopBar :show-notifications="false">
          <!-- Mobile Menu Button (slot in TopBar) -->
          <template #mobile-menu>
            <UButton
              icon="i-heroicons-bars-3"
              color="neutral"
              variant="ghost"
              size="lg"
              class="lg:hidden rounded-full"
              aria-label="Open sidebar"
              @click="openMobileSidebar"
            />
          </template>
        </LayoutTopBar>
      </header>

      <!-- Page Content with Overflow Handling -->
      <main class="flex-1 overflow-y-auto overflow-x-hidden bg-gray-50 dark:bg-gray-900">
        <div class="container mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * DefaultLayout Component
 *
 * Main application layout combining TopBar and Sidebar with responsive behavior:
 * - Desktop (≥1024px): Full sidebar visible, collapsible to icon-only
 * - Tablet (768-1023px): Collapsible sidebar
 * - Mobile (<768px): Hidden sidebar, drawer overlay accessible via hamburger menu
 *
 * Features:
 * - Responsive sidebar with smooth transitions
 * - Mobile drawer with backdrop
 * - Flex layout with proper overflow handling
 * - Persistent sidebar state (desktop/tablet)
 * - Auto-close mobile drawer on navigation
 *
 * @example
 * ```vue
 * <template>
 *   <NuxtLayout name="default">
 *     <YourPageContent />
 *   </NuxtLayout>
 * </template>
 * ```
 */

// ============================================================================
// Composables & State
// ============================================================================

const route = useRoute()

/**
 * Mobile sidebar open state
 * Controls drawer visibility on mobile screens
 */
const isMobileSidebarOpen = ref(false)

/**
 * Desktop/tablet sidebar collapsed state
 * Synced with Sidebar component's internal state
 * This is read from localStorage in Sidebar component
 */
const isSidebarCollapsed = ref(false)

// ============================================================================
// Methods
// ============================================================================

/**
 * Open mobile sidebar drawer
 */
const openMobileSidebar = () => {
  isMobileSidebarOpen.value = true
  // Prevent body scroll when drawer is open
  if (process.client) {
    document.body.style.overflow = 'hidden'
  }
}

/**
 * Close mobile sidebar drawer
 */
const closeMobileSidebar = () => {
  isMobileSidebarOpen.value = false
  // Restore body scroll
  if (process.client) {
    document.body.style.overflow = ''
  }
}

// ============================================================================
// Lifecycle & Watchers
// ============================================================================

/**
 * Load sidebar collapsed state from localStorage on mount
 * This syncs with the Sidebar component's internal state
 */
onMounted(() => {
  if (process.client) {
    const savedState = localStorage.getItem('sidebar-collapsed')
    if (savedState !== null) {
      isSidebarCollapsed.value = JSON.parse(savedState)
    }

    // Listen for storage events to sync across tabs
    window.addEventListener('storage', (e) => {
      if (e.key === 'sidebar-collapsed' && e.newValue !== null) {
        isSidebarCollapsed.value = JSON.parse(e.newValue)
      }
    })
  }
})

/**
 * Auto-close mobile sidebar on route change
 * Improves UX by closing drawer when user navigates
 */
watch(
  () => route.path,
  () => {
    if (isMobileSidebarOpen.value) {
      closeMobileSidebar()
    }
  }
)

/**
 * Cleanup: Restore body scroll on unmount
 */
onUnmounted(() => {
  if (process.client) {
    document.body.style.overflow = ''
  }
})

// ============================================================================
// Keyboard Shortcuts
// ============================================================================

/**
 * Handle keyboard shortcuts
 * - Escape: Close mobile sidebar
 * - Cmd/Ctrl + B: Toggle sidebar (desktop/tablet)
 */
onMounted(() => {
  if (process.client) {
    const handleKeydown = (e: KeyboardEvent) => {
      // Escape to close mobile sidebar
      if (e.key === 'Escape' && isMobileSidebarOpen.value) {
        closeMobileSidebar()
      }

      // Cmd/Ctrl + B to toggle sidebar (desktop/tablet only)
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault()
        const newState = !isSidebarCollapsed.value
        isSidebarCollapsed.value = newState
        localStorage.setItem('sidebar-collapsed', JSON.stringify(newState))
      }
    }

    window.addEventListener('keydown', handleKeydown)

    // Cleanup
    onUnmounted(() => {
      window.removeEventListener('keydown', handleKeydown)
    })
  }
})
</script>

<style scoped>
/**
 * Ensure smooth transitions for sidebar
 * Additional styles for layout components
 */

/* Prevent horizontal scrollbar during sidebar transitions */
.overflow-hidden {
  overflow: hidden;
}

/* Smooth sidebar transitions */
aside {
  transition-property: transform, width;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 300ms;
}

/* Backdrop fade transition */
.bg-opacity-75 {
  transition: opacity 300ms ease-in-out;
}

/* Ensure main content doesn't overflow */
main {
  /* Enable GPU acceleration for smooth scrolling */
  -webkit-overflow-scrolling: touch;
}

/* Fix for potential layout shift during transitions */
.container {
  max-width: 100%;
}
</style>
