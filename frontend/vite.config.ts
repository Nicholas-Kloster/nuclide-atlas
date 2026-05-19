import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Backend URL override: ATLAS_API_BASE=http://atlas-backend:8000
const backend = process.env.ATLAS_API_BASE || 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': { target: backend, changeOrigin: true },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': { target: backend, changeOrigin: true },
    },
  },
});
