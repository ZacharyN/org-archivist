<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <!-- TopBar Navigation -->
    <LayoutTopBar :show-notifications="false" />

    <!-- Main Content Area -->
    <main class="container mx-auto px-4 py-8">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
/**
 * Default Layout
 *
 * Main application layout with TopBar navigation.
 * Used by all authenticated pages.
 */
</script>
