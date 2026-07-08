import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' so the build works when served by FastAPI at any root.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    rollupOptions: {
      output: {
        // echarts is ~2/3 of the bundle -- split it (and the react stack) into
        // stable chunks so repeat visits hit the browser cache
        manualChunks: {
          echarts: ['echarts'],
          vendor: ['react', 'react-dom', 'react-router-dom', 'framer-motion'],
        },
      },
    },
  },
  server: {
    port: 5199,
    proxy: {
      '/api': 'http://127.0.0.1:8077',
    },
  },
})
