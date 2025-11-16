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
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8001',
      environment: process.env.NUXT_PUBLIC_ENVIRONMENT || 'development'
    }
  },

  // Proxy API requests to backend (for CORS)
  nitro: {
    devProxy: {
      '/api': {
        target: (process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8001') + '/api',
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
