// Thin JSON client over the FastAPI backend. Same-origin in prod (caddy proxies
// /api -> api pod); vite proxies it in dev.

export interface Doc {
  id: string;
  title: string | null;
  status: string;
  doc_type: string | null;
  mime: string | null;
  size: number | null;
  created_at: string | null;
  sha: string | null;
  pages: number | null;
  tags: string[];
  snippet?: string | null;
}

export interface Provenance {
  source: string;
  sender?: string;
  subject?: string;
  received_at?: string;
  created_at?: string;
}

export interface PageText {
  page_no?: number;
  engine?: string;
  text?: string;
}

export interface Job {
  stage: string;
  state: "pending" | "running" | "done" | "failed";
  n?: number;
}

export interface DocDetail {
  doc: Doc;
  provenance: Provenance[];
  pages: PageText[];
  jobs: Job[];
  fields?: { confirmed: number; review: number };
}

export interface Tag {
  name: string;
  n: number;
}

export interface TaxonomyCategory {
  category: string;
  subtags: string[];
}

export interface StatusOption {
  key: string;
  label: string;
}

export interface Taxonomy {
  tags: TaxonomyCategory[];
  statuses: StatusOption[];
}

export interface SenderRule {
  account_id: string;
  email?: string;
  pattern: string;
  action: "allow" | "deny";
}

export interface StatusAccount {
  id: string;
  email: string;
  synced: boolean;
  attachments: number;
}

export interface StatusSource {
  source: string;
  n: number;
}

export interface StatusFailure {
  id: string;
  stage: string;
  title: string;
  attempts: number;
}

export interface StatusSnapshot {
  documents: number;
  fields: { confirmed: number; review: number };
  sources: StatusSource[];
  accounts: StatusAccount[];
  jobs: Job[];
  failures: StatusFailure[];
}

export interface VaultField {
  id: string;
  document_id: string;
  entity_class: string;
  label: string;
  value_masked: string;
  expiry?: string | null;
  valid_from?: string | null;
  score?: number;
  doc_count?: number;
}

export interface DocField {
  id: string;
  entity_class: string;
  label: string;
  value_masked: string;
  expiry?: string | null;
  confirmed: boolean;
  score?: number;
  source?: string;
  doc_count?: number;
  document_id?: string;
}

export interface ReviewCandidate {
  id: string;
  document_id: string;
  entity_class: string;
  label: string;
  value_masked: string;
  score?: number;
  title: string;
}

export async function j<T>(path: string, opts?: RequestInit): Promise<T> {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

const post = <T>(path: string, body?: unknown): Promise<T> =>
  j<T>(path, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

export interface ListDocumentsParams {
  q?: string;
  status?: string;
  tag?: string;
  field?: string;
}

export const listDocuments = ({ q = "", status = "", tag = "", field = "" }: ListDocumentsParams = {}) => {
  const p = new URLSearchParams();
  if (q) p.set("q", q);
  if (status) p.set("status", status);
  if (tag) p.set("tag", tag);
  if (field) p.set("field", field);
  const qs = p.toString();
  return j<Doc[]>(`/api/documents${qs ? `?${qs}` : ""}`);
};

export const getDoc = (id: string) => j<DocDetail>(`/api/doc/${id}`);
export const listTags = () => j<Tag[]>("/api/tags");

export const updateDoc = (id: string, patch: Partial<Pick<Doc, "title" | "doc_type" | "status" | "tags">>) =>
  post(`/api/doc/${id}`, patch);
export const reprocessDoc = (id: string, stage: string) => post(`/api/doc/${id}/reprocess`, { stage });
export const deleteDoc = (id: string) => post(`/api/doc/${id}/delete`);
export const getTaxonomy = () => j<Taxonomy>("/api/taxonomy");
export const listSenderRules = () => j<SenderRule[]>("/api/sender-rules");
export const addSenderRule = (rule: SenderRule) => post("/api/sender-rule", rule);
export const delSenderRule = (rule: Pick<SenderRule, "account_id" | "pattern" | "action">) =>
  post("/api/sender-rule/delete", rule);

export const uploadFiles = (fileList: FileList | File[]) => {
  const fd = new FormData();
  for (const f of fileList) fd.append("files", f);
  return j<{ queued: unknown[] }>("/api/upload", { method: "POST", body: fd });
};

// --- field vault ---
export const listFields = () => j<VaultField[]>("/api/fields");
export const listReview = () => j<ReviewCandidate[]>("/api/review");
export const docFields = (id: string) => j<DocField[]>(`/api/doc/${id}/fields`);
export const revealField = (id: string) => post<{ value: string }>(`/api/field/${id}/reveal`).then((r) => r.value);
export const confirmField = (id: string, patch?: { value?: string } | null) =>
  post(`/api/field/${id}/confirm`, patch ?? null);
export const deleteField = (id: string) => post(`/api/field/${id}/delete`);
