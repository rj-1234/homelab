"""Browse · search · manage UI over the ingested corpus.

Run: uvicorn doccat.api:app --host 0.0.0.0 --port 8000
"""
import json
import os
import re
import shutil
import urllib.request
import uuid
from pathlib import Path

import psycopg
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import (FileResponse, JSONResponse,
                               StreamingResponse)

from . import classify, config, db, ui

app = FastAPI(title="Document Catalog")

_DOC_COLS = (
    "d.id, d.title, d.status, d.doc_type, b.mime, b.size, d.created_at,"
    " d.primary_blob_sha AS sha,"
    " (SELECT count(*) FROM page p WHERE p.document_id=d.id) AS pages,"
    " (SELECT array_agg(t.name ORDER BY t.name) FROM document_tag dt"
    "  JOIN tag t ON t.id=dt.tag_id WHERE dt.document_id=d.id) AS tags"
)


def _rows(sql, args=()):
    with db.connect() as c:
        cur = c.execute(sql, args)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _one(sql, args=()):
    r = _rows(sql, args)
    return r[0] if r else None


def _embed_query(text):
    """Embed a search query via the embedder microservice. Raises on failure."""
    body = json.dumps({"texts": [text], "is_query": True}).encode()
    req = urllib.request.Request(
        config.EMBEDDER_URL + "/embed", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["vectors"][0]


def _hybrid_search(q, limit=60):
    """Keyword (FTS) + semantic (pgvector) search fused with Reciprocal Rank
    Fusion (RRF, k=60). Falls back to FTS-only if the embedder is unreachable.
    Returns document rows (same shape as the browse list) plus `score` and a
    `snippet` FTS headline."""
    hl = ("'StartSel=@@HL@@, StopSel=@@EHL@@, MaxFragments=1, MinWords=4,"
          " MaxWords=16, FragmentDelimiter= … '")
    try:
        vec = _embed_query(q)
        vec_lit = "[" + ",".join(f"{x:.7f}" for x in vec) + "]"
    except Exception:
        vec_lit = None

    if vec_lit is not None:
        sql = f"""
        WITH kw AS (
          SELECT d.id AS doc_id,
                 row_number() OVER (
                   ORDER BY max(ts_rank(p.tsv, plainto_tsquery('english', %s))) DESC
                 ) AS rnk
          FROM page p JOIN document d ON d.id=p.document_id
          WHERE p.tsv @@ plainto_tsquery('english', %s)
            AND d.canonical_document_id IS NULL
          GROUP BY d.id
          LIMIT 80
        ),
        sem AS (
          SELECT c.document_id AS doc_id,
                 row_number() OVER (ORDER BY min(c.embedding <=> %s::vector)) AS rnk
          FROM chunk c JOIN document d ON d.id=c.document_id
          WHERE c.embedding IS NOT NULL AND d.canonical_document_id IS NULL
          GROUP BY c.document_id
          LIMIT 80
        ),
        fused AS (
          SELECT COALESCE(kw.doc_id, sem.doc_id) AS doc_id,
                 COALESCE(1.0/(60+kw.rnk), 0) + COALESCE(1.0/(60+sem.rnk), 0) AS score
          FROM kw FULL OUTER JOIN sem ON kw.doc_id = sem.doc_id
        )
        SELECT {_DOC_COLS}, f.score,
          (SELECT ts_headline('english', p.text,
                    plainto_tsquery('english', %s), {hl})
           FROM page p WHERE p.document_id=d.id
           ORDER BY ts_rank(p.tsv, plainto_tsquery('english', %s)) DESC
           LIMIT 1) AS snippet
        FROM fused f
        JOIN document d ON d.id=f.doc_id
        JOIN blob b ON b.sha256=d.primary_blob_sha
        ORDER BY f.score DESC
        LIMIT %s
        """
        return _rows(sql, (q, q, vec_lit, q, q, limit))

    # FTS-only fallback
    sql = f"""
    SELECT * FROM (
      SELECT DISTINCT ON (d.id) {_DOC_COLS},
        ts_rank(p.tsv, plainto_tsquery('english', %s)) AS score,
        ts_headline('english', p.text, plainto_tsquery('english', %s), {hl}) AS snippet
      FROM page p JOIN document d ON d.id=p.document_id
      JOIN blob b ON b.sha256=d.primary_blob_sha
      WHERE p.tsv @@ plainto_tsquery('english', %s)
        AND d.canonical_document_id IS NULL
      ORDER BY d.id, score DESC
    ) s ORDER BY score DESC LIMIT %s
    """
    return _rows(sql, (q, q, q, limit))


# --- health + JSON -----------------------------------------------------------
@app.get("/healthz")
def healthz():
    with db.connect() as c:
        c.execute("SELECT 1")
    return {"ok": True}


@app.get("/api/documents")
def api_documents(q: str = "", status: str = "", tag: str = "", field: str = ""):
    if q.strip():
        return _hybrid_search(q.strip())
    if field.strip():
        # Docs a given vault field was extracted from. Resolve the opaque field id
        # to its (entity_class, value) server-side — the plaintext value is never
        # in the request URL. Canonical docs only, so the count matches the shelf.
        try:
            fid = int(field)
        except ValueError:
            return []
        f = _one("SELECT entity_class, value FROM field WHERE id=%s", (fid,))
        if not f:
            return []
        return _rows(
            f"SELECT {_DOC_COLS} FROM document d JOIN blob b ON b.sha256=d.primary_blob_sha"
            " WHERE d.canonical_document_id IS NULL AND EXISTS ("
            "  SELECT 1 FROM field f WHERE f.document_id=d.id"
            "  AND f.entity_class=%s AND f.value=%s)"
            " ORDER BY d.created_at DESC LIMIT 500",
            (f["entity_class"], f["value"]),
        )
    where = "WHERE d.canonical_document_id IS NULL"
    args = []
    if status:
        where += " AND d.status=%s"; args.append(status)
    if tag:
        where += (" AND EXISTS (SELECT 1 FROM document_tag dt JOIN tag t"
                  " ON t.id=dt.tag_id WHERE dt.document_id=d.id AND t.name=%s)")
        args.append(tag)
    return _rows(
        f"SELECT {_DOC_COLS} FROM document d JOIN blob b ON b.sha256=d.primary_blob_sha"
        f" {where} ORDER BY d.created_at DESC LIMIT 500",
        tuple(args),
    )


@app.get("/api/doc/{doc_id}")
def api_doc(doc_id: int):
    d = _one(
        f"SELECT {_DOC_COLS} FROM document d JOIN blob b ON b.sha256=d.primary_blob_sha"
        " WHERE d.id=%s", (doc_id,))
    if not d:
        return JSONResponse({"error": "not found"}, status_code=404)
    prov = _rows(
        "SELECT source, source_ref, sender, subject, received_at, created_at"
        " FROM source_event WHERE blob_sha=%s ORDER BY created_at", (d["sha"],))
    pages = _rows(
        "SELECT page_no, engine, text FROM page WHERE document_id=%s ORDER BY page_no",
        (doc_id,))
    fc = _one(
        "SELECT count(*) FILTER (WHERE confirmed) AS confirmed,"
        " count(*) FILTER (WHERE NOT confirmed) AS review"
        " FROM field WHERE document_id=%s", (doc_id,))
    jobs = _rows("SELECT stage, state FROM job WHERE document_id=%s ORDER BY id", (doc_id,))
    return {"doc": d, "provenance": prov, "pages": pages,
            "fields": fc or {"confirmed": 0, "review": 0}, "jobs": jobs}


@app.get("/api/doc/{doc_id}/raw")
def api_raw(doc_id: int):
    d = _one("SELECT b.path, b.mime, d.title FROM document d"
             " JOIN blob b ON b.sha256=d.primary_blob_sha WHERE d.id=%s", (doc_id,))
    if not d or not Path(d["path"]).exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(d["path"], media_type=d["mime"],
        headers={"Content-Disposition": f'inline; filename="{d["title"]}"'})


@app.get("/api/tags")
def api_tags():
    return _rows(
        "SELECT t.name, count(*) AS n FROM tag t"
        " JOIN document_tag dt ON dt.tag_id=t.id"
        " JOIN document d ON d.id=dt.document_id"
        " WHERE d.canonical_document_id IS NULL"
        " GROUP BY t.name ORDER BY n DESC LIMIT 40")


@app.get("/api/taxonomy")
def api_taxonomy():
    return {
        "tags": [{"category": cat, "subtags": subs}
                 for cat, subs in classify.taxonomy_tags()],
        "statuses": [{"key": k, "label": v[0]} for k, v in ui.STATUS.items()],
    }


@app.get("/api/sender-rules")
def api_sender_rules():
    return _rows(
        "SELECT sr.account_id, a.email, sr.pattern, sr.action"
        " FROM sender_rule sr JOIN account a ON a.id=sr.account_id"
        " ORDER BY a.email, sr.action, sr.pattern")


@app.get("/api/search")
def api_search(q: str):
    return _rows(
        "SELECT DISTINCT ON (d.id) d.id, d.title, b.mime,"
        " ts_rank(p.tsv, plainto_tsquery('english', %s)) AS rank"
        " FROM page p JOIN document d ON d.id=p.document_id"
        " JOIN blob b ON b.sha256=d.primary_blob_sha"
        " WHERE p.tsv @@ plainto_tsquery('english', %s)"
        " AND d.canonical_document_id IS NULL ORDER BY d.id, rank DESC",
        (q, q),
    )


# --- detail + manage ---------------------------------------------------------
@app.post("/api/doc/{doc_id}")
async def update(doc_id: int, request: Request):
    p = await request.json()
    with db.connect() as c:
        with c.cursor() as cur:
            cur.execute(
                "UPDATE document SET title=%s, doc_type=%s, status=%s WHERE id=%s",
                (p.get("title"), p.get("doc_type"), p.get("status"), doc_id),
            )
            # Saving confirms the displayed tag set as user-owned: any auto tag
            # the user kept becomes 'user' (a labelled example for the feedback
            # loop); ones they removed are dropped.
            cur.execute("DELETE FROM document_tag WHERE document_id=%s", (doc_id,))
            for name in {t.strip() for t in p.get("tags", []) if t.strip()}:
                cur.execute("INSERT INTO tag(name) VALUES(%s) ON CONFLICT (name) "
                            "DO UPDATE SET name=EXCLUDED.name RETURNING id", (name,))
                tag_id = cur.fetchone()[0]
                cur.execute("INSERT INTO document_tag(document_id,tag_id,source)"
                            " VALUES(%s,%s,'user') ON CONFLICT (document_id,tag_id)"
                            " DO UPDATE SET source='user'", (doc_id, tag_id))
    return {"ok": True}


@app.post("/api/doc/{doc_id}/reprocess")
async def reprocess(doc_id: int, request: Request):
    """Manually enqueue a pipeline stage for a document (retry text/OCR)."""
    p = await request.json()
    stage = p.get("stage", "text")
    if stage not in ("text", "ocr", "embed", "embed_pages"):
        return JSONResponse({"error": "bad stage"}, status_code=400)
    with db.connect() as c:
        if not c.execute("SELECT 1 FROM document WHERE id=%s", (doc_id,)).fetchone():
            return JSONResponse({"error": "not found"}, status_code=404)
        c.execute("INSERT INTO job(document_id,stage) VALUES(%s,%s)", (doc_id, stage))
    return {"ok": True, "stage": stage}


@app.post("/api/doc/{doc_id}/delete")
def delete_doc(doc_id: int):
    """Delete a document, its derived rows, and (if no other document shares it)
    its blob row, provenance, and stored file."""
    path = None
    with db.connect() as conn:
        with conn.cursor() as cur:
            row = cur.execute("SELECT primary_blob_sha FROM document WHERE id=%s",
                              (doc_id,)).fetchone()
            if not row:
                return JSONResponse({"error": "not found"}, status_code=404)
            sha = row[0]
            for sql in (
                "DELETE FROM job WHERE document_id=%s",
                "DELETE FROM page WHERE document_id=%s",
                "DELETE FROM extraction WHERE document_id=%s",
                "DELETE FROM chunk WHERE document_id=%s",
                "DELETE FROM fingerprint WHERE document_id=%s",
                "DELETE FROM document_tag WHERE document_id=%s",
            ):
                cur.execute(sql, (doc_id,))
            cur.execute("DELETE FROM duplicate_link WHERE document_id=%s"
                        " OR other_document_id=%s", (doc_id, doc_id))
            cur.execute("UPDATE document SET canonical_document_id=NULL"
                        " WHERE canonical_document_id=%s", (doc_id,))
            cur.execute("DELETE FROM document WHERE id=%s", (doc_id,))
            # blob is content-addressed and may be shared (dedupe) — drop it only
            # when no remaining document references it.
            if not cur.execute("SELECT 1 FROM document WHERE primary_blob_sha=%s"
                               " LIMIT 1", (sha,)).fetchone():
                r = cur.execute("SELECT path FROM blob WHERE sha256=%s", (sha,)).fetchone()
                path = r[0] if r else None
                cur.execute("DELETE FROM source_event WHERE blob_sha=%s", (sha,))
                cur.execute("DELETE FROM blob WHERE sha256=%s", (sha,))
    if path:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass
    return {"ok": True}


# --- status ------------------------------------------------------------------
def _status_data():
    accounts = _rows(
        "SELECT a.id, a.email, a.status, a.last_full_sync_at,"
        " (a.history_id IS NOT NULL) AS synced,"
        " (SELECT count(*) FROM source_event se WHERE se.source='gmail'"
        "   AND se.source_ref LIKE 'gmail:' || a.id || ':%%') AS attachments"
        " FROM account a WHERE a.provider='gmail' ORDER BY a.email")
    jobs = _rows("SELECT stage, state, count(*) AS n FROM job"
                 " GROUP BY stage, state ORDER BY stage, state")
    sources = _rows("SELECT source, count(*) AS n FROM source_event"
                    " GROUP BY source ORDER BY n DESC")
    failures = _rows(
        "SELECT j.id, j.stage, j.attempts, left(j.error, 200) AS error, d.title"
        " FROM job j JOIN document d ON d.id=j.document_id"
        " WHERE j.state='failed' ORDER BY j.id DESC LIMIT 10")
    docs = _one("SELECT count(*) AS n FROM document"
                " WHERE canonical_document_id IS NULL")
    fields = _one(
        "SELECT (SELECT count(*) FROM (SELECT DISTINCT entity_class, value"
        "          FROM field WHERE confirmed) s) AS confirmed,"
        " (SELECT count(*) FROM (SELECT DISTINCT entity_class, value FROM field f"
        "   WHERE NOT confirmed AND NOT EXISTS (SELECT 1 FROM field c"
        "     WHERE c.entity_class=f.entity_class AND c.value=f.value"
        "     AND c.confirmed)) r) AS review")
    return {"accounts": accounts, "jobs": jobs, "sources": sources,
            "failures": failures, "documents": docs["n"] if docs else 0,
            "fields": {"confirmed": fields["confirmed"] if fields else 0,
                       "review": fields["review"] if fields else 0}}


@app.get("/api/status")
def api_status():
    return _status_data()


@app.get("/api/events")
def api_events():
    """Server-Sent Events: push the status snapshot whenever pipeline state
    changes (Postgres LISTEN/NOTIFY, see migration 006), so the UI never polls.
    A 15s heartbeat comment keeps proxies from closing an idle connection."""
    def frame():
        return f"data: {json.dumps(jsonable_encoder(_status_data()))}\n\n"

    def gen():
        conn = psycopg.connect(config.DATABASE_URL, autocommit=True)
        try:
            conn.execute("LISTEN doccat_events")
            yield frame()                                       # initial snapshot
            while True:
                # blocks up to 15s; returns after the first NOTIFY (a burst of
                # row changes collapses into one refresh)
                changed = any(True for _ in conn.notifies(timeout=15, stop_after=1))
                yield frame() if changed else ": ping\n\n"
        finally:
            conn.close()
    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Connection": "keep-alive"})


# --- field vault (Phase 8) ---------------------------------------------------
# The shelf and review lists NEVER ship the plaintext value — only value_masked.
# Plaintext is handed out one field at a time by /reveal (the UI reveal-gate).

def _mask_value(value):
    """Same rule as jobs._mask; duplicated here to avoid importing the heavy jobs
    module (pymupdf) into the api pod."""
    alnum = sum(c.isalnum() for c in value)
    if alnum <= 4:
        return "•" * len(value)
    seen, out = 0, []
    for c in value:
        if c.isalnum():
            seen += 1
            out.append(c if seen > alnum - 4 else "•")
        else:
            out.append(c)
    return "".join(out)


@app.get("/api/fields")
def api_fields():
    """Vault shelf: confirmed fields, deduped by (entity_class, value) so the same
    value on multiple documents shows once; masked, newest-valid first per class.
    `doc_count` = how many canonical documents this value was extracted from, so
    the card can link back to its source(s)."""
    return _rows(
        # NOTE: `value` (plaintext) is selected in the inner query only so the
        # doc_count subquery can correlate on it — it is deliberately NOT projected
        # in the outer SELECT, so the raw value never leaves the server here.
        "SELECT t.id, t.document_id, t.entity_class, t.label, t.value_masked,"
        " t.expiry, t.valid_from, t.score,"
        " (SELECT count(DISTINCT f2.document_id) FROM field f2"
        "  JOIN document d2 ON d2.id=f2.document_id"
        "  WHERE f2.entity_class=t.entity_class AND f2.value=t.value"
        "  AND d2.canonical_document_id IS NULL) AS doc_count"
        " FROM (SELECT DISTINCT ON (entity_class, value)"
        " id, document_id, entity_class, value, label, value_masked, expiry, valid_from, score"
        " FROM field WHERE confirmed=true"
        " ORDER BY entity_class, value, (expiry IS NULL), expiry DESC, created_at DESC) t"
        " ORDER BY t.entity_class, (t.expiry IS NULL), t.expiry DESC")


@app.get("/api/review")
def api_review():
    """Unconfirmed candidates, deduped by (entity_class, value) and hiding any value
    already confirmed elsewhere — so you confirm each unique value once."""
    return _rows(
        "SELECT * FROM (SELECT DISTINCT ON (f.entity_class, f.value)"
        " f.id, f.document_id, f.entity_class, f.label, f.value_masked, f.score, d.title"
        " FROM field f JOIN document d ON d.id=f.document_id"
        " WHERE f.confirmed=false AND NOT EXISTS ("
        "   SELECT 1 FROM field c WHERE c.entity_class=f.entity_class"
        "   AND c.value=f.value AND c.confirmed)"
        " ORDER BY f.entity_class, f.value, f.score DESC NULLS LAST) t"
        " ORDER BY score DESC NULLS LAST, id DESC")


@app.get("/api/doc/{doc_id}/fields")
def api_doc_fields(doc_id: int):
    return _rows(
        "SELECT id, entity_class, label, value_masked, expiry, confirmed, score,"
        " source FROM field WHERE document_id=%s ORDER BY confirmed DESC, score DESC",
        (doc_id,))


@app.post("/api/field/{field_id}/reveal")
def api_field_reveal(field_id: int):
    """Hand out the plaintext value for one field (the reveal-gate)."""
    r = _one("SELECT value FROM field WHERE id=%s", (field_id,))
    if not r:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {"value": r["value"]}


@app.post("/api/field/{field_id}/confirm")
async def api_field_confirm(field_id: int, request: Request):
    """Confirm a candidate onto the shelf; optional value/label/expiry overrides
    (user correcting a mis-extracted number). source flips to 'user' on override."""
    body = {}
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001 — empty body = plain confirm
        pass
    value = (body.get("value") or "").strip()
    label = (body.get("label") or "").strip()
    expiry = (body.get("expiry") or "").strip() or None
    with db.connect() as c:
        if value:
            c.execute(
                "UPDATE field SET confirmed=true, value=%s, value_masked=%s,"
                " label=COALESCE(NULLIF(%s,''), label), expiry=%s, source='user'"
                " WHERE id=%s",
                (value, _mask_value(value), label, expiry, field_id))
        else:
            # plain confirm applies to every row sharing this (class, value) —
            # the same number on other documents shouldn't come back in Review.
            c.execute(
                "UPDATE field SET confirmed=true,"
                " label=COALESCE(NULLIF(%s,''), label),"
                " expiry=COALESCE(%s, expiry)"
                " WHERE (entity_class, value) ="
                "   (SELECT entity_class, value FROM field WHERE id=%s)",
                (label, expiry, field_id))
    return {"ok": True}


@app.post("/api/field/{field_id}/delete")
def api_field_delete(field_id: int):
    """Reject every row sharing this (class, value) — it's the same value, so it
    shouldn't reappear from another document."""
    with db.connect() as c:
        c.execute(
            "DELETE FROM field WHERE (entity_class, value) ="
            " (SELECT entity_class, value FROM field WHERE id=%s)", (field_id,))
    return {"ok": True}




@app.post("/api/sender-rule")
async def add_sender_rule(request: Request):
    p = await request.json()
    pattern = (p.get("pattern") or "").strip()
    action = p.get("action", "allow")
    if not pattern or action not in ("allow", "deny"):
        return JSONResponse({"error": "pattern and allow|deny required"}, status_code=400)
    with db.connect() as c:
        c.execute("INSERT INTO sender_rule(account_id,pattern,action) VALUES(%s,%s,%s)",
                  (p["account_id"], pattern, action))
    return {"ok": True}


@app.post("/api/sender-rule/delete")
async def del_sender_rule(request: Request):
    p = await request.json()
    with db.connect() as c:
        c.execute("DELETE FROM sender_rule WHERE account_id=%s AND pattern=%s AND action=%s",
                  (p["account_id"], p.get("pattern"), p.get("action")))
    return {"ok": True}


# --- upload ------------------------------------------------------------------
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(name: str) -> str:
    """Basename only, restricted charset, length-capped — never a path."""
    base = os.path.basename((name or "").strip()) or "upload"
    base = _SAFE.sub("_", base).lstrip(".") or "upload"
    return base[-180:]


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    """Land uploads directly in the inbox; the worker's scan ingests them.
    Written to a dot-prefixed temp (scanner skips dotfiles) then atomically
    renamed in-place, so a half-written file is never claimed."""
    inbox = config.INBOX
    inbox.mkdir(parents=True, exist_ok=True)
    queued = []
    for f in files:
        name = _safe_name(f.filename)
        dest = inbox / name
        if dest.exists():                       # don't clobber a pending upload
            stem, ext = os.path.splitext(name)
            dest = inbox / f"{stem}-{uuid.uuid4().hex[:6]}{ext}"
        tmp = inbox / f".upload-{uuid.uuid4().hex}.part"
        try:
            with tmp.open("wb") as out:
                shutil.copyfileobj(f.file, out)
            os.replace(tmp, dest)               # atomic within the dataset
        finally:
            if tmp.exists():
                tmp.unlink()
            await f.close()
        queued.append(dest.name)
    return {"ok": True, "queued": queued}
