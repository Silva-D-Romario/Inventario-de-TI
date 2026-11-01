import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/static/frontend/',
  plugins: [react()],
  build: {
    outDir: '../frontend_dist',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:18000',
        changeOrigin: false,
      },
    },
  },
})
