import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'demo' ? '/AuditHive/' : '/',
  server: {
    port: 5173,
  },
}));
