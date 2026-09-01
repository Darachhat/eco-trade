import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/bybit-api': {
        target: 'https://api.bybit.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/bybit-api/, ''),
      },
      '/api': {
        target: 'http://103.6.168.32:8000',
        changeOrigin: true,
      },
      '/market': {
        target: 'http://103.6.168.32:8000',
        changeOrigin: true,
      },
      '/signals': {
        target: 'http://103.6.168.32:8000',
        changeOrigin: true,
      },
      '/performance': {
        target: 'http://103.6.168.32:8000',
        changeOrigin: true,
      },
      '/risk': {
        target: 'http://103.6.168.32:8000',
        changeOrigin: true,
      },
      '/journal': {
        target: 'http://103.6.168.32:8000',
        changeOrigin: true,
      },
      '/backtest': {
        target: 'http://103.6.168.32:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://103.6.168.32:8000',
        ws: true,
      },
    },
  },
})
