import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  kit: {
    // Pure SPA: prerender the shell, fall back to index.html for client routing.
    // Served as static assets by the caddy sidecar (no Node runtime in prod).
    adapter: adapter({ fallback: 'index.html', pages: 'build', assets: 'build' })
  }
};

export default config;
