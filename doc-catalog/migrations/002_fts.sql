-- Phase 3: lexical full-text search. A generated tsvector on page text keeps the
-- index in lock-step with the text automatically (no trigger, no app code), and
-- backfills existing rows on creation. GIN index for @@ queries.
-- pgvector semantic search is added later (Phase 7) alongside this, not instead.

ALTER TABLE page
    ADD COLUMN IF NOT EXISTS tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(text, ''))) STORED;

CREATE INDEX IF NOT EXISTS page_tsv_idx ON page USING GIN (tsv);
