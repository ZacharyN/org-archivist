# Nuxt 4 Frontend Setup Guide

## Overview

This document provides comprehensive setup instructions for the Nuxt 4 frontend implementation for the Org Archivist project. This replaces the previous Streamlit frontend with a modern, production-ready Vue 3/Nuxt 4 application.

## Project Scope

**IN SCOPE:**
- Nuxt 4 framework installation and configuration
- Nuxt UI official module integration
- Nuxt Icons official module integration
- Docker containerization
- Backend API connectivity
- Development environment setup

**OUT OF SCOPE (Future Phases):**
- UI/UX design implementation
- User workflow development
- Authentication implementation
- State management (Pinia)
- Component library development

## Prerequisites

### System Requirements
- **Node.js**: v18.0.0 or higher (v20.x recommended)
- **npm**: v9.0.0 or higher
- **Docker**: Latest version
- **Docker Compose**: v2.0 or higher

### Verify Prerequisites
```bash
node --version   # Should be >= 18.0.0
npm --version    # Should be >= 9.0.0
docker --version
docker-compose --version
```

## Installation Guide

### Phase 1: Project Initialization

#### 1.1 Backup Existing Frontend (If Applicable)
```bash
# From project root
cd /home/zacharyn/PyCharm-Projects/org-archivist
mv frontend frontend-streamlit-backup
mkdir frontend
```

#### 1.2 Initialize Nuxt 4 Project
```bash
cd frontend
npx nuxi@latest init .
# Select: TypeScript
# Package manager: npm
```

#### 1.3 Install Core Dependencies
```bash
# Install Nuxt UI (includes Tailwind CSS)
npm install @nuxt/ui

# Install Nuxt Icons
npm install @nuxt/icon

# Install development dependencies
npm install -D @nuxtjs/tailwindcss
```

### Phase 2: Configuration

#### 2.1 Nuxt Configuration (`nuxt.config.ts`)

Create or update `frontend/nuxt.config.ts`:

```typescript
// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-04-03',
  devtools: { enabled: true },

  modules: [
    '@nuxt/ui',
    '@nuxt/icon'
  ],

  runtimeConfig: {
    // Private keys (server-side only)
    // Add any server-side secrets here

    // Public keys (exposed to client)
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
      environment: process.env.NUXT_PUBLIC_ENVIRONMENT || 'development'
    }
  },

  // Proxy API requests to backend (for CORS)
  nitro: {
    devProxy: {
      '/api': {
        target: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },

  // TypeScript configuration
  typescript: {
    strict: true,
    typeCheck: true
  },

  // Development server configuration
  devServer: {
    port: 3000,
    host: '0.0.0.0'
  }
})
```

#### 2.2 Environment Configuration

Create `frontend/.env`:

```env
# Backend API Configuration
NUXT_PUBLIC_API_BASE=http://localhost:8000
NUXT_PUBLIC_ENVIRONMENT=development

# For Docker
# NUXT_PUBLIC_API_BASE=http://backend:8000
```

Create `frontend/.env.example`:

```env
# Backend API Configuration
NUXT_PUBLIC_API_BASE=http://localhost:8000
NUXT_PUBLIC_ENVIRONMENT=development
```

#### 2.3 TypeScript Configuration

Update `frontend/tsconfig.json`:

```json
{
  "extends": "./.nuxt/tsconfig.json",
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "paths": {
      "~/*": ["./*"],
      "@/*": ["./*"]
    }
  }
}
```

### Phase 3: Project Structure

Create the following directory structure:

```bash
mkdir -p frontend/layouts
mkdir -p frontend/pages
mkdir -p frontend/components
mkdir -p frontend/composables
mkdir -p frontend/types
mkdir -p frontend/utils
mkdir -p frontend/public/assets
```

#### 3.1 Root Component (`app.vue`)

```vue
<template>
  <div>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>
```

#### 3.2 Default Layout (`layouts/default.vue`)

```vue
<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <header class="bg-white dark:bg-gray-800 shadow">
      <div class="container mx-auto px-4 py-6">
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
          Org Archivist
        </h1>
      </div>
    </header>

    <main class="container mx-auto px-4 py-8">
      <slot />
    </main>
  </div>
</template>
```

#### 3.3 Home Page (`pages/index.vue`)

```vue
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
            :color="healthStatus.ok ? 'green' : 'red'"
            :title="healthStatus.ok ? 'Backend Connected' : 'Backend Error'"
            :description="healthStatus.message"
          />
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
const healthStatus = ref<{ok: boolean, message: string} | null>(null)

const testBackend = async () => {
  try {
    const config = useRuntimeConfig()
    const response = await $fetch(`${config.public.apiBase}/api/health`)
    healthStatus.value = {
      ok: true,
      message: 'Successfully connected to backend API'
    }
  } catch (error) {
    healthStatus.value = {
      ok: false,
      message: `Failed to connect: ${error}`
    }
  }
}
</script>
```

#### 3.4 Create Types (`types/api.ts`)

```typescript
// API Response Types
export interface HealthResponse {
  status: string
  version: string
  timestamp: string
}

export interface ApiError {
  detail: string
  status_code: number
}
```

### Phase 4: Docker Integration

#### 4.1 Production Dockerfile (`frontend/Dockerfile`)

```dockerfile
# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Copy built application
COPY --from=build /app/.output ./.output

# Expose port
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production
ENV NUXT_HOST=0.0.0.0
ENV NUXT_PORT=3000

# Start application
CMD ["node", ".output/server/index.mjs"]
```

