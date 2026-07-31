DROP TABLE IF EXISTS quote;
DROP TABLE IF EXISTS gift;

CREATE TABLE gifts (
    id          text PRIMARY KEY,
    stems       jsonb NOT NULL,
    message     text NOT NULL,
    sender      text NOT NULL,
    lifetime_ms bigint NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    opened_at   timestamptz,
    expires_at  timestamptz
);
