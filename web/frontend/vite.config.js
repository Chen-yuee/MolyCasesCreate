import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    hmr: {
      host: '192.168.106.20',
      clientPort: 5124
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000', // 本地开发使用 localhost，Docker 环境使用 http://backend:8000
        changeOrigin: true
      }
    }
  }
})
