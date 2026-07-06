import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3001,
    // Allow requests from any host (including public IP via router forwarding)
    allowedHosts: true,
    // HMR settings for proper WebSocket connection through port forwarding
    hmr: {
      // Use the client's host for HMR WebSocket connection
      // This prevents the HMR client from trying to connect to port 3001 directly
      clientPort: 12000,
    },
    // Proxy API requests to backend (avoids needing separate public port for API)
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        followRedirects: true,
      },
      '/docs': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        followRedirects: true,
      },
      '/redoc': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        followRedirects: true,
      },
      '/openapi.json': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        followRedirects: true,
      },
      '/files': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        followRedirects: true,
      },
    },
  },
})
