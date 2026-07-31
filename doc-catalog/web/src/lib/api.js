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

export const listDocuments = ({ q = '', status = '', tag = '', field = '' } = {}) => {
  const p = new URLSearchParams();
  if (q) p.set('q', q);
  if (status) p.set('status', status);
  if (tag) p.set('tag', tag);
  if (field) p.set('field', field);
  const qs = p.toString();
  return j(`/api/documents${qs ? `?${qs}` : ''}`);
};

export const getDoc = (id) => j(`/api/doc/${id}`);
export const listTags = () => j('/api/tags');

export const updateDoc = (id, patch) => post(`/api/doc/${id}`, patch);
export const reprocessDoc = (id, stage) => post(`/api/doc/${id}/reprocess`, { stage });
export const deleteDoc = (id) => post(`/api/doc/${id}/delete`);
export const getTaxonomy = () => j('/api/taxonomy');
export const listSenderRules = () => j('/api/sender-rules');
export const addSenderRule = (rule) => post('/api/sender-rule', rule);
export const delSenderRule = (rule) => post('/api/sender-rule/delete', rule);
export const uploadFiles = (fileList) => {
  const fd = new FormData();
  for (const f of fileList) fd.append('files', f);
  return j('/api/upload', { method: 'POST', body: fd });
};

// --- field vault ---
export const listFields = () => j('/api/fields');
export const listReview = () => j('/api/review');
export const docFields = (id) => j(`/api/doc/${id}/fields`);
export const revealField = (id) => post(`/api/field/${id}/reveal`).then((r) => r.value);
export const confirmField = (id, patch) => post(`/api/field/${id}/confirm`, patch || null);
export const deleteField = (id) => post(`/api/field/${id}/delete`);
