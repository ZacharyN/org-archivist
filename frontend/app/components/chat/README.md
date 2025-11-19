# Chat Components

This directory contains Vue components for the AI writing assistant chat interface.

## Components

### ConversationList

The main sidebar component that displays a list of conversations with search and grouping functionality.

**Location:** `components/chat/ConversationList.vue`

**Features:**
- "New Chat" button at the top
- Search input for filtering conversations by name or message content
- Conversations grouped by date (Today, Yesterday, Last 7 days, Older)
- Active conversation highlighting with left border
- Loading and empty states
- Click to select/navigate to conversation

**Props:**
```typescript
interface Props {
  /** Currently active conversation ID */
  activeConversationId?: string | null
}
```

**Events:**
```typescript
interface Emits {
  /** Emitted when user wants to create a new chat */
  (e: 'new-chat'): void
  /** Emitted when user selects a conversation */
  (e: 'select-conversation', conversation: Conversation): void
}
```

**Usage Example:**
```vue
<template>
  <div class="flex h-screen">
    <!-- Sidebar -->
    <div class="w-80 flex-shrink-0">
      <ConversationList
        :active-conversation-id="currentConversationId"
        @new-chat="handleNewChat"
        @select-conversation="handleSelectConversation"
      />
    </div>

    <!-- Main Chat Area -->
    <div class="flex-1">
      <!-- Your chat interface here -->
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Conversation } from '~/types/api'

const currentConversationId = ref<string | null>(null)

const handleNewChat = () => {
  // Navigate to new chat or create conversation
  navigateTo('/chat/new')
}

const handleSelectConversation = (conversation: Conversation) => {
  // Navigate to conversation
  navigateTo(`/chat/${conversation.conversation_id}`)
}
</script>
```

### ConversationItem

Individual conversation list item component used within ConversationList.

**Location:** `components/chat/ConversationItem.vue`

**Features:**
- Displays conversation name (falls back to "Untitled Conversation")
- Shows last message preview (truncated to 60 characters)
- Displays relative timestamp (e.g., "2h ago", "3d ago")
- Message count badge
- Active state highlighting with primary color theme
- Hover effects for better UX

**Props:**
```typescript
interface Props {
  /** Conversation data */
  conversation: Conversation
  /** Whether this conversation is currently active */
  isActive?: boolean
}
```

**Events:**
```typescript
interface Emits {
  /** Emitted when conversation item is clicked */
  (e: 'click'): void
}
```

**Usage Example:**
```vue
<template>
  <ConversationItem
    :conversation="conversation"
    :is-active="conversation.conversation_id === activeId"
    @click="selectConversation(conversation)"
  />
</template>

<script setup lang="ts">
import type { Conversation } from '~/types/api'

const activeId = ref('some-conversation-id')

const selectConversation = (conversation: Conversation) => {
  console.log('Selected:', conversation.conversation_id)
}
</script>
```

### ChatMessage

Displays individual chat messages with markdown rendering, source citations, and actions.

**Location:** `components/chat/ChatMessage.vue`

**Features:**
- Different styling for user vs assistant messages
- Markdown rendering with syntax highlighting
- Collapsible source citations (assistant messages)
- Relative timestamp display
- Copy to clipboard functionality
- Regenerate button for assistant messages
- Confidence scores and metadata display

**Props:**
```typescript
interface Props {
  /** The chat message to display */
  message: ChatMessage
  /** Optional sources for assistant messages */
  sources?: Source[]
}
```

**Events:**
```typescript
interface Emits {
  /** Emitted when user clicks regenerate button */
  (e: 'regenerate'): void
}
```

**Usage Example:**
```vue
<template>
  <div class="chat-messages">
    <ChatMessage
      v-for="msg in messages"
      :key="msg.message_id"
      :message="msg"
      :sources="msg.sources"
      @regenerate="handleRegenerate(msg)"
    />
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage, Source } from '~/types/api'

const messages = ref<ChatMessage[]>([])

const handleRegenerate = (message: ChatMessage) => {
  console.log('Regenerating message:', message.message_id)
}
</script>
```

### ChatInput

Input area for composing and sending chat messages with auto-resize and keyboard shortcuts.

**Location:** `components/chat/ChatInput.vue`

**Features:**
- Auto-resizing textarea (max 4 rows)
- Send button (disabled when empty or streaming)
- Word count display
- Character count badge for long messages
- Enter to send, Shift+Enter for new line
- Keyboard shortcuts hint display

