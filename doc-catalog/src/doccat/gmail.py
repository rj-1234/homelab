"""Gmail ingestion: pull attachments from authorized accounts into the pipeline.

Each account is a google "authorized_user" token JSON (client id/secret +
refresh token, gmail.readonly scope) mounted read-only as token-<label>.json.
Per poll we mint a fresh access token from the refresh token (nothing is
written back to the token file), sync incrementally via the History API with a
bounded first backfill, and hand each attachment to ingest.ingest_bytes with
gmail provenance.

Idempotent by construction: source_event UNIQUE(source, source_ref) means a
re-synced attachment is recorded once and never re-documented, and the blob
store dedupes identical bytes across messages/accounts.

google-api-python-client / google-auth are imported lazily so the package still
imports without them (they live only in the worker pod).
"""
import base64
from datetime import datetime, timezone

from . import config, db, ingest, log


def _service(token_path):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(token_path))
    if not creds.valid:
        creds.refresh(Request())               # in-memory only; file stays read-only
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _accounts(cur, tokens):
    """Ensure an account row exists per token file (email discovered from the
    profile on first sight). Returns (account_id, email, history_id, token_path)."""
    out = []
    for tok in tokens:
        secret_ref = str(tok)
        cur.execute(
            "SELECT id, email, history_id FROM account WHERE secret_ref=%s", (secret_ref,)
        )
        row = cur.fetchone()
        if row:
            out.append((row[0], row[1], row[2], tok))
            continue
        email = _service(tok).users().getProfile(userId="me").execute()["emailAddress"]
        cur.execute(
            "INSERT INTO account(provider,email,secret_ref) VALUES('gmail',%s,%s)"
            " ON CONFLICT (provider,email) DO UPDATE SET secret_ref=EXCLUDED.secret_ref"
            " RETURNING id, email, history_id",
            (email, secret_ref),
        )
        r = cur.fetchone()
        out.append((r[0], r[1], r[2], tok))
    return out


def _headers(msg):
    h = {x["name"].lower(): x["value"]
         for x in msg.get("payload", {}).get("headers", [])}
    return h.get("from"), h.get("subject")


def _attachments(payload):
    """Yield attachment parts (have a filename + an attachmentId), depth-first."""
    stack = [payload]
    while stack:
        p = stack.pop()
        stack.extend(p.get("parts", []) or [])
        if p.get("filename") and p.get("body", {}).get("attachmentId"):
            yield p


def _wanted(part):
    """Keep only document-type attachments (skip newsletter images)."""
    mt = (part.get("mimeType") or "").lower()
    fn = (part.get("filename") or "").lower()
    return mt in config.GMAIL_ATTACH_MIME or fn.endswith(config.GMAIL_ATTACH_EXT)


def _passes(rules, sender):
    """sender_rule policy: any deny match excludes; if allow rules exist the
    sender must match one; no rules => allow everything."""
    s = (sender or "").lower()
    allows = [p for p, a in rules if a == "allow"]
    if any(p.lower() in s for p, a in rules if a == "deny"):
        return False
    return not allows or any(p.lower() in s for p in allows)


def _backfill_query():
    """Recency bound + a server-side filename filter from the allowlist, so the
    list returns only document-bearing messages instead of every attachment."""
    fn = " OR ".join(f"filename:{e.lstrip('.')}" for e in config.GMAIL_ATTACH_EXT)
    q = config.GMAIL_INITIAL_QUERY.strip()
    return f"{q} has:attachment ({fn})" if fn else f"{q} has:attachment"


def _message_ids(svc, history_id):
    """Return (message_ids, latest_history_id, did_backfill). Incremental via the
    History API when we have a cursor; full bounded backfill otherwise (or when
    the stored historyId has aged out and Gmail 404s)."""
    if history_id:
        try:
            ids, page, latest = set(), None, history_id
            while True:
                resp = svc.users().history().list(
                    userId="me", startHistoryId=history_id,
                    historyTypes=["messageAdded"], pageToken=page).execute()
                for h in resp.get("history", []):
                    for m in h.get("messagesAdded", []):
                        ids.add(m["message"]["id"])
                latest = resp.get("historyId", latest)
                page = resp.get("nextPageToken")
                if not page:
                    break
            return ids, latest, False
        except Exception as e:  # noqa: BLE001 — historyId too old => backfill
            log.warn("gmail.history_expired", error=str(e))

    ids, page = set(), None
    query = _backfill_query()
    while True:
        resp = svc.users().messages().list(
            userId="me", q=query, pageToken=page).execute()
        for m in resp.get("messages", []) or []:
            ids.add(m["id"])
        page = resp.get("nextPageToken")
        if not page:
            break
    latest = svc.users().getProfile(userId="me").execute()["historyId"]
    return ids, latest, True


def _sync(account_id, email, history_id, token_path):
    svc = _service(token_path)
    ids, new_hist, backfill = _message_ids(svc, history_id)
    with db.connect() as conn:
        rules = conn.execute(
            "SELECT pattern, action FROM sender_rule WHERE account_id=%s",
            (account_id,)).fetchall()

    got = 0
    for mid in ids:
        msg = svc.users().messages().get(userId="me", id=mid, format="full").execute()
        sender, subject = _headers(msg)
        if not _passes(rules, sender):
            continue
        received = datetime.fromtimestamp(
            int(msg["internalDate"]) / 1000, tz=timezone.utc)
        for part in _attachments(msg["payload"]):
            if not _wanted(part):
                continue                        # skip images / non-document parts
            body = part["body"]
            size = body.get("size", 0) or 0
            if config.GMAIL_MIN_ATTACH_BYTES and size \
                    and size < config.GMAIL_MIN_ATTACH_BYTES:
                continue                        # tiny stray file, skip
            data = svc.users().messages().attachments().get(
                userId="me", messageId=mid, id=body["attachmentId"]).execute()["data"]
            ingest.ingest_bytes(
                base64.urlsafe_b64decode(data), part["filename"],
                {"source": "gmail",
                 "source_ref": f"gmail:{account_id}:{mid}:{part.get('partId', '')}",
                 "sender": sender, "subject": subject, "received_at": received,
                 "title": part["filename"]})
            got += 1

    with db.connect() as conn:
        conn.execute(
            "UPDATE account SET history_id=%s, last_full_sync_at=now() WHERE id=%s",
            (str(new_hist), account_id))
    log.info("gmail.sync", email=email, messages=len(ids), attachments=got,
             mode=("backfill" if backfill else "incremental"))


def poll():
    """One sync pass across every mounted account. Called by the worker loop."""
    if not config.GMAIL_TOKENS_DIR.exists():
        return
    tokens = sorted(config.GMAIL_TOKENS_DIR.glob("token-*.json"))
    if not tokens:
        return
    with db.connect() as conn:
        with conn.cursor() as cur:
            accounts = _accounts(cur, tokens)
    for account_id, email, history_id, token_path in accounts:
        try:
            _sync(account_id, email, history_id, token_path)
        except Exception as e:  # noqa: BLE001 — one bad account can't stall others
            log.error("gmail.sync_failed", email=email, error=str(e))
