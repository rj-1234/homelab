-- Personal field vault: typed PII/field candidates extracted from documents.
-- Each row is one value (passport №, SSN, USCIS receipt, card, …) pulled from a
-- document by the `fields` stage (Presidio + custom recognizers). Candidates land
-- unconfirmed; the user confirms once in the Review page, and only confirmed rows
-- surface on the vault shelf. Values are plaintext (masking is a UI reveal-gate,
-- not encryption — see VAULT_PLAN.md security posture); value_masked is the
-- precomputed display form so the list never ships the raw value until revealed.

CREATE TABLE IF NOT EXISTS field (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id   bigint NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    entity_class  text   NOT NULL,          -- US_PASSPORT, US_SSN, SEVIS_ID, …
    label         text   NOT NULL,          -- human label for the shelf
    value         text   NOT NULL,          -- plaintext (masked in UI)
    value_masked  text   NOT NULL,          -- precomputed display mask
    expiry        date,                      -- drives validity ranking / temporal shelf
    valid_from    date,                      -- itineraries (trip window)
    confirmed     boolean NOT NULL DEFAULT false,
    score         real,                      -- extractor confidence 0-1
    source        text   NOT NULL DEFAULT 'presidio',  -- presidio | mrz | user
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, entity_class, value)
);

CREATE INDEX IF NOT EXISTS field_class_idx     ON field (entity_class);
CREATE INDEX IF NOT EXISTS field_confirmed_idx ON field (confirmed);
CREATE INDEX IF NOT EXISTS field_document_idx  ON field (document_id);

-- Push channel: NOTIFY on field changes too, so the vault shelf / Review badge
-- update live over SSE (reuses the trigger function from migration 006).
DROP TRIGGER IF EXISTS field_notify ON field;
CREATE TRIGGER field_notify AFTER INSERT OR UPDATE OR DELETE ON field
  FOR EACH STATEMENT EXECUTE FUNCTION doccat_notify();