**Props:**
```typescript
interface Props {
  /** Current message text (for v-model) */
  modelValue?: string
  /** Whether the assistant is currently streaming a response */
  isStreaming?: boolean
}
```

**Events:**
```typescript
interface Emits {
  /** Emitted when modelValue changes */
  (e: 'update:modelValue', value: string): void
  /** Emitted when user sends a message */
  (e: 'send', message: string): void
}
```

**Usage Example:**
```vue
<template>
  <div class="chat-container">
    <!-- Messages Area -->
    <div class="messages">
      <ChatMessage
        v-for="msg in messages"
        :key="msg.message_id"
        :message="msg"
      />
    </div>

    <!-- Input Area -->
    <ChatInput
      v-model="currentMessage"
      :is-streaming="isStreaming"
      @send="handleSendMessage"
    />
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage } from '~/types/api'

const currentMessage = ref('')
const isStreaming = ref(false)
const messages = ref<ChatMessage[]>([])

const handleSendMessage = async (message: string) => {
  console.log('Sending:', message)

  // Add user message
  messages.value.push({
    role: 'user',
    content: message,
    timestamp: new Date().toISOString()
  })

  // Send to API and stream response
  isStreaming.value = true
  try {
    // Your API call here
  } finally {
    isStreaming.value = false
  }
}
</script>
```

### ContextPanel

Right sidebar component for chat interface with context settings and document filters.

**Location:** `components/chat/ContextPanel.vue`

**Features:**
- Generation settings form (writing style, audience, section, tone slider)
- Document filters (programs, doc types, years) with multi-select
- Active sources list with relevance scores
- Reset context functionality
- Apply settings button
- Custom scrollbar styling

**Props:**
```typescript
interface Props {
  /** Current conversation context */
  context?: ConversationContext
  /** Sources from last generation */
  sources?: Source[]
  /** Available programs for filtering */
  programs?: string[]
  /** Available writing styles */
  writingStyles?: WritingStyle[]
}
```

**Events:**
```typescript
interface Emits {
  /** Emitted when user applies context changes */
  (e: 'update:context', context: ConversationContext): void
}
```

**Usage Example:**
```vue
<template>
  <div class="flex h-screen">
    <!-- Main Chat Area -->
    <div class="flex-1">
      <!-- Chat messages and input -->
    </div>

    <!-- Right Sidebar -->
    <div class="w-80 flex-shrink-0">
      <ContextPanel
        :context="conversationContext"
        :sources="activeSources"
        :programs="availablePrograms"
        :writing-styles="writingStyles"
        @update:context="handleContextUpdate"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ConversationContext, Source, WritingStyle } from '~/types/api'

const conversationContext = ref<ConversationContext>({
  writing_style_id: undefined,
  audience: '',
  section: '',
  tone: 'balanced',
  filters: {}
})

const activeSources = ref<Source[]>([])
const availablePrograms = ref<string[]>(['Education', 'Health', 'Arts'])
const writingStyles = ref<WritingStyle[]>([])

const handleContextUpdate = (context: ConversationContext) => {
  console.log('Context updated:', context)
  conversationContext.value = context
  // Apply to next generation request
}
</script>
```

## Dependencies

These components use:
- **Nuxt UI v4** - UI component library (UButton, UInput, UTextarea, USelectMenu, URange, UIcon, UBadge, UAccordion, UFormField)
- **marked** - Markdown parser (ChatMessage)
- **isomorphic-dompurify** - HTML sanitizer (ChatMessage)
- **useChat** - Composable for conversation state management
- **ChatMessage, Source, Conversation, ConversationContext, WritingStyle** - TypeScript interfaces from `~/types/api`

## Styling Guide

All styling follows the Nuxt UI v4 patterns documented in `/docs/nuxt-ui-component-guide.md`:
- Colors: `primary`, `neutral`, `success`, `info`, `warning`, `error`
- Sizes: `xs`, `sm`, `md`, `lg`, `xl`
- Variants: `solid`, `outline`, `soft`, `ghost`, `link`, `subtle`

## Date Grouping Logic

Conversations are grouped by:
1. **Today** - Updated today (since midnight)
2. **Yesterday** - Updated yesterday
3. **Last 7 Days** - Updated within the past week
4. **Older** - Updated more than 7 days ago

## Search Functionality

The search filters conversations by:
- Conversation name (case-insensitive)
- Last message content (case-insensitive)

## Future Enhancements

Potential improvements:
- Context menu for conversation options (rename, delete, archive)
- Drag-and-drop to reorder conversations
- Pin/favorite conversations
- Conversation tags/labels
- Unread message indicators
- Keyboard navigation support
