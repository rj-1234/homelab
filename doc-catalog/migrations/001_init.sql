-- Document Catalog — full schema (schema-aware from day one per the brief).
-- Phase 1 exercises blob, source_event, document, job. The rest exist now so
-- later phases (OCR, extraction, dedupe, embeddings, Gmail) add no migrations
-- to the core shape — they just start writing rows.
--
-- Image: pgvector/pgvector:pg16 (ships the `vector` extension).

CREATE EXTENSION IF NOT EXISTS vector;

-- Immutable raw bytes. The blob is never modified; everything else derives from
-- it and is regenerable. Written to disk BEFORE this row exists (crash-safe:
-- orphan blob is GC-able, a row with no blob is corruption).
CREATE TABLE IF NOT EXISTS blob (
    sha256        text PRIMARY KEY,
    size          bigint NOT NULL,
    mime          text NOT NULL,
    path          text NOT NULL,            -- blobs/ab/cd/<sha256>
    first_seen_at timestamptz NOT NULL DEFAULT now()
);

-- Every arrival of a blob, even a known hash — provenance is append-only.
-- source = 'upload' | 'gmail'; source_ref e.g. 'file:<name>' or
-- 'gmail:<account_id>:<message_id>:<part_id>' (idempotent re-sync).
CREATE TABLE IF NOT EXISTS source_event (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    blob_sha    text NOT NULL REFERENCES blob(sha256),
    source      text NOT NULL,
    source_ref  text NOT NULL,
    sender      text,
    subject     text,
    received_at timestamptz,
    extra       jsonb NOT NULL DEFAULT '{}',
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source, source_ref)             -- idempotent re-ingest
);

-- A real-world document. canonical_document_id NULL => "I am canonical"
-- (default list view filters on IS NULL). One document per new blob at ingest;
-- dedupe later links non-canonicals to a chosen canonical.
CREATE TABLE IF NOT EXISTS document (
    id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    primary_blob_sha     text NOT NULL REFERENCES blob(sha256),
    canonical_document_id bigint REFERENCES document(id),
    quality_tier         int,               -- 1 digital-pdf > 2 scan > 3 photo
    doc_type             text,
    title                text,
    status               text NOT NULL DEFAULT 'ingested',
    created_at           timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS document_canonical_idx ON document(canonical_document_id);
CREATE INDEX IF NOT EXISTS document_blob_idx ON document(primary_blob_sha);

-- Derived, content-addressed, regenerable, byte-deterministic artifacts.
-- (tool, tool_version, params_hash) let "regenerate if tool changed" be a query.
CREATE TABLE IF NOT EXISTS rendition (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    blob_sha     text NOT NULL REFERENCES blob(sha256),
    kind         text NOT NULL,             -- normalized_pdf|page_images|text|thumbnail
    tool         text NOT NULL,
    tool_version text NOT NULL,
    params_hash  text NOT NULL,
    out_sha      text NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (blob_sha, kind, tool, tool_version, params_hash)
);

CREATE TABLE IF NOT EXISTS page (
    document_id bigint NOT NULL REFERENCES document(id),
    page_no     int NOT NULL,
    text        text,
    engine      text,
    confidence  real,
    PRIMARY KEY (document_id, page_no)
);

-- Append-only + versioned. Improving a prompt writes a NEW row; diff across
-- model versions; re-derive identity_keys on re-run.
CREATE TABLE IF NOT EXISTS extraction (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id    bigint NOT NULL REFERENCES document(id),
    schema_version text NOT NULL,
    model          text NOT NULL,
    model_version  text NOT NULL,
    params_hash    text NOT NULL,
    payload        jsonb NOT NULL,
    confidence     real,
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS extraction_doc_idx ON extraction(document_id);

CREATE TABLE IF NOT EXISTS chunk (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id bigint NOT NULL REFERENCES document(id),
    page_no     int,
    text        text NOT NULL,
    embedding   vector(768)
);
CREATE INDEX IF NOT EXISTS chunk_doc_idx ON chunk(document_id);

-- kind: content_hash | text_simhash | phash | identity_key
CREATE TABLE IF NOT EXISTS fingerprint (
    document_id bigint NOT NULL REFERENCES document(id),
    kind        text NOT NULL,
    value       text NOT NULL,
    page_no     int
);
CREATE INDEX IF NOT EXISTS fingerprint_kind_value_idx ON fingerprint(kind, value);

-- Link, never destroy. state=rejected means "these really differ" (stops
-- re-flagging every run).
CREATE TABLE IF NOT EXISTS duplicate_link (
    document_id       bigint NOT NULL REFERENCES document(id),
    other_document_id bigint NOT NULL REFERENCES document(id),
    kind              text NOT NULL,        -- exact | near | logical
    score             real,
    state             text NOT NULL DEFAULT 'suspected', -- suspected|confirmed|rejected
    decided_at        timestamptz,
    PRIMARY KEY (document_id, other_document_id, kind)
);

-- Postgres-as-queue. Claimed via SELECT ... FOR UPDATE SKIP LOCKED.
CREATE TABLE IF NOT EXISTS job (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id bigint NOT NULL REFERENCES document(id),
    stage       text NOT NULL,             -- normalize|ocr|extract|embed
    state       text NOT NULL DEFAULT 'pending', -- pending|running|done|failed
    attempts    int NOT NULL DEFAULT 0,
    locked_at   timestamptz,
    error       text,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS job_claim_idx ON job(stage, state) WHERE state = 'pending';

CREATE TABLE IF NOT EXISTS account (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider          text NOT NULL,
    email             text NOT NULL,
    status            text NOT NULL DEFAULT 'active',
    secret_ref        text NOT NULL,        -- points at k8s Secret / token file
    history_id        text,
    last_full_sync_at timestamptz,
    UNIQUE (provider, email)
);

CREATE TABLE IF NOT EXISTS sender_rule (
    account_id bigint NOT NULL REFERENCES account(id),
    pattern    text NOT NULL,
    action     text NOT NULL,              -- allow | deny | candidate
    created_at timestamptz NOT NULL DEFAULT now()
);
