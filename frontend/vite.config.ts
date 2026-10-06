import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy) => {
          // The local API allows the standard Vite origin on port 5173.
          // Forwarding this origin lets the dev server work on alternate local ports too.
          proxy.on('proxyReq', (proxyReq) => proxyReq.setHeader('origin', 'http://127.0.0.1:5173'))
        },
      },
    },
  },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true },
})
