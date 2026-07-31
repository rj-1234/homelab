// A dynamic id route can't be enumerated at prerender time (unlike the static
// routes, which the root layout prerenders as the SPA shell). Skip prerendering
// here and let adapter-static's `fallback: 'index.html'` serve it client-side.
export const prerender = false;
