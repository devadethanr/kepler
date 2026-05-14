import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vite';

export default defineConfig(() => {
  const fastApiUrl = process.env.FASTAPI_URL || 'http://app:8000';
  const fastApiKey = process.env.FASTAPI_API_KEY || process.env.API_KEY || '';

  return {
    plugins: [react(), tailwindcss()],

    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },

    server: {
      host: true,
      allowedHosts: ['.ngrok-free.dev', '.ngrok-free.app'],
      hmr: process.env.DISABLE_HMR !== 'true',

      proxy: {
        '/api': {
          target: fastApiUrl,
          changeOrigin: true,
          rewrite: (proxyPath) => proxyPath.replace(/^\/api/, ''),
          configure: (proxy) => {
            proxy.on('proxyReq', (proxyReq) => {
              if (fastApiKey) {
                proxyReq.setHeader('X-API-Key', fastApiKey);
              }
            });
          },
        },
      },
    },
  };
});
