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
      '/auth': 'http://localhost:8002',
      '/projects': 'http://localhost:8002',
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/fonts': 'http://localhost:8002',
      '/project-files': 'http://localhost:8002',
      '/library': 'http://localhost:8002',
      '/reports': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/datasources': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/templates': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/export': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/scenarios': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/knowledge': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/report-templates': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/smart-fill': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/data-sources': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
