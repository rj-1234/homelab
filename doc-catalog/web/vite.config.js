import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Dev: proxy /api to the API pod. Reach it with
//   kubectl -n docs port-forward svc/api 8000:8000
// then `npm run dev`. Override the target with VITE_API_TARGET if needed.
const API = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      '/api': {
        target: API,
        changeOrigin: true,
        // SSE (/api/events) is a long-lived stream — don't let the proxy buffer.
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              proxyRes.headers['x-accel-buffering'] = 'no';
            }
          });
        }
      }
    }
  }
});
