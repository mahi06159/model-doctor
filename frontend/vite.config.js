import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Allows connections from outside the container
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://backend:8000', // Docker Compose backend service name
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
