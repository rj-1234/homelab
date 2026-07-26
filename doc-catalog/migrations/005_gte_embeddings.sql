-- Switch the embedding model from Qwen3-Embedding-0.6B (1024-dim) to a 768-dim
-- base model (bge-base-en-v1.5). The pipeline caps input at 512 tokens, which
-- throws away Qwen's long-context/size advantage; a 768-dim base model gives
-- near-identical tagging/search at ~4-5x less memory and CPU. The dim change
-- forces a re-embed, so drop the column + ANN index and recreate at 768. Every
-- document then re-runs the 'embed' stage (enqueued out-of-band) to repopulate.
-- Idempotent so a re-run is harmless.

DROP INDEX IF EXISTS chunk_embedding_idx;

ALTER TABLE chunk DROP COLUMN IF EXISTS embedding;
ALTER TABLE chunk ADD COLUMN IF NOT EXISTS embedding vector(768);

-- Cosine ANN index for semantic search (small corpus; HNSW is cheap insurance).
CREATE INDEX IF NOT EXISTS chunk_embedding_idx
    ON chunk USING hnsw (embedding vector_cosine_ops);
