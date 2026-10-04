import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Allows any localtunnel or cloudflared host to connect
    allowedHosts: true,
  },
})
