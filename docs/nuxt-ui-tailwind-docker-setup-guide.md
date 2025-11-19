# Nuxt 4 + Nuxt UI v4 + Tailwind v4 Docker Setup Guide

**Last Updated:** November 19, 2025
**Author:** Based on org-archivist implementation
**Tech Stack:** Nuxt 4.2+, Nuxt UI v4.2+, Tailwind CSS v4.1+

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Project Setup](#project-setup)
4. [Critical Configuration Files](#critical-configuration-files)
5. [Docker Configuration](#docker-configuration)
6. [Common Pitfalls & Solutions](#common-pitfalls--solutions)
7. [Verification Steps](#verification-steps)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers the proper setup of a Nuxt 4 application with Nuxt UI v4 and Tailwind CSS v4 running in Docker production containers.

### Key Differences from Nuxt UI v3

- **Tailwind v4** uses `@import` syntax instead of `@tailwind` directives
- **CSS is embedded** in JavaScript modules (not separate .css files)
- **Requires PostCSS configuration** for proper build processing
- **Docker volume mounts** must be handled differently for dev vs production

---

## Prerequisites

### Required Versions

```json
{
  "nuxt": "^4.2.1",
  "@nuxt/ui": "^4.2.0",
  "tailwindcss": "^4.1.0" // (installed via @nuxt/ui)
}
```

**Note:** Nuxt 4 is now officially released. The above versions are the current stable releases.

### System Requirements

- Node.js 18+ or 20+
- Docker & Docker Compose
- npm or pnpm

---

## Project Setup

### Step 1: Initialize Nuxt Project

```bash
npx nuxi@latest init my-project
cd my-project
```

### Step 2: Install Dependencies

```bash
npm install @nuxt/ui @nuxt/icon
```

**Note:** Nuxt UI v4 automatically installs Tailwind CSS v4 as a dependency. Do NOT manually install tailwindcss.

### Step 3: Project Structure

Create the following directory structure:

```
my-project/
├── assets/
│   └── css/
│       └── main.css          # Tailwind imports
├── components/
├── layouts/
│   └── default.vue
├── pages/
├── app.vue                    # Root component
├── app.config.ts              # Nuxt UI configuration
├── nuxt.config.ts             # Nuxt configuration
├── postcss.config.js          # ⚠️ CRITICAL - PostCSS config
├── tailwind.config.ts         # Tailwind config (optional)
├── Dockerfile
└── docker-compose.yml
```

---

## Critical Configuration Files

### 1. `postcss.config.js` ⚠️ CRITICAL

**This file is REQUIRED for Tailwind v4 to work properly.**

```javascript
export default {
  plugins: {
    '@tailwindcss/postcss': {},
  },
}
```

**Why it's needed:**
- Tailwind v4 uses a PostCSS plugin architecture
- Without this, CSS will not be generated during production builds
- Nuxt/Vite will not process Tailwind directives

**Common mistake:** Forgetting to create this file results in unstyled pages in production.

---

### 2. `assets/css/main.css`

```css
@import "tailwindcss";
@import "@nuxt/ui";
```

**Important Notes:**
- Use `@import` syntax (Tailwind v4), NOT `@tailwind` directives (Tailwind v3)
- Import order matters: tailwindcss first, then @nuxt/ui
- This file must be referenced in nuxt.config.ts

---

### 3. `nuxt.config.ts`

```typescript
// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  // ⚠️ Enable Nuxt 4 compatibility features
  compatibilityDate: '2024-04-03',
  devtools: { enabled: true },

  modules: [
    '@nuxt/ui',
    '@nuxt/icon'
  ],

  // ⚠️ CRITICAL: Reference the CSS file
  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8000',
      environment: process.env.NUXT_PUBLIC_ENVIRONMENT || 'development'
    }
  },

  devServer: {
    port: 3000,
    host: '0.0.0.0'
  }
})
```

**Key Points:**
- `css: ['~/assets/css/main.css']` is required
- Do NOT add Vite/PostCSS configuration in nuxt.config.ts (postcss.config.js handles it)
- @nuxt/ui module must be before @nuxt/icon

---

### 4. `app.config.ts`

```typescript
export default defineAppConfig({
  ui: {
    // Nuxt UI global configuration
    // Customize colors, spacing, etc.
    primary: 'blue',
    gray: 'neutral'
  }
})
```

---

### 5. `tailwind.config.ts` (Optional)

```typescript
import type { Config } from 'tailwindcss'

export default {
  // Nuxt UI v3 handles most configuration
  // Add custom extensions here if needed
  theme: {
    extend: {
      // Custom theme extensions
    }
  }
} satisfies Config
```

**Note:** With Nuxt UI v4 + Tailwind v4, this file is mostly optional. Nuxt UI handles the configuration.

---

### 6. `app.vue`

```vue
<template>
  <UApp>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>

<script setup lang="ts">
// App-level logic
</script>
```

**Critical:** The `<UApp>` wrapper is required for Nuxt UI to function properly.

---

## Docker Configuration

### Development vs Production Configurations

**Key Principle:** Development and production Docker configurations must be separate.

### Production Dockerfile

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /build

# Copy package files
COPY package*.json ./

# Install ALL dependencies (including devDependencies for build)
RUN npm ci

# Copy source code
COPY . .

# Build the application
# This generates .output directory with production assets
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Install curl for healthchecks
RUN apk add --no-cache curl

# Copy package files
COPY package*.json ./

# Install ONLY production dependencies
RUN npm ci --only=production && npm cache clean --force

# ⚠️ CRITICAL: Copy built output from builder stage
COPY --from=builder /build/.output ./.output
COPY --from=builder /build/nuxt.config.ts ./nuxt.config.ts

# Create non-root user
RUN addgroup -g 1001 appuser && \
    adduser -D -u 1001 -G appuser appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 3000

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=3000
ENV NODE_ENV=production

# Start the application
CMD ["node", ".output/server/index.mjs"]
```

---

### Production docker-compose.yml

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: my-app-frontend
    ports:
      - "3000:3000"
    environment:
      NUXT_PUBLIC_API_BASE: ${BACKEND_URL:-http://backend:8000}
      NUXT_PUBLIC_ENVIRONMENT: ${ENVIRONMENT:-production}
      NODE_ENV: production
      HOST: 0.0.0.0
      PORT: 3000

    # ⚠️ CRITICAL: NO VOLUME MOUNTS IN PRODUCTION
    # Commenting out these volumes is essential for production
    # volumes:
    #   - ./frontend:/app
    #   - /app/node_modules
    #   - /app/.nuxt
    #   - /app/.output

    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:3000/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

    restart: unless-stopped
```

**Why no volumes in production:**
- Volume mounts override the built `.output` directory
- This causes the container to serve unbundled source code instead of production assets
- Results in missing CSS and broken application

---

### Development docker-compose.dev.yml

For development with hot reload, use a separate compose file:

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev  # Different Dockerfile for dev
    container_name: my-app-frontend-dev
    ports:
      - "3000:3000"
    environment:
      NODE_ENV: development
      HOST: 0.0.0.0
      PORT: 3000

    # ✅ Volumes are OK for development
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.nuxt

    command: npm run dev
```

**Usage:**
```bash
# Development
docker-compose -f docker-compose.dev.yml up

# Production
docker-compose up
```

---

## Common Pitfalls & Solutions

### Issue 1: Unstyled Pages in Production

**Symptoms:**
- Pages render but have no styling
- CSS classes are present in HTML but not applied
- Works in development, fails in Docker production

**Root Cause:**
- Missing `postcss.config.js` file
- Docker volume mounts overriding production build

**Solution:**
```bash
# 1. Create postcss.config.js
cat > postcss.config.js << 'EOF'
export default {
  plugins: {
    '@tailwindcss/postcss': {},
  },
}
EOF

# 2. Comment out volume mounts in docker-compose.yml
# 3. Rebuild Docker image
docker-compose build frontend
docker-compose up -d frontend
```

---

### Issue 2: CSS Not Generated During Build

**Symptoms:**
- Build completes but entry-styles file is nearly empty
- No CSS files in `.output/public/_nuxt/`
- `entry-styles.*.mjs` is < 10KB

**Root Cause:**
- Missing PostCSS configuration
- Incorrect CSS import syntax in main.css

**Solution:**
```bash
# 1. Verify postcss.config.js exists and is correct
# 2. Check assets/css/main.css uses @import (not @tailwind)
# 3. Clear build cache and rebuild
rm -rf .nuxt .output
npm run build

# 4. Verify entry-styles.*.mjs is > 100KB
ls -lh .output/server/chunks/build/entry-styles.*.mjs
```

**Expected:** entry-styles file should be ~130-150KB with full Tailwind CSS

---

### Issue 3: "Cannot find module @tailwindcss/postcss"

**Symptoms:**
- Build fails with module not found error
- Error mentions @tailwindcss/postcss

**Root Cause:**
- Dependencies not fully installed
- Using Tailwind v3 instead of v4

**Solution:**
```bash
# 1. Remove node_modules and package-lock.json
rm -rf node_modules package-lock.json

# 2. Ensure @nuxt/ui v3+ is in package.json
npm install @nuxt/ui@latest

# 3. Clean install
npm ci
```

---

### Issue 4: Styles Embedded in JS Instead of Separate CSS Files

**This is NOT an issue!**

**Expected Behavior:**
- Nuxt UI v4 + Tailwind v4 embeds CSS in `<style>` tags in HTML
- CSS is also in JavaScript modules (entry-styles.*.mjs)
- You will NOT see large separate .css files in production

**Verification:**
```bash
# Check HTML output
curl http://localhost:3000 | grep '<style'

# Should show inline <style> tags with Tailwind CSS
```

---

## Verification Steps

### 1. Local Build Verification

```bash
# Clean build
rm -rf .nuxt .output
npm run build

# Check entry-styles size (should be 100KB+)
ls -lh .output/server/chunks/build/entry-styles.*.mjs

# Preview build
npm run preview
# Open http://localhost:3000
```

**Expected:**
- Build completes without errors
- entry-styles.*.mjs is 130KB+
- Pages render with full styling

---

### 2. Docker Build Verification

```bash
# Rebuild image
docker-compose build frontend

# Start container
docker-compose up -d frontend

# Check logs
docker logs my-app-frontend

# Test endpoint
curl http://localhost:3000
```

**Verify CSS in HTML:**
```bash
curl -s http://localhost:3000 | grep '<style' | head -3
```

**Expected output:**
```html
<style id="nuxt-ui-colors">@layer base {
<style>@layer properties{@supports...
```

---

### 3. Visual Verification

Open browser to http://localhost:3000 and verify:

- [ ] Nuxt UI components render with proper styling
- [ ] Buttons have correct colors and hover states
- [ ] Forms have proper borders and focus states
- [ ] Typography uses correct fonts and sizes
- [ ] Layout spacing is consistent
- [ ] Dark mode toggle works (if implemented)

---

## Troubleshooting

### Debug: Check CSS Generation

```bash
# 1. Check if postcss.config.js exists
ls -la postcss.config.js

# 2. Verify Tailwind import syntax
cat assets/css/main.css

# 3. Check Nuxt config references CSS
grep "css:" nuxt.config.ts

# 4. Build and check output
npm run build
head -50 .output/server/chunks/build/entry-styles.*.mjs
```

---

### Debug: Docker Container Issues

```bash
# 1. Check if volume mounts are commented out
grep -A 5 "volumes:" docker-compose.yml

# 2. Verify container is using built output
docker exec -it my-app-frontend ls -la .output

# 3. Check environment variables
docker exec -it my-app-frontend env | grep NODE_ENV

# 4. Check served HTML
docker exec -it my-app-frontend curl -s http://localhost:3000 | grep style
```

---

### Debug: Build Output Analysis

```bash
# Check what's in the .output directory
tree .output -L 3

# Verify CSS in entry-styles
grep -o "\.bg-gray-50" .output/server/chunks/build/entry-styles.*.mjs

# Check public assets
ls -lh .output/public/_nuxt/
```

---

## Quick Reference Checklist

Use this checklist when setting up a new project:

### Setup Phase
- [ ] Create `postcss.config.js` with @tailwindcss/postcss plugin
- [ ] Create `assets/css/main.css` with @import directives (not @tailwind)
- [ ] Add css reference to `nuxt.config.ts`
- [ ] Wrap app with `<UApp>` component in app.vue
- [ ] Install @nuxt/ui and @nuxt/icon modules

### Configuration Phase
- [ ] Verify nuxt.config.ts has @nuxt/ui in modules array
- [ ] Verify app.config.ts exists with ui configuration
- [ ] Check package.json has @nuxt/ui v4+ and nuxt 4.2+

### Docker Phase
- [ ] Create production Dockerfile with multi-stage build
- [ ] Ensure docker-compose.yml has NO volume mounts for production
- [ ] Add healthcheck to docker-compose.yml
- [ ] Set NODE_ENV=production in container

### Testing Phase
- [ ] Run local build: `npm run build`
- [ ] Verify entry-styles.*.mjs is > 100KB
- [ ] Build Docker image: `docker-compose build`
- [ ] Start container: `docker-compose up -d`
- [ ] Test styling: `curl http://localhost:3000 | grep style`
- [ ] Visual check in browser

---

## Additional Resources

### Official Documentation
- [Nuxt 4 Documentation](https://nuxt.com)
- [Nuxt UI v4 Documentation](https://ui.nuxt.com)
- [Tailwind CSS v4 Documentation](https://tailwindcss.com/docs)

### Example Configuration Files

Full working examples are available in this repository:
- `frontend/postcss.config.js`
- `frontend/nuxt.config.ts`
- `frontend/app.config.ts`
- `frontend/assets/css/main.css`
- `docker-compose.yml`

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-19 | 1.1 | Updated to Nuxt UI v4 (from v3) |
| 2025-11-18 | 1.0 | Initial guide based on org-archivist implementation |

---

## Summary

**The Three Critical Requirements:**

1. **PostCSS Config:** Create `postcss.config.js` with @tailwindcss/postcss plugin
2. **CSS Imports:** Use `@import "tailwindcss"` syntax in main.css (not @tailwind)
3. **Docker Volumes:** Remove volume mounts from production docker-compose.yml

**If you follow these three rules, your Nuxt UI v4 + Tailwind v4 app will work correctly in Docker production builds.**

---

## Support

If you encounter issues not covered in this guide:

1. Verify all three critical requirements above
2. Check the troubleshooting section
3. Review the debug commands
4. Compare your config files with the examples in this repository

For project-specific issues, refer to the `docs/` directory for additional documentation.
