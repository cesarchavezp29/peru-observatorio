import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' so the build works when served by FastAPI at any root.
export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    port: 5199,
    proxy: {
      '/api': 'http://127.0.0.1:8077',
    },
  },
})
