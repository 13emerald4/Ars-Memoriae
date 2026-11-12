import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dev server proxies everything the backend owns, so the app talks to its
// own origin in development exactly as it does in production (where FastAPI
// serves the build). That keeps it working from a phone on the LAN too.
const backend = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: backend,
        changeOrigin: true,
        // The sync socket lives under /api/sync/ws.
        ws: true,
        // Adds X-Forwarded-For so the backend can tell a browser on this
        // machine from one on the network (code execution is local-only).
        xfwd: true,
      },
      // Uploaded images (occlusion cards) are served by the backend too.
      '/media': {
        target: backend,
        changeOrigin: true,
        xfwd: true,
      },
    },
  },
})
