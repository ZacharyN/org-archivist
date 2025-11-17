<template>
  <div class="space-y-6">
    <UCard>
      <template #header>
        <div class="flex items-center gap-2">
          <UIcon name="i-heroicons-shield-check" class="text-blue-500" />
          <h2 class="text-xl font-semibold">Admin Dashboard</h2>
        </div>
      </template>

      <div class="space-y-4">
        <p class="text-gray-600 dark:text-gray-300">
          This page is only accessible to users with the <strong>admin</strong> role.
        </p>

        <UAlert
          color="blue"
          variant="soft"
          icon="i-heroicons-information-circle"
          title="Admin Access Only"
          description="This page demonstrates role-based access control. Only administrators can view this content."
        />

        <div class="mt-4">
          <h3 class="text-lg font-semibold mb-2">Current User</h3>
          <UCard>
            <dl class="space-y-2">
              <div>
                <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Email</dt>
                <dd class="text-sm text-gray-900 dark:text-white">{{ user?.email }}</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Name</dt>
                <dd class="text-sm text-gray-900 dark:text-white">{{ user?.full_name }}</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Role</dt>
                <dd>
                  <UBadge color="blue" variant="soft">
                    {{ user?.role }}
                  </UBadge>
                </dd>
              </div>
            </dl>
          </UCard>
        </div>

        <div class="flex gap-2 mt-4">
          <UButton
            label="Back to Home"
            color="gray"
            icon="i-heroicons-arrow-left"
            @click="$router.push('/')"
          />
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
/**
 * Admin Dashboard Page
 *
 * This page demonstrates role-based access control.
 * Only users with the 'admin' role can access this page.
 *
 * If a non-admin user tries to access this page, they will be
 * redirected to the home page with an error message.
 */

// Protect this route - require admin role
definePageMeta({
  middleware: 'auth',
  auth: {
    roles: ['admin']
  }
})

useHead({
  title: 'Admin Dashboard - Org Archivist',
  meta: [
    {
      name: 'description',
      content: 'Admin-only dashboard for Org Archivist system administration.'
    }
  ]
})

const { user } = useAuth()
</script>
