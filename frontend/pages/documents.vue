<template>
  <div class="space-y-6">
    <UCard>
      <template #header>
        <div class="flex items-center gap-2">
          <UIcon name="i-heroicons-document-text" class="text-green-500" />
          <h2 class="text-xl font-semibold">Document Library</h2>
        </div>
      </template>

      <div class="space-y-4">
        <p class="text-gray-600 dark:text-gray-300">
          This page is accessible to <strong>admin</strong> and <strong>editor</strong> roles.
          Writers can view documents but cannot upload or delete.
        </p>

        <UAlert
          color="green"
          variant="soft"
          icon="i-heroicons-information-circle"
          title="Editor & Admin Access"
          description="This page demonstrates multi-role access control. Both administrators and editors can view this content."
        />

        <div class="mt-4">
          <h3 class="text-lg font-semibold mb-2">Current User Permissions</h3>
          <UCard>
            <dl class="space-y-2">
              <div>
                <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">User</dt>
                <dd class="text-sm text-gray-900 dark:text-white">{{ user?.full_name }} ({{ user?.email }})</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Role</dt>
                <dd>
                  <UBadge :color="getBadgeColor(user?.role)" variant="soft">
                    {{ user?.role }}
                  </UBadge>
                </dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Can Edit</dt>
                <dd>
                  <UBadge :color="canEdit ? 'green' : 'gray'" variant="soft">
                    {{ canEdit ? 'Yes' : 'No' }}
                  </UBadge>
                </dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Is Admin</dt>
                <dd>
                  <UBadge :color="isAdmin ? 'blue' : 'gray'" variant="soft">
                    {{ isAdmin ? 'Yes' : 'No' }}
                  </UBadge>
                </dd>
              </div>
            </dl>
          </UCard>
        </div>

        <div v-if="canEdit" class="mt-4">
          <UAlert
            color="yellow"
            variant="soft"
            icon="i-heroicons-sparkles"
            title="You can manage documents"
            description="As an admin or editor, you have permission to upload and delete documents."
          />
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
 * Document Library Page
 *
 * This page demonstrates multi-role access control.
 * Both admins and editors can access this page.
 *
 * If a writer or unauthenticated user tries to access this page,
 * they will be redirected.
 */

// Protect this route - require admin or editor role
definePageMeta({
  middleware: 'auth',
  auth: {
    roles: ['admin', 'editor']
  }
})

useHead({
  title: 'Document Library - Org Archivist',
  meta: [
    {
      name: 'description',
      content: 'Document library for uploading and managing organizational documents.'
    }
  ]
})

const { user, isAdmin, canEdit } = useAuth()

const getBadgeColor = (role: string | undefined) => {
  switch (role) {
    case 'admin':
      return 'blue'
    case 'editor':
      return 'green'
    case 'writer':
      return 'yellow'
    default:
      return 'gray'
  }
}
</script>
