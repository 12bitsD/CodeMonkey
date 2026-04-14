import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

export default defineConfig(({ mode }) => {
  const rootDir = path.dirname(fileURLToPath(import.meta.url))
  const env = loadEnv(mode, rootDir, '')
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      port: 3000,
      open: true,
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
          // Disable response buffering so SSE chunks are forwarded immediately
          configure: (proxy) => {
            proxy.on('proxyRes', (proxyRes, req) => {
              if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
                proxyRes.headers['cache-control'] = 'no-cache';
                proxyRes.headers['x-accel-buffering'] = 'no';
              }
            });
          }
        }
      }
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test-setup.js'],
      include: ['src/**/*.test.{js,ts,jsx,tsx}']
    }
  }
})
