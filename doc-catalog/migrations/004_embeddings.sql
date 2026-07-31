-- Phase 7 (semantic tagging + search): switch the reserved embedding column to
-- 1024 dims for Qwen3-Embedding-0.6B. The column was never populated, so this
-- is a widen, not a data migration. A document's doc-level vector is stored as
-- a chunk row with page_no IS NULL; per-page chunks keep their page_no.
--
-- Classification output (tags + per-category scores + model/version) is recorded
-- in the existing append-only `extraction` table — no new table needed.

ALTER TABLE chunk DROP COLUMN IF EXISTS embedding;
ALTER TABLE chunk ADD COLUMN embedding vector(1024);

-- Cosine ANN index for semantic search (small corpus; HNSW is cheap insurance).
CREATE INDEX IF NOT EXISTS chunk_embedding_idx
    ON chunk USING hnsw (embedding vector_cosine_ops);

-- Distinguish auto-applied tags from user-confirmed ones so the embed stage can
-- refresh its own tags without touching manual edits, and the feedback loop can
-- train centroids from confirmed ('user') tags only.
ALTER TABLE document_tag ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'user';
