import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/analyze': 'http://localhost:8000',
      '/reports': 'http://localhost:8000',
      '/history': 'http://localhost:8000'
    }
  }
})
