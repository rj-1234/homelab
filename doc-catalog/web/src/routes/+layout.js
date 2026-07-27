// Pure client-side SPA: no SSR (the backend is a JSON API, not a render server),
// prerender the shell so adapter-static can emit index.html.
export const ssr = false;
export const prerender = true;
