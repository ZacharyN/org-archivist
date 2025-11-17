# Org Archivist Frontend UI Implementation Plan

**Version:** 1.0
**Date:** November 16, 2025
**Status:** In Progress - Phase 1 (MVP Foundation)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Page Structure & Routing](#page-structure--routing)
- [Core Components by Feature](#core-components-by-feature)
- [Composables & Utilities](#composables--utilities)
- [Implementation Phases](#implementation-phases)
- [Key UX Principles](#key-ux-principles)
- [Technical Considerations](#technical-considerations)

---

## Overview

This document outlines the complete UI implementation plan for Org Archivist, a Nuxt 4-based frontend for nonprofit organizations to upload documents, create writing styles, manage programs, and use an AI chat assistant for grant writing.

### Design Goals

1. **User-friendly for non-technical users** - Clear navigation, familiar patterns, minimal complexity
2. **Chat-first experience** - Quick access to AI assistant from anywhere
3. **Progressive disclosure** - Advanced features hidden until needed
4. **Responsive design** - Works on desktop, tablet, and mobile

### Tech Stack

- **Framework:** Nuxt 4 (Vue 3 Composition API)
- **Language:** TypeScript (strict mode)
- **UI Library:** Nuxt UI (Tailwind CSS + Radix UI components)
- **Icons:** Nuxt Icon
- **State:** Composables with reactive refs
- **API Client:** Custom `$fetch` wrapper with auth injection
- **Forms:** Nuxt UI Form with Zod validation

---

## Architecture

### Layout Structure

**Combined Navigation Pattern** (Top bar + Left sidebar)

```
┌─────────────────────────────────────────────────────────┐
│  Logo    Breadcrumbs              [User] [Settings] [▼] │  ← Top Bar
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│  [Home]  │                                              │
│  [Chat]  │                                              │
│  [Docs]  │         Main Content Area                    │
│  [Prog]  │                                              │
│  [Style] │                                              │
│  [Out]   │                                              │
│          │                                              │
│  Sidebar │                                              │
└──────────┴──────────────────────────────────────────────┘
```

**Components:**
- `TopBar.vue` - User profile menu, notifications, logout, organization branding
- `Sidebar.vue` - Main navigation menu with role-based visibility
- `DefaultLayout.vue` - Container with top bar + sidebar + main content area

### Directory Structure

```
frontend/
├── app.vue                 # Root component
├── nuxt.config.ts          # Nuxt configuration
├── pages/                  # File-based routing
│   ├── index.vue          # Dashboard (landing page)
│   ├── login.vue          # Login page
│   ├── documents/
│   │   ├── index.vue      # Document library
│   │   └── upload.vue     # Upload documents
│   ├── programs/
│   │   └── index.vue      # Programs management
│   ├── writing-styles/
│   │   ├── index.vue      # Writing styles list
│   │   └── create.vue     # Create writing style wizard
│   ├── chat/
│   │   ├── index.vue      # Chat interface
│   │   └── [id].vue       # Specific conversation
│   ├── outputs/
│   │   ├── index.vue      # Past outputs dashboard
│   │   └── [id].vue       # Output detail + success tracking
│   ├── settings/
│   │   └── index.vue      # User settings
│   └── admin/
│       └── users.vue      # User management (Admin only)
├── layouts/
│   └── default.vue        # Default layout
├── components/
│   ├── layout/
│   │   ├── TopBar.vue
│   │   └── Sidebar.vue
│   ├── dashboard/
│   │   ├── ChatQuickStart.vue
│   │   ├── RecentActivity.vue
│   │   ├── SetupChecklist.vue
│   │   └── QuickStats.vue
│   ├── documents/
│   │   ├── DocumentUpload.vue
│   │   ├── DocumentLibrary.vue
│   │   └── DocumentCard.vue
│   ├── chat/
│   │   ├── ChatMessage.vue
│   │   ├── ChatInput.vue
│   │   └── ConversationList.vue
│   ├── outputs/
│   │   ├── OutputCard.vue
│   │   └── SuccessTrackingForm.vue
│   └── shared/
│       ├── LoadingSkeleton.vue
│       └── EmptyState.vue
├── composables/
│   ├── useApi.ts          # API client (COMPLETED ✓)
│   ├── useAuth.ts         # Authentication state
│   ├── useDocuments.ts    # Document operations
│   ├── usePrograms.ts     # Programs CRUD
│   ├── useWritingStyles.ts # Writing styles management
│   ├── useChat.ts         # Conversation management
│   ├── useStreaming.ts    # SSE streaming for AI responses
│   └── useOutputs.ts      # Outputs management
├── types/
│   └── api.ts             # TypeScript type definitions (COMPLETED ✓)
├── middleware/
│   └── auth.ts            # Route protection
└── utils/
    └── format.ts          # Formatting utilities
```

---

## Page Structure & Routing

### Route Map

| Route | Page | Auth Required | Roles |
|-------|------|---------------|-------|
| `/` | Dashboard | Yes | All |
| `/login` | Login | No | - |
| `/documents` | Document Library | Yes | All |
| `/documents/upload` | Upload Documents | Yes | Admin, Editor |
| `/programs` | Programs Management | Yes | Admin, Editor |
| `/writing-styles` | Writing Styles List | Yes | All |
| `/writing-styles/create` | Create Writing Style Wizard | Yes | Admin, Editor |
| `/chat` | Chat Interface | Yes | All |
| `/chat/:id` | Specific Conversation | Yes | All |
| `/outputs` | Past Outputs Dashboard | Yes | All |
| `/outputs/:id` | Output Detail + Success Tracking | Yes | All |
| `/settings` | User Settings | Yes | All |
| `/admin/users` | User Management | Yes | Admin |

---

## Core Components by Feature

### 1. Authentication & Layout

#### `LoginPage.vue` (`/pages/login.vue`)

**Purpose:** User login with JWT authentication

**Components Used:**
- `UForm` - Form wrapper with validation
- `UInput` - Email and password fields
- `UButton` - Submit button
- `UAlert` - Error messages
- `UCheckbox` - "Remember me" option

**State:**
```typescript
const form = ref({
  email: '',
  password: ''
})
const error = ref<string | null>(null)
const loading = ref(false)
```

**Flow:**
1. User enters credentials
2. Submit via `useAuth().login()`
3. On success: Redirect to dashboard
4. On failure: Show error message

---

#### `DefaultLayout.vue` (`/layouts/default.vue`)

**Purpose:** Main application layout with navigation

**Structure:**
```vue
<template>
  <div class="min-h-screen flex flex-col">
    <TopBar />
    <div class="flex flex-1 overflow-hidden">
      <Sidebar />
      <main class="flex-1 overflow-y-auto bg-gray-50 dark:bg-gray-900">
        <slot />
      </main>
    </div>
  </div>
</template>
```

**Responsive Behavior:**
- Desktop: Full sidebar visible
- Tablet: Collapsible sidebar
- Mobile: Drawer-style sidebar (overlay)

---

#### `TopBar.vue` (`/components/layout/TopBar.vue`)

**Features:**
- Organization logo/name
- Breadcrumb navigation (dynamic based on route)
- User avatar + name
- Dropdown menu: Profile, Settings, Logout
- Optional notification bell

**Navigation Items:**
```typescript
const userMenuItems = computed(() => [
  { label: 'Profile', icon: 'i-heroicons-user', to: '/settings' },
  { label: 'Settings', icon: 'i-heroicons-cog', to: '/settings' },
  { label: 'Logout', icon: 'i-heroicons-arrow-right-on-rectangle', click: handleLogout }
])
```

---

#### `Sidebar.vue` (`/components/layout/Sidebar.vue`)

**Navigation Items:**

```typescript
const navigationItems = computed(() => {
  const { user } = useAuth()

  const items = [
    {
      label: 'Dashboard',
      icon: 'i-heroicons-home',
      to: '/',
      badge: null
    },
    {
      label: 'Chat',
      icon: 'i-heroicons-chat-bubble-left-right',
      to: '/chat',
      badge: 'New' // Highlight important feature
    },
    {
      label: 'Documents',
      icon: 'i-heroicons-document-text',
      to: '/documents'
    },
    {
      label: 'Writing Styles',
      icon: 'i-heroicons-pencil-square',
      to: '/writing-styles'
    },
    {
      label: 'Past Outputs',
      icon: 'i-heroicons-archive-box',
      to: '/outputs'
    }
  ]

  // Admin/Editor only items
  if (user.value?.role === 'admin' || user.value?.role === 'editor') {
    items.splice(3, 0, {
      label: 'Programs',
      icon: 'i-heroicons-rectangle-stack',
      to: '/programs'
    })
  }

  // Admin only items
  if (user.value?.role === 'admin') {
    items.push({
      label: 'Manage Users',
      icon: 'i-heroicons-users',
      to: '/admin/users'
    })
  }

  return items
})
```

---

### 2. Dashboard (Landing Page)

#### `DashboardPage.vue` (`/pages/index.vue`)

**Layout:** 2-column grid (8-4 split on desktop, stacked on mobile)

**Left Column (Main):**

1. **ChatQuickStart.vue** - Prominent chat widget
   - Large "Start New Conversation" button
   - Resume recent conversation dropdown
   - Quick context selectors (writing style, audience)
   - "Open full chat" link → `/chat`

2. **RecentActivity.vue** - Tabbed card
   - Tab 1: Recent Chats (last 5 conversations)
   - Tab 2: Recent Uploads (last 5 documents)
   - Tab 3: Recent Outputs (last 5 generated content)

**Right Column (Sidebar):**

1. **SetupChecklist.vue** - Progress tracker
   ```typescript
   const checklistItems = [
     {
       label: 'Documents uploaded',
       completed: documentCount.value > 0,
       count: documentCount.value,
       to: '/documents/upload'
     },
     {
       label: 'Writing styles created',
       completed: styleCount.value > 0,
       count: styleCount.value,
       to: '/writing-styles/create'
     },
     {
       label: 'Programs configured',
       completed: programCount.value > 0,
       count: programCount.value,
       to: '/programs'
     }
   ]
   ```

2. **QuickStats.vue** - Stat cards
   - Total documents
   - Grant success rate (if outputs exist)
   - Active conversations

**Optional Onboarding Tour:**
- Triggered on first login only
- Skippable tooltips/popovers
- Highlights: Upload docs → Create style → Start chat
- "Don't show again" checkbox

---

### 3. Document Management

#### `DocumentLibraryPage.vue` (`/pages/documents/index.vue`)

**Header:**
- Page title: "Document Library"
- Primary action: `UButton` "Upload Documents" → `/documents/upload`
- Search bar: `UInput` with icon (full-text search)

**Filter Sidebar** (Collapsible on mobile):
```typescript
const filters = ref({
  docTypes: [] as DocumentType[],
  programs: [] as string[],
  years: [] as number[],
  outcomes: [] as DocumentOutcome[]
})
```

**Filter Components:**
- `USelectMenu` - Document type filter (multi-select)
- `USelectMenu` - Program filter (multi-select, loaded from API)
- `USelectMenu` - Year filter (range or multi-select)
- `USelectMenu` - Outcome filter
- `UButton` - "Clear all filters"

**Main Content:**

`UTable` configuration:
```typescript
const columns = [
  { key: 'filename', label: 'Filename', sortable: true },
  { key: 'doc_type', label: 'Type' },
  { key: 'programs', label: 'Programs' },
  { key: 'year', label: 'Year', sortable: true },
  { key: 'outcome', label: 'Outcome' },
  { key: 'upload_date', label: 'Uploaded', sortable: true },
  { key: 'actions', label: '' }
]

const rows = computed(() => {
  return documents.value.map(doc => ({
    filename: doc.filename,
    doc_type: doc.metadata.doc_type,
    programs: doc.metadata.programs, // Rendered as badges
    year: doc.metadata.year,
    outcome: doc.metadata.outcome, // Rendered as colored badge
    upload_date: formatDate(doc.upload_date),
    actions: doc.doc_id
  }))
})
```

**Cell Rendering:**
- **Programs:** Max 3 `UBadge` visible, "+2 more" if > 3
- **Outcome:** Colored `UBadge` (green=Funded, red=Not Funded, yellow=Pending)
- **Actions:** `UDropdown` with "View Details", "Delete" options

**Pagination:**
- `UPagination` component at bottom
- Page size selector (10, 25, 50, 100)

**Empty State:**
```vue
<UCard v-if="documents.length === 0">
  <template #header>
    <div class="text-center">
      <UIcon name="i-heroicons-document-text" class="w-12 h-12 mx-auto text-gray-400" />
      <h3>No documents yet</h3>
    </div>
  </template>
  <div class="text-center">
    <p class="text-gray-600 mb-4">
      Upload your grant proposals, reports, and other documents to get started.
    </p>
    <UButton to="/documents/upload" color="primary">
      Upload Your First Document
    </UButton>
  </div>
</UCard>
```

---

#### `DocumentUploadPage.vue` (`/pages/documents/upload.vue`)

**Multi-step Wizard** (Using `USteps` for progress indicator)

```typescript
const currentStep = ref(1)
const steps = [
  { id: 1, label: 'Upload Files' },
  { id: 2, label: 'Add Metadata' },
  { id: 3, label: 'Sensitivity Check' },
  { id: 4, label: 'Upload' }
]
```

**Step 1: File Upload**
- `UFileUpload` with drag-and-drop zone
- Accepted formats: PDF, DOCX, TXT
- Max file size: 50MB per file
- Multiple file upload support
- File preview list with remove option

```vue
<UFileUpload
  v-model="files"
  multiple
  accept=".pdf,.docx,.txt"
  :max-size="50 * 1024 * 1024"
  @change="handleFileChange"
>
  <template #default="{ isDragging }">
    <div :class="{ 'bg-primary-50': isDragging }">
      <UIcon name="i-heroicons-cloud-arrow-up" />
      <p>Drag files here or click to browse</p>
      <p class="text-sm text-gray-500">PDF, DOCX, TXT up to 50MB</p>
    </div>
  </template>
</UFileUpload>
```

**Step 2: Metadata** (For each file)
```typescript
const metadata = ref<Record<string, DocumentMetadata>>({})

// Form for each file
{
  doc_type: 'Grant Proposal', // USelect
  year: 2024, // UInput (number) with validation
  programs: [], // USelectMenu (multi-select)
  tags: [], // Chip input (comma-separated)
  outcome: 'N/A', // USelect
  notes: '' // UTextarea
}
```

**Step 3: Sensitivity Confirmation**
```vue
<UAlert color="warning" icon="i-heroicons-exclamation-triangle">
  <template #title>Important: Public Documents Only</template>
  <template #description>
    In this MVP version, only non-sensitive documents should be uploaded.
    Please confirm that these documents contain no confidential information.
  </template>
</UAlert>

<UCheckbox
  v-model="sensitivityConfirmed"
  label="I confirm these documents contain no sensitive information"
  required
/>
```

**Step 4: Upload**
- Progress bars for each file (`UProgress`)
- Success/error indicators
- Real-time upload status
- Summary of uploaded documents
- Actions: "Upload More" or "Go to Library"

---

### 4. Programs Management

#### `ProgramsPage.vue` (`/pages/programs/index.vue`)

**Permissions:** Editor and Admin only

**Header:**
- Page title: "Programs"
- Description: "Organize your documents by program areas"
- Primary action: `UButton` "Add Program" (opens modal)

**Main Content:**

`UTable` with drag-and-drop reordering:
```typescript
const columns = [
  { key: 'drag', label: '' }, // Drag handle
  { key: 'name', label: 'Name' },
  { key: 'description', label: 'Description' },
  { key: 'active', label: 'Active' },
  { key: 'actions', label: '' }
]
```

**Features:**
- Drag handles for reordering (updates `display_order`)
- `UToggle` for active/inactive status
- `UDropdown` actions: Edit, Delete
- Inline editing for quick name changes

**Modals:**

`CreateProgramModal.vue` / `EditProgramModal.vue`:
```vue
<UModal v-model="isOpen">
  <UCard>
    <template #header>
      <h3>{{ mode === 'create' ? 'Add Program' : 'Edit Program' }}</h3>
    </template>

    <UForm :state="form" @submit="handleSubmit">
      <UFormField label="Program Name" required>
        <UInput v-model="form.name" />
      </UFormField>

      <UFormField label="Description">
        <UTextarea v-model="form.description" />
      </UFormField>

      <UFormField label="Active">
        <UToggle v-model="form.active" />
      </UFormField>
    </UForm>

    <template #footer>
      <UButton color="gray" @click="isOpen = false">Cancel</UButton>
      <UButton color="primary" @click="handleSubmit">
        {{ mode === 'create' ? 'Create' : 'Save' }}
      </UButton>
    </template>
  </UCard>
</UModal>
```

---

### 5. Writing Styles

#### `WritingStylesPage.vue` (`/pages/writing-styles/index.vue`)

**Header:**
- Page title: "Writing Styles"
- Description: "Train the AI to write in your organization's voice"
- Primary action: `UButton` "Create Writing Style" → `/writing-styles/create`

**Main Content:**

Grid of `UCard` components (2-3 columns responsive):
```vue
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <UCard v-for="style in writingStyles" :key="style.style_id">
    <template #header>
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-semibold">{{ style.name }}</h3>
        <UBadge :color="getTypeColor(style.type)">
          {{ style.type }}
        </UBadge>
      </div>
    </template>

    <div class="space-y-3">
      <p class="text-sm text-gray-600">{{ style.description }}</p>

      <div class="flex items-center gap-2 text-sm">
        <UIcon name="i-heroicons-document-text" class="w-4 h-4" />
        <span>{{ style.sample_count }} samples</span>
      </div>

      <div class="text-sm text-gray-700 line-clamp-2">
        {{ style.prompt_content.slice(0, 100) }}...
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between">
        <UToggle v-model="style.active" @change="updateStyle(style)" />

        <UDropdown :items="styleActions(style)">
          <UButton icon="i-heroicons-ellipsis-vertical" variant="ghost" />
        </UDropdown>
      </div>
    </template>
  </UCard>
</div>
```

---

#### `CreateWritingStylePage.vue` (`/pages/writing-styles/create.vue`)

**4-Step Wizard** (Using `USteps`)

**Step 1: Basic Info**
```typescript
const form = ref({
  name: '',
  type: 'grant' as WritingStyleType,
  description: ''
})
```

- `UInput` - Style name (required, unique)
- `USelect` - Type (grant, proposal, report, general)
- `UTextarea` - Description

**Step 2: Upload Samples**
```typescript
const samples = ref<string[]>([])
const uploadMethod = ref<'file' | 'paste'>('file')
```

Two input methods:
1. **File Upload:** `UFileUpload` for TXT/DOCX files
2. **Paste Text:** `UTextarea` for direct input

Requirements:
- 3-7 samples needed
- Minimum 200 words per sample
- Real-time word count display

```vue
<div v-for="(sample, index) in samples" :key="index" class="border rounded p-4">
  <div class="flex items-center justify-between mb-2">
    <span class="text-sm font-medium">Sample {{ index + 1 }}</span>
    <div class="flex items-center gap-2">
      <span class="text-sm" :class="{ 'text-red-500': wordCount(sample) < 200 }">
        {{ wordCount(sample) }} words
      </span>
      <UButton
        icon="i-heroicons-trash"
        size="sm"
        color="red"
        variant="ghost"
        @click="removeSample(index)"
      />
    </div>
  </div>
  <p class="text-sm text-gray-600 line-clamp-3">{{ sample.slice(0, 150) }}...</p>
</div>
```

**Step 3: AI Analysis** (Automatic)

Loading state while AI processes samples:
```vue
<div class="text-center py-12">
  <UProgress animation="carousel" />
  <h3 class="mt-4 text-lg font-semibold">Analyzing writing samples...</h3>
  <p class="text-sm text-gray-600">
    This may take 30-60 seconds. We're identifying patterns in vocabulary,
    sentence structure, tone, and style.
  </p>
</div>
```

Results display:
```vue
<div class="space-y-6">
  <UAlert color="success">
    Analysis complete! We've generated a writing style prompt based on your samples.
  </UAlert>

  <div class="grid grid-cols-2 gap-4">
    <UCard>
      <template #header>Vocabulary Characteristics</template>
      {{ analysis.vocabulary }}
    </UCard>

    <UCard>
      <template #header>Sentence Structure</template>
      {{ analysis.sentence_structure }}
    </UCard>

    <UCard>
      <template #header>Tone & Voice</template>
      {{ analysis.tone }}
    </UCard>

    <UCard>
      <template #header>Transition Patterns</template>
      {{ analysis.transitions }}
    </UCard>
  </div>

  <UFormField label="Generated Style Prompt (Editable)">
    <UTextarea
      v-model="generatedPrompt"
      rows="10"
      placeholder="AI-generated style prompt..."
    />
  </UFormField>
</div>
```

**Step 4: Review & Save**
- Display final prompt (read-only view with syntax highlighting)
- `UToggle` - "Make active immediately"
- `UButton` - "Save Writing Style"

---

### 6. Chat Interface

#### `ChatQuickStart.vue` (`/components/dashboard/ChatQuickStart.vue`)

Used on Dashboard for quick access:

```vue
<UCard class="bg-gradient-to-br from-primary-50 to-primary-100 dark:from-primary-900 dark:to-primary-800">
  <template #header>
    <div class="flex items-center gap-2">
      <UIcon name="i-heroicons-chat-bubble-left-right" class="w-6 h-6" />
      <h2 class="text-xl font-semibold">Start a Conversation</h2>
    </div>
  </template>

  <div class="space-y-4">
    <UButton
      block
      size="lg"
      color="primary"
      @click="startNewChat"
    >
      New Conversation
    </UButton>

    <USelectMenu
      v-model="selectedConversation"
      :options="recentConversations"
      placeholder="Or resume a recent conversation..."
      @change="resumeChat"
    />

    <div class="grid grid-cols-2 gap-2">
      <USelectMenu
        v-model="quickContext.writingStyle"
        :options="writingStyles"
        placeholder="Writing Style"
        size="sm"
      />

      <UInput
        v-model="quickContext.audience"
        placeholder="Audience"
        size="sm"
      />
    </div>
  </div>

  <template #footer>
    <NuxtLink to="/chat" class="text-sm text-primary-600 hover:underline">
      Open full chat interface →
    </NuxtLink>
  </template>
</UCard>
```

---

#### `ChatPage.vue` (`/pages/chat/index.vue` or `/pages/chat/[id].vue`)

**3-Column Layout:**

```vue
<div class="flex h-[calc(100vh-4rem)]">
  <!-- Left Sidebar: Conversations List -->
  <aside class="w-64 border-r overflow-y-auto">
    <ConversationList />
  </aside>

  <!-- Center: Chat Messages -->
  <main class="flex-1 flex flex-col">
    <ChatHeader />
    <ChatMessages />
    <ChatInput />
  </main>

  <!-- Right Sidebar: Context Panel -->
  <aside class="w-80 border-l overflow-y-auto">
    <ContextPanel />
  </aside>
</div>
```

**ConversationList Component:**
```vue
<div class="p-4 space-y-4">
  <UButton block color="primary" @click="createConversation">
    <UIcon name="i-heroicons-plus" />
    New Chat
  </UButton>

  <UInput
    v-model="searchQuery"
    icon="i-heroicons-magnifying-glass"
    placeholder="Search conversations..."
  />

  <!-- Grouped by date -->
  <div v-for="group in groupedConversations" :key="group.label">
    <h3 class="text-xs font-semibold text-gray-500 uppercase mb-2">
      {{ group.label }}
    </h3>

    <div class="space-y-1">
      <button
        v-for="conv in group.items"
        :key="conv.conversation_id"
        :class="[
          'w-full text-left p-3 rounded-lg hover:bg-gray-100',
          { 'bg-primary-100': conv.conversation_id === activeConversationId }
        ]"
        @click="selectConversation(conv)"
      >
        <p class="font-medium truncate">{{ conv.name }}</p>
        <p class="text-sm text-gray-600 truncate">
          {{ conv.lastMessage?.content.slice(0, 50) }}...
        </p>
        <p class="text-xs text-gray-400">
          {{ formatTimestamp(conv.updated_at) }}
        </p>
      </button>
    </div>
  </div>
</div>
```

**ChatMessages Component:**
```vue
<div ref="messagesContainer" class="flex-1 overflow-y-auto p-6 space-y-4">
  <ChatMessage
    v-for="message in messages"
    :key="message.message_id"
    :message="message"
  />

  <!-- Streaming indicator -->
  <div v-if="isStreaming" class="flex items-start gap-3">
    <UAvatar src="/ai-avatar.png" />
    <div class="flex-1">
      <div class="bg-gray-100 rounded-lg p-4">
        <p class="animate-pulse">{{ streamingContent }}</p>
      </div>
    </div>
  </div>

  <!-- Empty state -->
  <div v-if="messages.length === 0" class="text-center py-12">
    <UIcon name="i-heroicons-chat-bubble-left-right" class="w-16 h-16 mx-auto text-gray-300" />
    <h3 class="mt-4 text-lg font-semibold">Start a conversation</h3>
    <p class="text-gray-600">Ask me anything about your documents and grant writing.</p>
  </div>
</div>
```

**ChatMessage Component:**
```vue
<div :class="['flex gap-3', message.role === 'user' ? 'justify-end' : '']">
  <UAvatar
    v-if="message.role === 'assistant'"
    src="/ai-avatar.png"
  />

  <div :class="[
    'max-w-3xl rounded-lg p-4',
    message.role === 'user'
      ? 'bg-primary-600 text-white'
      : 'bg-gray-100'
  ]">
    <!-- Message content with markdown rendering -->
    <div class="prose prose-sm" v-html="renderMarkdown(message.content)" />

    <!-- Sources (for assistant messages) -->
    <div v-if="message.sources && message.sources.length > 0" class="mt-4">
      <UAccordion :items="sourceAccordionItems(message.sources)">
        <template #default="{ item, open }">
          <div class="flex items-center gap-2">
            <UIcon :name="open ? 'i-heroicons-chevron-down' : 'i-heroicons-chevron-right'" />
            <span class="text-sm font-medium">
              {{ item.sources.length }} sources
            </span>
          </div>
        </template>

        <template #content="{ item }">
          <div class="space-y-2">
            <div
              v-for="source in item.sources"
              :key="source.chunk_id"
              class="p-2 bg-white rounded border"
            >
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium">{{ source.filename }}</span>
                <UBadge>{{ Math.round(source.relevance_score * 100) }}%</UBadge>
              </div>
              <p class="text-xs text-gray-600">{{ source.text.slice(0, 150) }}...</p>
            </div>
          </div>
        </template>
      </UAccordion>
    </div>

    <!-- Timestamp and actions -->
    <div class="flex items-center gap-2 mt-2 text-xs opacity-70">
      <span>{{ formatTimestamp(message.created_at) }}</span>
      <UButton
        icon="i-heroicons-clipboard-document"
        size="xs"
        variant="ghost"
        @click="copyMessage(message)"
      />
    </div>
  </div>

  <UAvatar
    v-if="message.role === 'user'"
    :src="user.avatar"
  />
</div>
```

**ChatInput Component:**
```vue
<div class="border-t p-4">
  <div class="flex items-end gap-2">
    <UTextarea
      v-model="messageInput"
      :rows="rows"
      :max-rows="4"
      placeholder="Ask about your documents, request grant content, or refine your writing..."
      @keydown.enter.exact.prevent="sendMessage"
      @keydown.shift.enter="handleNewLine"
    />

    <UButton
      icon="i-heroicons-paper-airplane"
      color="primary"
      :disabled="!messageInput.trim() || isStreaming"
      @click="sendMessage"
    />
  </div>

  <div class="flex items-center justify-between mt-2 text-xs text-gray-500">
    <span>{{ wordCount(messageInput) }} words</span>
    <span>Press Enter to send, Shift+Enter for new line</span>
  </div>
</div>
```

**ContextPanel Component:**
```vue
<div class="p-4 space-y-6">
  <UCard>
    <template #header>
      <h3 class="font-semibold">Context Settings</h3>
    </template>

    <div class="space-y-4">
      <UFormField label="Writing Style">
        <USelectMenu
          v-model="context.writingStyleId"
          :options="writingStyles"
          placeholder="Select a style..."
        />
      </UFormField>

      <UFormField label="Audience">
        <UInput
          v-model="context.audience"
          placeholder="e.g., Federal agency, Foundation board"
        />
      </UFormField>

      <UFormField label="Section">
        <UInput
          v-model="context.section"
          placeholder="e.g., Executive Summary, Budget Narrative"
        />
      </UFormField>

      <UFormField label="Tone">
        <div class="space-y-2">
          <URange
            v-model="context.tone"
            :min="0"
            :max="1"
            :step="0.1"
          />
          <div class="flex justify-between text-xs text-gray-500">
            <span>Formal</span>
            <span>Conversational</span>
          </div>
        </div>
      </UFormField>

      <UFormField label="Document Filters">
        <USelectMenu
          v-model="context.filters.programs"
          :options="programs"
          multiple
          placeholder="Filter by programs..."
        />

        <USelectMenu
          v-model="context.filters.docTypes"
          :options="documentTypes"
          multiple
          placeholder="Filter by document type..."
          class="mt-2"
        />
      </UFormField>
    </div>
  </UCard>

  <UCard v-if="activeSources.length > 0">
    <template #header>
      <h3 class="font-semibold">Active Sources</h3>
    </template>

    <div class="space-y-2">
      <button
        v-for="source in activeSources"
        :key="source.doc_id"
        class="w-full text-left p-2 rounded hover:bg-gray-50 transition"
        @click="viewDocument(source)"
      >
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium truncate">{{ source.filename }}</span>
          <UBadge size="sm">{{ Math.round(source.relevance_score * 100) }}%</UBadge>
        </div>
        <p class="text-xs text-gray-500">{{ source.doc_type }} • {{ source.year }}</p>
      </button>
    </div>
  </UCard>
</div>
```

---

### 7. Past Outputs & Success Tracking

#### `OutputsPage.vue` (`/pages/outputs/index.vue`)

**Header:**
- Page title: "Past Outputs"
- View toggle: Grid / List (URadioGroup)
- Search bar (full-text search across title, content, funder, notes)
- `UButton` "Create Manual Output" (opens modal)

**Filter Sidebar:**
```typescript
const filters = ref({
  outputType: [] as OutputType[],
  status: [] as OutputStatus[],
  funderName: '',
  dateRange: { start: null, end: null },
  writingStyleId: null
})
```

**Grid View:**
```vue
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <UCard
    v-for="output in outputs"
    :key="output.output_id"
    class="cursor-pointer hover:shadow-lg transition"
    @click="navigateTo(`/outputs/${output.output_id}`)"
  >
    <template #header>
      <div class="flex items-start justify-between">
        <h3 class="font-semibold line-clamp-2">{{ output.title }}</h3>
        <UBadge :color="getStatusColor(output.status)">
          {{ output.status }}
        </UBadge>
      </div>
    </template>

    <div class="space-y-2">
      <div class="flex items-center gap-2 text-sm text-gray-600">
        <UIcon name="i-heroicons-document-text" class="w-4 h-4" />
        <span>{{ output.word_count?.toLocaleString() }} words</span>
      </div>

      <div v-if="output.funder_name" class="text-sm">
        <span class="font-medium">Funder:</span> {{ output.funder_name }}
      </div>

      <div v-if="output.requested_amount" class="text-sm">
        <span class="font-medium">Requested:</span>
        {{ formatCurrency(output.requested_amount) }}
      </div>

      <div v-if="output.awarded_amount" class="text-sm text-green-600">
        <span class="font-medium">Awarded:</span>
        {{ formatCurrency(output.awarded_amount) }}
      </div>

      <p class="text-xs text-gray-500">
        Created {{ formatDate(output.created_at) }}
      </p>
    </div>
  </UCard>
</div>
```

**List View:**
```typescript
const columns = [
  { key: 'title', label: 'Title', sortable: true },
  { key: 'output_type', label: 'Type' },
  { key: 'status', label: 'Status', sortable: true },
  { key: 'funder_name', label: 'Funder' },
  { key: 'requested_amount', label: 'Requested', sortable: true },
  { key: 'awarded_amount', label: 'Awarded', sortable: true },
  { key: 'submission_date', label: 'Submitted', sortable: true },
  { key: 'actions', label: '' }
]
```

---

#### `OutputDetailPage.vue` (`/pages/outputs/[id].vue`)

**Layout:** 2-column (content preview + metadata/tracking)

**Left Column:**
- Header with title (editable), back button, actions dropdown (Export, Delete)
- Content preview (read-only, formatted display or UTextarea)
- Word count, created date

**Right Column:**

**Metadata Panel:**
```vue
<UCard>
  <template #header>Metadata</template>
  <dl class="space-y-2 text-sm">
    <div>
      <dt class="font-medium text-gray-500">Type</dt>
      <dd>{{ output.output_type }}</dd>
    </div>
    <div>
      <dt class="font-medium text-gray-500">Word Count</dt>
      <dd>{{ output.word_count?.toLocaleString() }}</dd>
    </div>
    <div>
      <dt class="font-medium text-gray-500">Created</dt>
      <dd>{{ formatDate(output.created_at) }}</dd>
    </div>
    <div v-if="output.writing_style_id">
      <dt class="font-medium text-gray-500">Writing Style</dt>
      <dd>{{ getStyleName(output.writing_style_id) }}</dd>
    </div>
    <div v-if="output.conversation_id">
      <dt class="font-medium text-gray-500">From Conversation</dt>
      <dd>
        <NuxtLink :to="`/chat/${output.conversation_id}`" class="text-primary-600 hover:underline">
          View conversation →
        </NuxtLink>
      </dd>
    </div>
  </dl>
</UCard>
```

**Success Tracking Form:**
```vue
<UCard>
  <template #header>Grant Success Tracking</template>

  <UForm :state="successForm" @submit="updateSuccessTracking">
    <UFormField label="Status" required>
      <USelect
        v-model="successForm.status"
        :options="statusOptions"
        @change="handleStatusChange"
      />
    </UFormField>

    <UFormField label="Funder Name">
      <UInput v-model="successForm.funder_name" />
    </UFormField>

    <UFormField label="Requested Amount">
      <UInput
        v-model="successForm.requested_amount"
        type="number"
        icon="i-heroicons-currency-dollar"
      />
    </UFormField>

    <UFormField label="Submission Date">
      <UDatePicker v-model="successForm.submission_date" />
    </UFormField>

    <!-- Only show if status is awarded or not_awarded -->
    <template v-if="['awarded', 'not_awarded'].includes(successForm.status)">
      <UFormField label="Decision Date">
        <UDatePicker v-model="successForm.decision_date" />
      </UFormField>

      <UFormField v-if="successForm.status === 'awarded'" label="Awarded Amount">
        <UInput
          v-model="successForm.awarded_amount"
          type="number"
          icon="i-heroicons-currency-dollar"
        />
      </UFormField>
    </template>

    <UFormField label="Notes">
      <UTextarea
        v-model="successForm.success_notes"
        rows="4"
        placeholder="Add notes about the submission, review process, or outcome..."
      />
    </UFormField>

    <UButton type="submit" color="primary" block>
      Save Tracking Info
    </UButton>
  </UForm>
</UCard>
```

**Status Workflow Validation:**
```typescript
const statusTransitions = {
  draft: ['submitted', 'done'], // Can skip to done if not submitting
  submitted: ['pending'],
  pending: ['awarded', 'not_awarded'],
  awarded: [], // Terminal state
  not_awarded: [] // Terminal state
}

function validateStatusChange(from: OutputStatus, to: OutputStatus): boolean {
  return statusTransitions[from]?.includes(to) || false
}
```

**Export Options:**
```vue
<UDropdown :items="exportActions">
  <UButton icon="i-heroicons-arrow-down-tray">
    Export
  </UButton>
</UDropdown>

<script>
const exportActions = [
  [
    { label: 'Download as DOCX', icon: 'i-heroicons-document', click: () => exportDocx() },
    { label: 'Download as PDF', icon: 'i-heroicons-document-text', click: () => exportPdf() },
    { label: 'Copy to Clipboard', icon: 'i-heroicons-clipboard-document', click: () => copyToClipboard() }
  ]
]
</script>
```

---

### 8. Settings & Administration

#### `SettingsPage.vue` (`/pages/settings/index.vue`)

**Tabs:** UTabs component

**Tab 1: Profile**
```vue
<UForm :state="profileForm" @submit="updateProfile">
  <UFormField label="Full Name">
    <UInput v-model="profileForm.full_name" />
  </UFormField>

  <UFormField label="Email">
    <UInput v-model="profileForm.email" type="email" disabled />
    <template #help>Contact admin to change email</template>
  </UFormField>

  <UFormField label="Current Password">
    <UInput v-model="profileForm.current_password" type="password" />
  </UFormField>

  <UFormField label="New Password">
    <UInput v-model="profileForm.new_password" type="password" />
  </UFormField>

  <UFormField label="Confirm New Password">
    <UInput v-model="profileForm.confirm_password" type="password" />
  </UFormField>

  <UButton type="submit" color="primary">Save Changes</UButton>
</UForm>
```

**Tab 2: Preferences**
```vue
<div class="space-y-6">
  <UFormField label="Default Writing Style">
    <USelectMenu
      v-model="preferences.default_writing_style_id"
      :options="writingStyles"
      placeholder="Select default style..."
    />
  </UFormField>

  <UFormField label="Default Audience">
    <UInput
      v-model="preferences.default_audience"
      placeholder="e.g., Federal agencies"
    />
  </UFormField>

  <UFormField label="Notifications">
    <div class="space-y-2">
      <UCheckbox
        v-model="preferences.email_notifications"
        label="Email notifications for important updates"
      />
      <UCheckbox
        v-model="preferences.browser_notifications"
        label="Browser notifications"
      />
    </div>
  </UFormField>

  <UFormField label="Theme">
    <URadioGroup
      v-model="preferences.theme"
      :options="[
        { label: 'Light', value: 'light' },
        { label: 'Dark', value: 'dark' },
        { label: 'System', value: 'auto' }
      ]"
    />
  </UFormField>
</div>
```

---

#### `UserManagementPage.vue` (`/pages/admin/users.vue`)

**Admin Only**

**Header:**
- Page title: "User Management"
- `UButton` "Add User" (opens modal)

**Main Content:**

UTable:
```typescript
const columns = [
  { key: 'full_name', label: 'Name', sortable: true },
  { key: 'email', label: 'Email', sortable: true },
  { key: 'role', label: 'Role' },
  { key: 'is_active', label: 'Status' },
  { key: 'last_login', label: 'Last Login', sortable: true },
  { key: 'actions', label: '' }
]
```

**Cell Rendering:**
- **Role:** UBadge with color coding (admin=purple, editor=blue, writer=gray)
- **Status:** UToggle for active/inactive with confirmation
- **Actions:** UDropdown (Edit, Reset Password, Delete)

**UserModal Component:**
```vue
<UModal v-model="isOpen">
  <UCard>
    <template #header>
      <h3>{{ mode === 'create' ? 'Add User' : 'Edit User' }}</h3>
    </template>

    <UForm :state="form" @submit="handleSubmit">
      <UFormField label="Full Name" required>
        <UInput v-model="form.full_name" />
      </UFormField>

      <UFormField label="Email" required>
        <UInput v-model="form.email" type="email" />
      </UFormField>

      <UFormField label="Role" required>
        <USelectMenu
          v-model="form.role"
          :options="roleOptions"
        />
      </UFormField>

      <template v-if="mode === 'create'">
        <UFormField label="Password" required>
          <UInput v-model="form.password" type="password" />
        </UFormField>

        <UFormField label="Confirm Password" required>
          <UInput v-model="form.confirm_password" type="password" />
        </UFormField>
      </template>

      <UFormField label="Active">
        <UToggle v-model="form.is_active" />
      </UFormField>
    </UForm>

    <template #footer>
      <UButton color="gray" @click="isOpen = false">Cancel</UButton>
      <UButton color="primary" @click="handleSubmit">
        {{ mode === 'create' ? 'Create User' : 'Save Changes' }}
      </UButton>
    </template>
  </UCard>
</UModal>
```

---

## Composables & Utilities

### Authentication

**`useAuth.ts`** - Authentication state and operations

```typescript
export const useAuth = () => {
  // Cookies for token storage
  const accessToken = useCookie('access_token', {
    maxAge: 5 * 60 * 60, // 5 hours
    secure: true,
    sameSite: 'strict'
  })

  const refreshToken = useCookie('refresh_token', {
    maxAge: 7 * 24 * 60 * 60, // 7 days
    secure: true,
    sameSite: 'strict'
  })

  // User state
  const user = useState<UserResponse | null>('user', () => null)
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)

  // Login
  const login = async (email: string, password: string) => {
    const { apiFetch } = usePublicApi()

    try {
      const response = await apiFetch<LoginResponse>('/api/auth/login', {
        method: 'POST',
        body: { email, password }
      })

      accessToken.value = response.access_token
      refreshToken.value = response.refresh_token
      user.value = response.user

      return { success: true }
    } catch (error: any) {
      return {
        success: false,
        error: error.data?.detail || 'Login failed'
      }
    }
  }

  // Logout
  const logout = async () => {
    const { apiFetch } = useApi()

    try {
      await apiFetch('/api/auth/logout', { method: 'POST' })
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      accessToken.value = null
      refreshToken.value = null
      user.value = null
      navigateTo('/login')
    }
  }

  // Validate session
  const validateSession = async () => {
    if (!accessToken.value) {
      return false
    }

    const { apiFetch } = useApi()

    try {
      const response = await apiFetch<SessionResponse>('/api/auth/session')

      if (response.valid && response.user) {
        user.value = response.user
        return true
      }

      return false
    } catch (error) {
      return false
    }
  }

  // Check role
  const hasRole = (role: UserRole | UserRole[]) => {
    if (!user.value) return false

    const roles = Array.isArray(role) ? role : [role]
    return roles.includes(user.value.role)
  }

  return {
    user,
    isAuthenticated,
    login,
    logout,
    validateSession,
    hasRole,
    accessToken,
    refreshToken
  }
}
```

---

### API Composables

**`useDocuments.ts`** - Document management operations

```typescript
export const useDocuments = () => {
  const { apiFetch } = useApi()

  const documents = ref<DocumentResponse[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Get all documents with filters
  const getDocuments = async (filters?: DocumentFilters, pagination?: ListQueryParams) => {
    loading.value = true
    error.value = null

    try {
      const response = await apiFetch<PaginatedResponse<DocumentResponse>>('/api/documents', {
        params: {
          ...filters,
          ...pagination
        }
      })

      documents.value = response.items
      return response
    } catch (err: any) {
      error.value = err.data?.detail || 'Failed to fetch documents'
      throw err
    } finally {
      loading.value = false
    }
  }

  // Upload document
  const uploadDocument = async (file: File, metadata: DocumentMetadata) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('metadata', JSON.stringify(metadata))

    try {
      const response = await apiFetch<DocumentResponse>('/api/documents/upload', {
        method: 'POST',
        body: formData,
        headers: {
          // Don't set Content-Type, let browser set it with boundary
        }
      })

      return response
    } catch (err: any) {
      error.value = err.data?.detail || 'Upload failed'
      throw err
    }
  }

  // Delete document
  const deleteDocument = async (docId: string) => {
    try {
      await apiFetch(`/api/documents/${docId}`, {
        method: 'DELETE'
      })

      // Remove from local state
      documents.value = documents.value.filter(d => d.document_id !== docId)
    } catch (err: any) {
      error.value = err.data?.detail || 'Delete failed'
      throw err
    }
  }

  // Get document stats
  const getStats = async () => {
    try {
      return await apiFetch('/api/documents/stats')
    } catch (err: any) {
      error.value = err.data?.detail || 'Failed to fetch stats'
      throw err
    }
  }

  return {
    documents,
    loading,
    error,
    getDocuments,
    uploadDocument,
    deleteDocument,
    getStats
  }
}
```

**`usePrograms.ts`** - Programs CRUD operations

```typescript
export const usePrograms = () => {
  const { apiFetch } = useApi()

  const programs = ref<ProgramResponse[]>([])
  const loading = ref(false)

  const getPrograms = async () => {
    loading.value = true
    try {
      programs.value = await apiFetch<ProgramResponse[]>('/api/programs')
    } finally {
      loading.value = false
    }
  }

  const getActivePrograms = async () => {
    return await apiFetch<string[]>('/api/programs/active')
  }

  const createProgram = async (data: ProgramRequest) => {
    const program = await apiFetch<ProgramResponse>('/api/programs', {
      method: 'POST',
      body: data
    })

    programs.value.push(program)
    return program
  }

  const updateProgram = async (id: string, data: Partial<ProgramRequest>) => {
    const program = await apiFetch<ProgramResponse>(`/api/programs/${id}`, {
      method: 'PUT',
      body: data
    })

    const index = programs.value.findIndex(p => p.program_id === id)
    if (index !== -1) {
      programs.value[index] = program
    }

    return program
  }

  const deleteProgram = async (id: string) => {
    await apiFetch(`/api/programs/${id}`, { method: 'DELETE' })
    programs.value = programs.value.filter(p => p.program_id !== id)
  }

  const reorderPrograms = async (newOrder: string[]) => {
    // Implementation depends on backend API
    // May require batch update or individual updates with display_order
  }

  return {
    programs,
    loading,
    getPrograms,
    getActivePrograms,
    createProgram,
    updateProgram,
    deleteProgram,
    reorderPrograms
  }
}
```

**`useWritingStyles.ts`** - Writing styles management

```typescript
export const useWritingStyles = () => {
  const { apiFetch } = useApi()

  const writingStyles = ref<WritingStyle[]>([])
  const loading = ref(false)

  const getWritingStyles = async () => {
    loading.value = true
    try {
      writingStyles.value = await apiFetch<WritingStyle[]>('/api/writing-styles')
    } finally {
      loading.value = false
    }
  }

  const analyzeWritingSamples = async (samples: string[], styleType?: WritingStyleType) => {
    return await apiFetch<StyleAnalysisResponse>('/api/writing-styles/analyze', {
      method: 'POST',
      body: {
        samples,
        style_type: styleType
      }
    })
  }

  const createWritingStyle = async (data: WritingStyleCreateRequest) => {
    const style = await apiFetch<WritingStyle>('/api/writing-styles', {
      method: 'POST',
      body: data
    })

    writingStyles.value.push(style)
    return style
  }

  const updateWritingStyle = async (id: string, data: WritingStyleUpdateRequest) => {
    const style = await apiFetch<WritingStyle>(`/api/writing-styles/${id}`, {
      method: 'PUT',
      body: data
    })

    const index = writingStyles.value.findIndex(s => s.style_id === id)
    if (index !== -1) {
      writingStyles.value[index] = style
    }

    return style
  }

  const deleteWritingStyle = async (id: string) => {
    await apiFetch(`/api/writing-styles/${id}`, { method: 'DELETE' })
    writingStyles.value = writingStyles.value.filter(s => s.style_id !== id)
  }

  return {
    writingStyles,
    loading,
    getWritingStyles,
    analyzeWritingSamples,
    createWritingStyle,
    updateWritingStyle,
    deleteWritingStyle
  }
}
```

**`useChat.ts`** - Conversation management

```typescript
export const useChat = () => {
  const { apiFetch } = useApi()

  const conversations = ref<Conversation[]>([])
  const currentConversation = ref<Conversation | null>(null)
  const messages = ref<ChatMessage[]>([])
  const loading = ref(false)

  const getConversations = async () => {
    loading.value = true
    try {
      conversations.value = await apiFetch<Conversation[]>('/api/chat')
    } finally {
      loading.value = false
    }
  }

  const getConversation = async (id: string) => {
    loading.value = true
    try {
      currentConversation.value = await apiFetch<Conversation>(`/api/chat/${id}`)
      messages.value = currentConversation.value.messages || []
    } finally {
      loading.value = false
    }
  }

  const createConversation = async (name: string) => {
    const conversation = await apiFetch<Conversation>('/api/chat', {
      method: 'POST',
      body: { name }
    })

    conversations.value.unshift(conversation)
    return conversation
  }

  const sendMessage = async (conversationId: string, message: string, context?: ConversationContext) => {
    const response = await apiFetch<ChatResponse>('/api/chat', {
      method: 'POST',
      body: {
        message,
        conversation_id: conversationId,
        context
      }
    })

    return response
  }

  const deleteConversation = async (id: string) => {
    await apiFetch(`/api/chat/${id}`, { method: 'DELETE' })
    conversations.value = conversations.value.filter(c => c.conversation_id !== id)
  }

  const updateConversationContext = async (id: string, context: ConversationContext) => {
    return await apiFetch<ConversationContextResponse>(`/api/chat/conversations/${id}/context`, {
      method: 'POST',
      body: { context }
    })
  }

  const getConversationContext = async (id: string) => {
    return await apiFetch<ConversationContextResponse>(`/api/chat/conversations/${id}/context`)
  }

  return {
    conversations,
    currentConversation,
    messages,
    loading,
    getConversations,
    getConversation,
    createConversation,
    sendMessage,
    deleteConversation,
    updateConversationContext,
    getConversationContext
  }
}
```

**`useStreaming.ts`** - SSE streaming for real-time AI responses

```typescript
export const useStreaming = () => {
  const config = useRuntimeConfig()
  const { accessToken } = useAuth()

  const streamChatResponse = async (
    query: QueryRequest,
    onChunk: (content: string) => void,
    onSources?: (sources: Source[]) => void,
    onDone?: () => void,
    onError?: (error: Error) => void
  ) => {
    try {
      const response = await fetch(`${config.public.apiBase}/api/query/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken.value}`
        },
        body: JSON.stringify(query)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('No response body')
      }

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          onDone?.()
          break
        }

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data:')) {
            try {
              const data = JSON.parse(line.slice(5).trim())

              if (data.type === 'content') {
                onChunk(data.text)
              } else if (data.type === 'sources') {
                onSources?.(data.sources)
              } else if (data.type === 'done') {
                onDone?.()
              } else if (data.type === 'error') {
                onError?.(new Error(data.message))
              }
            } catch (parseError) {
              console.error('Error parsing SSE data:', parseError)
            }
          }
        }
      }
    } catch (error) {
      onError?.(error as Error)
    }
  }

  return {
    streamChatResponse
  }
}
```

**`useOutputs.ts`** - Outputs management and analytics

```typescript
export const useOutputs = () => {
  const { apiFetch } = useApi()

  const outputs = ref<OutputResponse[]>([])
  const loading = ref(false)

  const getOutputs = async (filters?: any, pagination?: ListQueryParams) => {
    loading.value = true
    try {
      const response = await apiFetch<PaginatedResponse<OutputResponse>>('/api/outputs', {
        params: {
          ...filters,
          ...pagination
        }
      })

      outputs.value = response.items
      return response
    } finally {
      loading.value = false
    }
  }

  const getOutput = async (id: string) => {
    return await apiFetch<OutputResponse>(`/api/outputs/${id}`)
  }

  const createOutput = async (data: OutputCreateRequest) => {
    const output = await apiFetch<OutputResponse>('/api/outputs', {
      method: 'POST',
      body: data
    })

    outputs.value.unshift(output)
    return output
  }

  const updateOutput = async (id: string, data: OutputUpdateRequest) => {
    const output = await apiFetch<OutputResponse>(`/api/outputs/${id}`, {
      method: 'PUT',
      body: data
    })

    const index = outputs.value.findIndex(o => o.output_id === id)
    if (index !== -1) {
      outputs.value[index] = output
    }

    return output
  }

  const deleteOutput = async (id: string) => {
    await apiFetch(`/api/outputs/${id}`, { method: 'DELETE' })
    outputs.value = outputs.value.filter(o => o.output_id !== id)
  }

  const getStats = async () => {
    return await apiFetch<OutputStatsResponse>('/api/outputs/stats')
  }

  const getAnalytics = async (filters?: any) => {
    return await apiFetch('/api/outputs/analytics/summary', {
      params: filters
    })
  }

  return {
    outputs,
    loading,
    getOutputs,
    getOutput,
    createOutput,
    updateOutput,
    deleteOutput,
    getStats,
    getAnalytics
  }
}
```

---

## Implementation Phases

### Phase 1: MVP Foundation (Weeks 1-2)

**Status:** In Progress ✓

**Completed:**
- [x] Core API composable with auth token injection and refresh

**Remaining:**
1. Authentication composables and login page
2. Default layout (top bar + sidebar)
3. Dashboard with stats and quick chat
4. Document upload workflow
5. Document library with filtering
6. Basic chat interface (non-streaming)
7. Outputs list view

**Success Criteria:**
- Users can log in and see their profile
- Documents can be uploaded with metadata
- Basic chat works without streaming
- Past outputs can be viewed

---

### Phase 2: Core Features (Weeks 3-4)

1. Programs CRUD with drag-and-drop reordering
2. Writing styles creation wizard with AI analysis
3. Full chat interface with SSE streaming
4. Chat context persistence and management
5. Output success tracking form with workflow validation
6. Optional onboarding tour for first-time users

**Success Criteria:**
- Real-time AI streaming works smoothly
- Writing styles can be created and applied
- Grant success tracking is functional
- Context persists across chat sessions

---

### Phase 3: Enhancement (Weeks 5-6)

1. User management (admin panel)
2. Settings pages (profile, preferences)
3. Analytics dashboard for grant success metrics
4. Advanced filters and search across all modules
5. Export functionality (DOCX, PDF)
6. Mobile responsive refinements

**Success Criteria:**
- Admins can manage users and roles
- Analytics provide actionable insights
- All features work on mobile devices
- Export formats are properly formatted

---

### Phase 4: Polish (Weeks 7-8)

1. Performance optimization (lazy loading, code splitting)
2. Loading states and skeleton screens
3. Error boundaries and retry logic
4. Accessibility improvements (ARIA, keyboard nav)
5. User testing and feedback iteration
6. Documentation and help content

**Success Criteria:**
- Lighthouse score > 90
- WCAG 2.1 AA compliance
- No critical bugs
- Positive user feedback

---

## Key UX Principles

### 1. Progressive Disclosure
Show only what users need when they need it. Hide advanced options behind expandable sections or modal dialogs.

**Example:** Document filters start collapsed on mobile, advanced chat settings in right sidebar.

### 2. Immediate Feedback
Every action should have instant visual feedback.

**Examples:**
- Button loading states
- Optimistic UI updates
- Toast notifications for success/error
- Progress indicators for long operations

### 3. Familiar Patterns
Use established UI patterns that users recognize.

**Examples:**
- Gmail-like sidebar navigation
- Slack-like chat interface
- Google Drive-like file upload
- Trello-like status workflows

### 4. Forgiving Interactions
Make it easy to recover from mistakes.

**Examples:**
- Confirmation dialogs for destructive actions
- Undo options where possible
- Auto-save drafts
- "Are you sure?" warnings

### 5. Contextual Help
Provide help exactly when and where it's needed.

**Examples:**
- Tooltips on hover
- Empty states with clear CTAs
- Inline validation messages
- Placeholder text with examples

### 6. Keyboard Accessibility
Support power users with keyboard shortcuts.

**Examples:**
- `Cmd/Ctrl + K` for search
- `/` to focus chat input
- `Esc` to close modals
- Arrow keys for navigation

---

## Technical Considerations

### Performance

**Code Splitting:**
```typescript
// Lazy load heavy components
const ChatInterface = defineAsyncComponent(() => import('~/components/chat/ChatInterface.vue'))
const WritingStyleWizard = defineAsyncComponent(() => import('~/components/WritingStyleWizard.vue'))
```

**Virtual Scrolling:**
For long lists (documents, conversations), use virtual scrolling to render only visible items.

**Image Optimization:**
Use Nuxt Image for automatic optimization and lazy loading.

**Bundle Size:**
- Keep bundle < 200KB gzipped
- Lazy load non-critical features
- Tree-shake unused code

---

### State Management

**Composables over Vuex/Pinia:**
Use Vue 3 composables for most state management. Only use Pinia if truly global state is needed.

**Local vs. Global State:**
- **Local:** Component-specific UI state (modals, dropdowns)
- **Composable:** Feature-specific state (documents list, chat messages)
- **Global:** User auth, app-wide settings

---

### Error Handling

**Error Boundary Component:**
```vue
<template>
  <div v-if="error" class="error-boundary">
    <UAlert color="error">
      <template #title>Something went wrong</template>
      <template #description>{{ error.message }}</template>
    </UAlert>
    <UButton @click="retry">Try Again</UButton>
  </div>
  <slot v-else />
</template>

<script setup>
const error = ref(null)

onErrorCaptured((err) => {
  error.value = err
  return false // Stop propagation
})

const retry = () => {
  error.value = null
  // Reload component
}
</script>
```

**Global Error Handler:**
```typescript
// plugins/error-handler.ts
export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.hook('vue:error', (error, instance, info) => {
    // Log to error tracking service
    console.error('Global error:', error, info)

    // Show toast notification
    const toast = useToast()
    toast.add({
      title: 'An error occurred',
      description: error.message,
      color: 'red'
    })
  })
})
```

---

### Accessibility

**ARIA Labels:**
All interactive elements should have clear labels.

```vue
<UButton
  icon="i-heroicons-trash"
  aria-label="Delete document"
  @click="deleteDocument"
/>
```

**Keyboard Navigation:**
Ensure all features are accessible via keyboard.

**Focus Management:**
Manage focus when opening/closing modals and navigating routes.

**Color Contrast:**
Maintain WCAG AA contrast ratios (4.5:1 for text).

**Screen Reader Support:**
Use semantic HTML and ARIA attributes appropriately.

---

### Security

**XSS Prevention:**
- Sanitize user input before rendering
- Use `v-text` instead of `v-html` where possible
- Validate and escape markdown content

**CSRF Protection:**
- SameSite cookies (already configured)
- CSRF tokens for state-changing operations (if needed)

**Token Security:**
- Store tokens in httpOnly, secure cookies
- Automatic token refresh
- Clear tokens on logout

**Content Security Policy:**
Configure CSP headers in `nuxt.config.ts`:

```typescript
export default defineNuxtConfig({
  app: {
    head: {
      meta: [
        {
          'http-equiv': 'Content-Security-Policy',
          content: "default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
        }
      ]
    }
  }
})
```

---

## Appendix: Component Library (Nuxt UI)

### Commonly Used Components

**Layout:**
- `UContainer` - Responsive container
- `UCard` - Card component
- `UDivider` - Horizontal/vertical divider

**Forms:**
- `UForm` - Form wrapper with validation
- `UFormField` - Form field with label
- `UInput` - Text input
- `UTextarea` - Multi-line text input
- `USelect` - Dropdown select
- `USelectMenu` - Multi-select dropdown
- `UCheckbox` - Checkbox
- `URadio` / `URadioGroup` - Radio buttons
- `UToggle` - Switch toggle
- `URange` - Slider
- `UDatePicker` - Date picker
- `UFileUpload` - File upload with drag-drop

**Navigation:**
- `UButton` - Button
- `UDropdown` - Dropdown menu
- `UTabs` - Tabbed interface
- `UVerticalNavigation` - Sidebar navigation
- `UPagination` - Pagination controls
- `UBreadcrumbs` - Breadcrumb navigation

**Feedback:**
- `UAlert` - Alert messages
- `UToast` / `useToast()` - Toast notifications
- `UProgress` - Progress bar
- `UBadge` - Status badge
- `USkeleton` - Loading skeleton

**Overlay:**
- `UModal` - Modal dialog
- `USlideOver` - Slide-over panel
- `UPopover` - Popover tooltip
- `UTooltip` - Tooltip

**Data Display:**
- `UTable` - Data table
- `UAccordion` - Accordion/collapse
- `UAvatar` - User avatar
- `UIcon` - Icon component

---

## Conclusion

This plan provides a comprehensive roadmap for building a user-friendly, production-ready frontend for Org Archivist. The phased approach ensures we deliver value incrementally while maintaining code quality and user experience.

**Next Steps:**
1. Complete Phase 1 tasks (authentication, layout, basic features)
2. Gather user feedback on MVP
3. Iterate and improve based on usage patterns
4. Proceed with Phase 2 (core features)

**Questions or Feedback:**
As implementation progresses, this document should be updated to reflect actual decisions, challenges, and solutions discovered during development.
