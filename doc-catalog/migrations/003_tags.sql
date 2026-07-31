-- Phase 3b (management UI): user-applied tags. Kept separate from doc_type
-- (which extraction sets automatically in Phase 6) — tags are the human's own
-- filing labels, many-to-many.

CREATE TABLE IF NOT EXISTS tag (
    id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS document_tag (
    document_id bigint NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    tag_id      bigint NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
    PRIMARY KEY (document_id, tag_id)
);
CREATE INDEX IF NOT EXISTS document_tag_tag_idx ON document_tag(tag_id);
