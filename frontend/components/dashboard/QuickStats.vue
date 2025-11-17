<template>
  <UCard>
    <template #header>
      <div class="flex items-center gap-2">
        <UIcon name="i-heroicons-chart-bar" class="w-6 h-6" />
        <h2 class="text-xl font-semibold">Quick Stats</h2>
      </div>
    </template>

    <div v-if="isLoading" class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <!-- Loading skeletons -->
      <div v-for="i in 3" :key="i" class="animate-pulse">
        <div class="bg-gray-200 dark:bg-gray-700 rounded-lg h-24"></div>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <!-- Total Documents Stat -->
      <div
        class="p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer"
        @click="navigateTo('/documents')"
      >
        <div class="flex items-center justify-between mb-2">
          <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-900">
            <UIcon name="i-heroicons-document-text" class="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
        </div>
        <div>
          <p class="text-2xl font-bold text-gray-900 dark:text-white">
            {{ totalDocuments }}
          </p>
          <p class="text-sm text-gray-600 dark:text-gray-400">
            Total Documents
          </p>
        </div>
      </div>

      <!-- Grant Success Rate Stat -->
      <div
        class="p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer"
        @click="navigateTo('/outputs')"
      >
        <div class="flex items-center justify-between mb-2">
          <div class="p-2 rounded-lg bg-green-100 dark:bg-green-900">
            <UIcon name="i-heroicons-chart-bar" class="w-6 h-6 text-green-600 dark:text-green-400" />
          </div>
        </div>
        <div>
          <p class="text-2xl font-bold text-gray-900 dark:text-white">
            {{ successRateDisplay }}
          </p>
          <p class="text-sm text-gray-600 dark:text-gray-400">
            Grant Success Rate
          </p>
        </div>
      </div>

      <!-- Active Conversations Stat -->
      <div
        class="p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer"
        @click="navigateTo('/chat')"
      >
        <div class="flex items-center justify-between mb-2">
          <div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-900">
            <UIcon name="i-heroicons-chat-bubble-left" class="w-6 h-6 text-purple-600 dark:text-purple-400" />
          </div>
        </div>
        <div>
          <p class="text-2xl font-bold text-gray-900 dark:text-white">
            {{ activeConversations }}
          </p>
          <p class="text-sm text-gray-600 dark:text-gray-400">
            Active Conversations
          </p>
        </div>
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
/**
 * QuickStats Dashboard Widget
 *
 * Displays key metrics at a glance:
 * - Total documents uploaded
 * - Grant success rate (if outputs exist)
 * - Active conversations
 *
 * Each stat card is clickable and navigates to the relevant page.
 */

import type { DocumentResponse, OutputStatsResponse, Conversation } from '~/types/api'

// ============================================================================
// State Management
// ============================================================================

// Metrics data
const totalDocuments = ref(0)
const successRate = ref<number | null>(null)
const activeConversations = ref(0)

// Loading state
const isLoading = ref(true)

// ============================================================================
// Computed Properties
// ============================================================================

/**
 * Format success rate for display
 * Shows percentage if data exists, otherwise shows N/A
 */
const successRateDisplay = computed(() => {
  if (successRate.value === null) {
    return 'N/A'
  }
  return `${Math.round(successRate.value)}%`
})

// ============================================================================
// Data Fetching
// ============================================================================

/**
 * Fetch total documents count
 */
const fetchDocumentsCount = async () => {
  try {
    const { apiFetch } = useApi()

    const response = await apiFetch<DocumentResponse[]>('/api/documents')

    if (Array.isArray(response)) {
      totalDocuments.value = response.length
    }
  } catch (error) {
    console.error('Failed to fetch documents count:', error)
    totalDocuments.value = 0
  }
}

/**
 * Fetch grant success rate from outputs stats
 */
const fetchSuccessRate = async () => {
  try {
    const { apiFetch } = useApi()

    const response = await apiFetch<OutputStatsResponse>('/api/outputs/stats')

    // Only set success rate if there are outputs
    if (response && response.total_outputs > 0) {
      successRate.value = response.success_rate
    } else {
      successRate.value = null
    }
  } catch (error) {
    console.error('Failed to fetch success rate:', error)
    successRate.value = null
  }
}

/**
 * Fetch active conversations count
 */
const fetchConversationsCount = async () => {
  try {
    const { apiFetch } = useApi()

    const response = await apiFetch<Conversation[]>('/api/chat')

    if (Array.isArray(response)) {
      activeConversations.value = response.length
    }
  } catch (error) {
    console.error('Failed to fetch conversations count:', error)
    activeConversations.value = 0
  }
}

/**
 * Fetch all stats data in parallel
 */
const fetchStats = async () => {
  isLoading.value = true

  try {
    // Fetch all metrics in parallel for better performance
    await Promise.all([
      fetchDocumentsCount(),
      fetchSuccessRate(),
      fetchConversationsCount()
    ])
  } finally {
    isLoading.value = false
  }
}

// ============================================================================
// Lifecycle Hooks
// ============================================================================

/**
 * Fetch data on component mount
 */
onMounted(() => {
  fetchStats()
})
</script>
