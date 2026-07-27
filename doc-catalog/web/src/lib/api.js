// Thin JSON client over the FastAPI backend. Same-origin in prod (caddy proxies
// /api -> api pod); vite proxies it in dev.
export async function j(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

const post = (path, body) =>
  j(path, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined
  });

export const listDocuments = (q = '') =>
  j(`/api/documents${q ? `?q=${encodeURIComponent(q)}` : ''}`);

// --- field vault ---
export const listFields = () => j('/api/fields');
export const listReview = () => j('/api/review');
export const docFields = (id) => j(`/api/doc/${id}/fields`);
export const revealField = (id) => post(`/api/field/${id}/reveal`).then((r) => r.value);
export const confirmField = (id, patch) => post(`/api/field/${id}/confirm`, patch || null);
export const deleteField = (id) => post(`/api/field/${id}/delete`);
