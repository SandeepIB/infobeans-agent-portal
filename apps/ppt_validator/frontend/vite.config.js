import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  // Load .env from the project root (one level up from frontend/)
  const env = loadEnv(mode, '../', '')

  const appPort      = parseInt(env.APP_PORT      || '8080', 10)
  const frontendPort = parseInt(env.FRONTEND_PORT || '5173', 10)

  return {
    plugins: [react()],
    server: {
      port: frontendPort,
      strictPort: true,
      // Bind to all interfaces so the app is reachable over the network
      host: '0.0.0.0',
      proxy: {
        '/api': {
          // Use localhost (not 127.0.0.1) — avoids IPv6/IPv4 resolution issues
          // with uvicorn's --reload reloader parent process
          target: `http://localhost:${appPort}`,
          changeOrigin: true,
          ws: true,
          timeout: 120000,
          proxyTimeout: 120000,
          configure: (proxy) => {
            proxy.on('error', (err) => {
              console.warn('[proxy] Backend not ready yet:', err.message)
            })
          },
        },
      },
    },
    base: '/ppt-validator/app/',
    build: {
      outDir: 'dist',
    },
  }
})
