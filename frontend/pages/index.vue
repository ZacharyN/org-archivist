<template>
  <div class="space-y-6">
    <UCard>
      <template #header>
        <div class="flex items-center gap-2">
          <UIcon name="i-heroicons-check-circle" class="text-green-500" />
          <h2 class="text-xl font-semibold">Nuxt 4 Setup Complete</h2>
        </div>
      </template>

      <div class="space-y-4">
        <p>Welcome to the Org Archivist Nuxt 4 frontend!</p>

        <UButton
          label="Test Nuxt UI"
          color="primary"
          @click="testBackend"
        />

        <div v-if="healthStatus" class="mt-4">
          <UAlert
            :color="healthStatus.ok ? 'success' : 'error'"
            :title="healthStatus.ok ? 'Backend Connected' : 'Backend Error'"
            :description="healthStatus.message"
          />
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import type { HealthCheckResponse } from '~/types/api'

// Protect this route - require authentication
definePageMeta({
  middleware: 'auth'
})

const healthStatus = ref<{ok: boolean, message: string} | null>(null)

const testBackend = async () => {
  try {
    const config = useRuntimeConfig()
    const response = await $fetch<HealthCheckResponse>(`${config.public.apiBase}/api/health`)
    healthStatus.value = {
      ok: response.status === 'healthy',
      message: `Successfully connected to backend API (v${response.version})`
    }
  } catch (error) {
    healthStatus.value = {
      ok: false,
      message: `Failed to connect: ${error}`
    }
  }
}
</script>
