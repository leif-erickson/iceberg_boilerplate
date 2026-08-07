import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev and preview servers listen on 3000 to match the Docker Compose port mapping.
export default defineConfig({
  plugins: [react()],
  server: { host: true, port: 3000 },
  preview: { host: true, port: 3000 },
});
