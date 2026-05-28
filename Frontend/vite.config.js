import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // In production build (Vercel), no proxy needed — axios uses VITE_API_BASE_URL directly.
  // In local dev, proxy /api/v1 → Django at localhost:8000.
  const backendTarget = env.VITE_API_BASE_URL
    ? new URL(env.VITE_API_BASE_URL).origin   // e.g. http://localhost:8000
    : 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target:      backendTarget,
          changeOrigin: true,
          secure:       false,
        },
      },
    },
  }
})
