// Thin JSON client over the FastAPI backend. Same-origin in prod (caddy proxies
// /api -> api pod); vite proxies it in dev.
export async function j(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

export const listDocuments = (q = '') =>
  j(`/api/documents${q ? `?q=${encodeURIComponent(q)}` : ''}`);
