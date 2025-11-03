import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',   // tüm arayüzlerden erişim
    port: 5173,        // sabit port
    strictPort: true,
    hmr: false,        // HMR (WebSocket) kapalı -> connection reset hatası biter
    watch: {
      usePolling: true // dosya değişikliklerini algılar
    }
  }
})
