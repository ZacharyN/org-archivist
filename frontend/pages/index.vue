<template>
  <div>
    <!-- Dashboard Header -->
    <div class="mb-6">
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
        Dashboard
      </h1>
      <p class="text-gray-600 dark:text-gray-400 mt-1">
        Welcome to Org Archivist - Your AI-powered writing assistant
      </p>
    </div>

    <!-- 2-Column Dashboard Layout -->
    <!-- On desktop: 2:1 ratio (66.67% : 33.33%) using grid-cols-3 -->
    <!-- On mobile: Stack vertically -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left Column (8 units / 2 columns span) -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Chat Quick Start -->
        <DashboardChatQuickStart />

        <!-- Recent Activity -->
        <DashboardRecentActivity />
      </div>

      <!-- Right Column (4 units / 1 column span) -->
      <div class="lg:col-span-1 space-y-6">
        <!-- Setup Checklist -->
        <DashboardSetupChecklist />

        <!-- Quick Stats -->
        <DashboardQuickStats />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Dashboard Page (Home)
 *
 * Main landing page after login with 2-column responsive layout:
 * - Left Column (8 units): ChatQuickStart + RecentActivity
 * - Right Column (4 units): SetupChecklist + QuickStats
 *
 * Layout uses Tailwind grid with 3 columns on desktop:
 * - Left column spans 2 columns (66.67%)
 * - Right column spans 1 column (33.33%)
 * - On mobile: Stacks vertically
 */

// Protect this route - require authentication
definePageMeta({
  middleware: 'auth'
})
</script>
