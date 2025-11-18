# Nuxt UI Component Guide

**Last Updated:** 2025-11-18
**Nuxt UI Version:** v3/v4
**Purpose:** Project-specific guide for type-safe Nuxt UI component usage

This guide documents the specific patterns and best practices for using Nuxt UI components in the Org Archivist frontend. It focuses on type-safe usage and common pitfalls discovered during development.

## Table of Contents

- [Quick Reference](#quick-reference)
- [Type-Safe Prop Values](#type-safe-prop-values)
- [Common Component Patterns](#common-component-patterns)
- [Common Pitfalls & Solutions](#common-pitfalls--solutions)
- [Migration Notes (v2/v3 → v4)](#migration-notes-v2v3--v4)
- [Component-Specific Guides](#component-specific-guides)

---

## Quick Reference

### Valid Prop Values

**Colors** (UButton, UBadge, UAlert, etc.):
```typescript
type Color = 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'error' | 'neutral'
```

**Sizes** (UButton, UBadge, etc.):
```typescript
type Size = 'xs' | 'sm' | 'md' | 'lg' | 'xl'
// Note: '2xs' is NOT valid in Nuxt UI v3/v4
```

**Variants** (UButton, UBadge, UAlert):
```typescript
type Variant = 'solid' | 'outline' | 'soft' | 'ghost' | 'link' | 'subtle'
```

### Color Mapping Guide

Common colors and their Nuxt UI equivalents:

| Common Name | Nuxt UI Color | Use Case |
|-------------|---------------|----------|
| Gray/Grey   | `neutral`     | Subtle/secondary actions |
| Blue        | `info` or `primary` | Information, primary actions |
| Green       | `success`     | Success states, positive actions |
| Red         | `error`       | Errors, destructive actions |
| Yellow/Orange | `warning`   | Warnings, caution |

---

## Type-Safe Prop Values

### UButton

```vue
<template>
  <!-- ✅ Correct -->
  <UButton
    color="primary"
    size="md"
    variant="solid"
    icon="i-heroicons-plus"
    label="Add Item"
  />

  <!-- ❌ Wrong - Invalid color -->
  <UButton color="gray" label="Cancel" />

  <!-- ✅ Correct -->
  <UButton color="neutral" label="Cancel" />

  <!-- ❌ Wrong - Invalid size -->
  <UButton size="2xs" icon="i-heroicons-x-mark" />

  <!-- ✅ Correct -->
  <UButton size="xs" icon="i-heroicons-x-mark" />
</template>
```

### UBadge

```vue
<template>
  <!-- ✅ Correct -->
  <UBadge color="success" variant="subtle" size="sm">
    Active
  </UBadge>

  <!-- ❌ Wrong - Invalid colors -->
  <UBadge color="green">Success</UBadge>
  <UBadge color="gray">Pending</UBadge>

  <!-- ✅ Correct -->
  <UBadge color="success">Success</UBadge>
  <UBadge color="neutral">Pending</UBadge>
</template>
```

### UAlert

```vue
<template>
  <!-- ✅ Correct -->
  <UAlert
    color="warning"
    variant="soft"
    icon="i-heroicons-exclamation-triangle"
    title="Important Notice"
    description="Please review the sensitivity guidelines."
  />

  <!-- ❌ Wrong - Invalid colors -->
  <UAlert color="yellow" title="Warning" />
  <UAlert color="blue" title="Info" />
  <UAlert color="red" title="Error" />

  <!-- ✅ Correct -->
  <UAlert color="warning" title="Warning" />
  <UAlert color="info" title="Info" />
  <UAlert color="error" title="Error" />
</template>
```

---

## Common Component Patterns

### Multi-Select Filters (USelectMenu)

**Pattern:** Document Library Filter Sidebar

```vue
<script setup lang="ts">
const selectedPrograms = ref<string[]>([])

const programOptions = [
  { label: 'Program A', value: 'program-a' },
  { label: 'Program B', value: 'program-b' },
  { label: 'Program C', value: 'program-c' }
]

// Calculate display text for selected items
const selectedProgramsLabel = computed(() => {
  if (selectedPrograms.value.length === 0) return 'Select programs...'
  return `${selectedPrograms.value.length} selected`
})
</script>

<template>
  <UFormField label="Programs" name="programs">
    <USelectMenu
      v-model="selectedPrograms"
      :options="programOptions"
      multiple
      placeholder="Select programs..."
    >
      <!-- Use placeholder or computed label prop for display -->
      <template #default="{ open }">
        <UButton
          :label="selectedProgramsLabel"
          trailing-icon="i-heroicons-chevron-down"
          color="neutral"
          variant="outline"
        />
      </template>
    </USelectMenu>
  </UFormField>
</template>
```

**Key Points:**
- Don't use `#label` slot (doesn't exist in v3/v4)
- Use default slot or computed label for custom display
- Use `multiple` prop for multi-select behavior

### Toast Notifications (useToast)

```vue
<script setup lang="ts">
const toast = useToast()

function showSuccessToast() {
  toast.add({
    title: 'Success!',
    description: 'Document uploaded successfully.',
    color: 'success',  // ✅ Not 'green'
    icon: 'i-heroicons-check-circle'
  })
}

function showErrorToast() {
  toast.add({
    title: 'Error',
    description: 'Failed to upload document.',
    color: 'error',  // ✅ Not 'red'
    icon: 'i-heroicons-exclamation-triangle'
  })
}

function showWarningToast() {
  toast.add({
    title: 'Warning',
    description: 'This action cannot be undone.',
    color: 'warning',  // ✅ Not 'yellow'
    icon: 'i-heroicons-exclamation-triangle'
  })
}
</script>
```

### Form Field Errors (UFormField)

```vue
<script setup lang="ts">
// ❌ Wrong - null is not assignable to string | boolean | undefined
const validationError = ref<string | null>(null)

// ✅ Correct - Use undefined instead of null
const validationError = ref<string | boolean | undefined>(undefined)

// ✅ Alternative - Convert null to undefined
const validationErrorAlt = ref<string | null>(null)
</script>

<template>
  <!-- ❌ Wrong - Type error if validationError is null -->
  <UFormField :error="validationError">
    <UInput />
  </UFormField>

  <!-- ✅ Correct - Convert null to undefined -->
  <UFormField :error="validationError || undefined">
    <UInput />
  </UFormField>

  <!-- ✅ Correct - Convert to boolean -->
  <UFormField :error="!!validationError">
    <UInput />
  </UFormField>
</template>
```

### Dynamic Badge Colors

```vue
<script setup lang="ts">
import type { BadgeColor } from '#ui/types'

// ✅ Correct - Return type-safe colors
function getStatusColor(status: string): BadgeColor {
  const colorMap: Record<string, BadgeColor> = {
    'completed': 'success',
    'processing': 'info',
    'pending': 'warning',
    'failed': 'error',
    'draft': 'neutral'
  }
  return colorMap[status] || 'neutral'
}

// ❌ Wrong - Might return invalid colors like 'green', 'blue'
function getStatusColorWrong(status: string): string {
  const colorMap: Record<string, string> = {
    'completed': 'green',
    'processing': 'blue',
    'pending': 'yellow',
    'failed': 'red'
  }
  return colorMap[status] || 'gray'
}
</script>

<template>
  <!-- ✅ Correct -->
  <UBadge :color="getStatusColor(document.status)">
    {{ document.status }}
  </UBadge>
</template>
```

### Card Styling with :ui Prop

```vue
<script setup lang="ts">
const hasError = ref(false)
</script>

<template>
  <!-- ❌ Wrong - 'ring' doesn't exist in ui prop type -->
  <UCard :ui="{ ring: hasError ? 'ring-2 ring-red-500' : '' }">
    <p>Card content</p>
  </UCard>

  <!-- ✅ Correct - Use 'root' for wrapper classes -->
  <UCard :ui="{ root: hasError ? 'ring-2 ring-red-500' : '' }">
    <p>Card content</p>
  </UCard>

  <!-- ✅ Alternative - Use class binding -->
  <UCard :class="{ 'ring-2 ring-red-500': hasError }">
    <p>Card content</p>
  </UCard>
</template>
```

---

## Common Pitfalls & Solutions

### 1. Invalid Slot Names

**Problem:** Using slots that don't exist in Nuxt UI v3/v4

```vue
<!-- ❌ Wrong - #label slot doesn't exist on USelectMenu -->
<USelectMenu v-model="selected" :options="options">
  <template #label>
    <span>{{ selectedLabel }}</span>
  </template>
</USelectMenu>

<!-- ✅ Correct - Use default slot or label prop -->
<USelectMenu v-model="selected" :options="options">
  <template #default="{ open }">
    <UButton :label="selectedLabel" />
  </template>
</USelectMenu>

<!-- ✅ Or use label prop directly -->
<USelectMenu
  v-model="selected"
  :options="options"
  :label="selectedLabel"
/>
```

**Solution:** Check Nuxt UI v4 documentation for correct slot names. Common changes:
- `#label` → Use default slot or label prop
- Component API has changed between versions

### 2. Invalid Color Values

**Problem:** Using CSS color names instead of Nuxt UI color tokens

```vue
<!-- ❌ Wrong -->
<UButton color="gray">Cancel</UButton>
<UBadge color="blue">Info</UBadge>
<UAlert color="red">Error</UAlert>
<UAlert color="yellow">Warning</UAlert>

<!-- ✅ Correct -->
<UButton color="neutral">Cancel</UButton>
<UBadge color="info">Info</UBadge>
<UAlert color="error">Error</UAlert>
<UAlert color="warning">Warning</UAlert>
```

**Solution:** Use the [color mapping guide](#color-mapping-guide) above.

### 3. Invalid Size Values

**Problem:** Using sizes that don't exist

```vue
<!-- ❌ Wrong - '2xs' doesn't exist -->
<UButton size="2xs" icon="i-heroicons-x-mark" />

<!-- ✅ Correct - Use 'xs' -->
<UButton size="xs" icon="i-heroicons-x-mark" />
```

**Valid sizes:** `xs`, `sm`, `md`, `lg`, `xl`

### 4. Event Handler Type Mismatches

**Problem:** Event handler receives wrong type

```vue
<script setup lang="ts">
// ❌ Wrong - Expects string but receives SelectMenuItem
function resumeChat(conversationId: string) {
  navigateTo(`/chat/${conversationId}`)
}
</script>

<template>
  <USelectMenu
    v-model="selectedConversation"
    :options="conversations"
    @update:model-value="resumeChat"
  />
</template>
```

**Solution:** Update handler to accept correct type

```vue
<script setup lang="ts">
import type { SelectMenuItem } from '#ui/types'

// ✅ Correct - Handle SelectMenuItem
function resumeChat(item: SelectMenuItem) {
  if (typeof item === 'string') {
    navigateTo(`/chat/${item}`)
  } else if (item?.value) {
    navigateTo(`/chat/${item.value}`)
  }
}

// ✅ Or use separate ref and watch
const selectedConversation = ref<string>()
watch(selectedConversation, (newValue) => {
  if (newValue) {
    navigateTo(`/chat/${newValue}`)
  }
})
</script>
```

### 5. Null vs Undefined for Optional Props

**Problem:** Using `null` for props that expect `undefined`

```vue
<script setup lang="ts">
// ❌ Wrong - UFormField error prop expects string | boolean | undefined
const errorMessage = ref<string | null>(null)
</script>

<template>
  <UFormField :error="errorMessage">
    <UInput />
  </UFormField>
</template>
```

**Solutions:**

```vue
<script setup lang="ts">
// Solution 1: Type as undefined instead of null
const errorMessage = ref<string | undefined>(undefined)

// Solution 2: Convert null to undefined
const errorMessage = ref<string | null>(null)
</script>

<template>
  <!-- Solution 2 template fix -->
  <UFormField :error="errorMessage || undefined">
    <UInput />
  </UFormField>
</template>
```

---

## Migration Notes (v2/v3 → v4)

### API Changes

1. **Slot Names Changed**
   - Many named slots have been removed or renamed
   - Check v4 docs for current slot API
   - Use default slot with custom content when needed

2. **Color System Standardized**
   - All components now use the same color tokens
   - CSS color names (gray, blue, red, etc.) no longer valid
   - Use semantic colors: primary, secondary, success, info, warning, error, neutral

3. **UI Prop Structure**
   - Some properties in `:ui` object have changed
   - Use `root` for wrapper classes instead of component-specific keys
   - Check TypeScript types for valid keys

### Breaking Changes to Watch For

```vue
<!-- v2/v3 Patterns (may not work) -->
<USelectMenu>
  <template #label>Custom Label</template>
</USelectMenu>

<UCard :ui="{ ring: 'ring-2' }" />

<UButton color="gray" size="2xs" />

<!-- v4 Patterns (current) -->
<USelectMenu>
  <template #default>
    <UButton label="Custom Label" />
  </template>
</USelectMenu>

<UCard :ui="{ root: 'ring-2' }" />

<UButton color="neutral" size="xs" />
```

---

## Component-Specific Guides

### USelectMenu (Multi-Select)

```vue
<script setup lang="ts">
interface Option {
  label: string
  value: string
}

const selected = ref<string[]>([])
const options: Option[] = [
  { label: 'Option 1', value: 'opt1' },
  { label: 'Option 2', value: 'opt2' }
]

const displayLabel = computed(() => {
  if (selected.value.length === 0) return 'Select options...'
  if (selected.value.length === 1) {
    return options.find(o => o.value === selected.value[0])?.label
  }
  return `${selected.value.length} selected`
})
</script>

<template>
  <UFormField label="Options" name="options">
    <USelectMenu
      v-model="selected"
      :options="options"
      multiple
      searchable
      placeholder="Select options..."
    >
      <template #default="{ open }">
        <UButton
          :label="displayLabel"
          trailing-icon="i-heroicons-chevron-down"
          color="neutral"
          variant="outline"
          class="w-full"
        />
      </template>
    </USelectMenu>
  </UFormField>
</template>
```

### UFileUpload

```vue
<script setup lang="ts">
const selectedFiles = ref<File[]>([])

const accept = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain'
]

function handleFileChange(files: File[]) {
  selectedFiles.value = files
}
</script>

<template>
  <UFormField
    label="Documents"
    name="files"
    help="PDF, DOCX, or TXT files. Max 50MB per file."
  >
    <UFileUpload
      v-model="selectedFiles"
      :accept="accept"
      :max-size="50 * 1024 * 1024"
      multiple
      @update:model-value="handleFileChange"
    >
      <template #default>
        <div class="flex flex-col items-center gap-2 p-6">
          <UIcon name="i-heroicons-cloud-arrow-up" class="w-12 h-12 text-gray-400" />
          <p class="text-sm text-gray-600">
            Drop files here or click to browse
          </p>
        </div>
      </template>
    </UFileUpload>
  </UFormField>
</template>
```

### UProgress

```vue
<script setup lang="ts">
const uploadProgress = ref(0)
const isComplete = computed(() => uploadProgress.value === 100)
</script>

<template>
  <UProgress
    :value="uploadProgress"
    :color="isComplete ? 'success' : 'primary'"
    size="md"
  />
</template>
```

---

## TypeScript Integration

### Import Types

```typescript
// Import Nuxt UI types for better type safety
import type { BadgeColor, ButtonSize, AlertVariant } from '#ui/types'
import type { SelectMenuItem } from '#ui/types'

// Use in component
const color: BadgeColor = 'success'
const size: ButtonSize = 'md'
```

### Type-Safe Helper Functions

```typescript
import type { BadgeColor } from '#ui/types'

export function getStatusBadgeColor(status: string): BadgeColor {
  const statusMap: Record<string, BadgeColor> = {
    active: 'success',
    pending: 'warning',
    inactive: 'neutral',
    error: 'error',
    processing: 'info'
  }
  return statusMap[status.toLowerCase()] ?? 'neutral'
}

export function getOutcomeBadgeColor(outcome: string): BadgeColor {
  const outcomeMap: Record<string, BadgeColor> = {
    awarded: 'success',
    rejected: 'error',
    pending: 'warning',
    withdrawn: 'neutral'
  }
  return outcomeMap[outcome.toLowerCase()] ?? 'neutral'
}
```

---

## Resources

- **Official Nuxt UI Documentation:** https://ui.nuxt.com/docs
- **Nuxt UI v4 Release Notes:** https://nuxt.com/blog/nuxt-ui-v4
- **Project Frontend Requirements:** `/context/frontend-requirements.md`
- **Component Type Definitions:** `node_modules/@nuxt/ui/dist/runtime/types/`

---

## Contributing to This Guide

When you discover new patterns or pitfalls:

1. Document the problem and solution
2. Add code examples
3. Update relevant sections
4. Keep examples practical and project-specific
5. Include TypeScript types when helpful

**Last Updated:** 2025-11-18
**Maintained by:** Org Archivist Development Team