#### 4.2 Development Dockerfile (`frontend/Dockerfile.dev`)

```dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source
COPY . .

EXPOSE 3000

# Development server with hot reload
CMD ["npm", "run", "dev"]
```

#### 4.3 Update Docker Compose

Update `docker-compose.yml` to replace Streamlit with Nuxt:

```yaml
services:
  # ... other services (postgres, qdrant, backend) ...

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NUXT_PUBLIC_API_BASE=http://backend:8000
      - NUXT_PUBLIC_ENVIRONMENT=production
    depends_on:
      - backend
    networks:
      - org-archivist-network
    volumes:
      # For development hot reload
      - ./frontend:/app
      - /app/node_modules
    restart: unless-stopped

networks:
  org-archivist-network:
    driver: bridge
```

#### 4.4 Docker Ignore (`frontend/.dockerignore`)

```
node_modules
.nuxt
.output
.env
.env.local
dist
*.log
.DS_Store
```

### Phase 5: Backend Integration

#### 5.1 Update Backend CORS Settings

Add to `backend/.env`:

```env
CORS_ORIGINS=http://localhost:3000,http://frontend:3000,http://localhost:8000
```

#### 5.2 Create API Client Composable (`composables/useApi.ts`)

```typescript
export const useApi = () => {
  const config = useRuntimeConfig()

  const apiFetch = $fetch.create({
    baseURL: config.public.apiBase,
    headers: {
      'Content-Type': 'application/json'
    },
    onResponseError({ response }) {
      console.error('API Error:', response.status, response.statusText)
    }
  })

  return {
    apiFetch
  }
}
```

## Development Workflow

### Local Development

#### Start Development Server
```bash
cd frontend
npm run dev
```

Access at: `http://localhost:3000`

#### Development with Backend
```bash
# Terminal 1: Start backend
cd backend
docker-compose up postgres qdrant backend

# Terminal 2: Start frontend
cd frontend
npm run dev
```

### Docker Development

#### Start All Services
```bash
docker-compose up
```

#### Rebuild Frontend
```bash
docker-compose up --build frontend
```

#### View Logs
```bash
docker-compose logs -f frontend
```

### Production Build

#### Local Build Test
```bash
cd frontend
npm run build
npm run preview
```

#### Docker Production Build
```bash
docker-compose -f docker-compose.yml up --build
```

## Testing

### 1. Verify Nuxt UI Components
Visit `http://localhost:3000` and verify:
- UI components render correctly
- Tailwind CSS styles apply
- Dark mode toggle works (if implemented)

### 2. Verify Nuxt Icons
Check that icons display:
```vue
<UIcon name="i-heroicons-check-circle" />
<UIcon name="i-heroicons-user" />
```

### 3. Test Backend Connectivity
Click "Test Nuxt UI" button on home page to verify:
- API call succeeds
- CORS configured correctly
- Health check returns data

### 4. Test Hot Module Replacement
1. Make a change to `pages/index.vue`
2. Save file
3. Verify browser updates without full reload

## Troubleshooting

### Port 3000 Already in Use
```bash
# Find process using port 3000
lsof -i :3000

# Kill the process
kill -9 <PID>

# Or change port in nuxt.config.ts
devServer: {
  port: 3001
}
```

### CORS Errors
Verify backend `.env` includes:
```env
CORS_ORIGINS=http://localhost:3000,http://frontend:3000
```

Restart backend after changes:
```bash
docker-compose restart backend
```

### Module Not Found Errors
```bash
# Clear Nuxt cache
rm -rf .nuxt
rm -rf .output

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

### Docker Container Won't Start
```bash
# Check logs
docker-compose logs frontend

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache frontend
docker-compose up
```

### TypeScript Errors
```bash
# Regenerate types
npx nuxi prepare

# Check TypeScript
npx nuxi typecheck
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `nuxt.config.ts` | Main Nuxt configuration |
| `.env` | Environment variables |
| `app.vue` | Root component |
| `layouts/default.vue` | Default layout wrapper |
| `pages/index.vue` | Home page |
| `composables/useApi.ts` | API client composable |
| `types/api.ts` | TypeScript type definitions |
| `Dockerfile` | Production Docker image |
| `Dockerfile.dev` | Development Docker image |

## Next Steps

After completing this setup:

1. **Authentication Implementation**
   - Install `nuxt-auth-utils` or `@sidebase/nuxt-auth`
   - Create login/register pages
   - Implement JWT token management

2. **UI Development**
   - Design system implementation
   - Component library creation
   - Page layouts

3. **Feature Implementation**
   - Document management
   - AI Assistant chat
   - Writing styles
   - Past outputs

4. **State Management**
   - Install Pinia
   - Create stores for auth, documents, chat

## Resources

- [Nuxt 4 Documentation](https://nuxt.com/)
- [Nuxt UI Documentation](https://ui.nuxt.com/)
- [Nuxt Icon Documentation](https://nuxt.com/modules/icon)
- [Vue 3 Documentation](https://vuejs.org/)
- [TypeScript Documentation](https://www.typescriptlang.org/)

## Support

For issues or questions:
1. Check this documentation
2. Review Nuxt official docs
3. Check project CLAUDE.md for workflow guidelines
4. Consult project architecture in `/context/architecture.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-16
**Status**: Initial Setup Phase
