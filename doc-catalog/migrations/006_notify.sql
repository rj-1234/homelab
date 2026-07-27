-- Push channel for the decoupled UI: emit a Postgres NOTIFY whenever pipeline
-- state changes, so the API can stream Server-Sent Events to the browser instead
-- of the client polling. The payload is intentionally empty — listeners re-read
-- the current status snapshot on any signal (cheap, single-user corpus), which
-- also collapses a burst of row changes into one refresh. Idempotent.

CREATE OR REPLACE FUNCTION doccat_notify() RETURNS trigger AS $$
BEGIN
  PERFORM pg_notify('doccat_events', '');
  RETURN NULL;   -- AFTER trigger, result ignored
END;
$$ LANGUAGE plpgsql;

-- Statement-level triggers: one signal per statement, not per row (a bulk
-- re-enqueue of 57 jobs fires once, not 57 times).
DROP TRIGGER IF EXISTS job_notify ON job;
CREATE TRIGGER job_notify AFTER INSERT OR UPDATE OR DELETE ON job
  FOR EACH STATEMENT EXECUTE FUNCTION doccat_notify();

DROP TRIGGER IF EXISTS document_notify ON document;
CREATE TRIGGER document_notify AFTER INSERT OR UPDATE OR DELETE ON document
  FOR EACH STATEMENT EXECUTE FUNCTION doccat_notify();

DROP TRIGGER IF EXISTS account_notify ON account;
CREATE TRIGGER account_notify AFTER INSERT OR UPDATE OR DELETE ON account
  FOR EACH STATEMENT EXECUTE FUNCTION doccat_notify();
