"""Postgres-as-queue job runner. Claims via SELECT ... FOR UPDATE SKIP LOCKED
so multiple workers never grab the same job. Phase 2 handles the 'text' stage
(Tier-0 text-layer extraction); unknown stages are marked done as no-ops.
"""
from . import db, extract

MAX_ATTEMPTS = 3


def claim():
    """Atomically take one pending job and mark it running. Returns
    (job_id, document_id, stage) or None. The row lock is released on commit;
    state='running' keeps other workers from re-claiming it."""
    conn = db.connect()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, document_id, stage FROM job WHERE state='pending' "
                "ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1"
            )
            row = cur.fetchone()
            if not row:
                return None
            cur.execute(
                "UPDATE job SET state='running', locked_at=now(), "
                "attempts=attempts+1 WHERE id=%s",
                (row[0],),
            )
    return row


def _blob_for(cur, document_id):
    cur.execute(
        "SELECT b.mime, b.path FROM document d JOIN blob b "
        "ON b.sha256 = d.primary_blob_sha WHERE d.id=%s",
        (document_id,),
    )
    return cur.fetchone()


def _run_text(cur, doc_id):
    mime, path = _blob_for(cur, doc_id)
    if mime == "application/pdf":
        pages, engine = extract.pages_from_pdf(path), "pdf-text-layer"
    elif mime == "text/plain":
        pages, engine = extract.pages_from_text(path), "text"
    else:
        pages, engine = [], "skip"

    for pno, txt in pages:
        cur.execute(
            "INSERT INTO page(document_id,page_no,text,engine,confidence) "
            "VALUES(%s,%s,%s,%s,1.0) ON CONFLICT (document_id,page_no) "
            "DO UPDATE SET text=EXCLUDED.text, engine=EXCLUDED.engine",
            (doc_id, pno, txt, engine),
        )

    has_text = any(t.strip() for _, t in pages)
    if has_text:
        status = "text_extracted"
    elif mime == "application/pdf":
        status = "needs_ocr"           # scanned PDF -> Phase 4 OCR
    else:
        status = "no_text"
    cur.execute("UPDATE document SET status=%s WHERE id=%s", (status, doc_id))
    return status


_STAGES = {"text": _run_text}


def _process(job):
    job_id, doc_id, stage = job
    try:
        conn = db.connect()
        with conn:
            with conn.cursor() as cur:
                handler = _STAGES.get(stage)
                info = handler(cur, doc_id) if handler else "noop"
                cur.execute(
                    "UPDATE job SET state='done', error=NULL WHERE id=%s", (job_id,)
                )
        print(f"[job] {job_id} done stage={stage} doc={doc_id} -> {info}")
    except Exception as e:  # noqa: BLE001 — isolate a bad doc, keep draining
        with db.connect() as c:
            c.execute(
                "UPDATE job SET state=%s, error=%s WHERE id=%s",
                ("pending" if _attempts(job_id) < MAX_ATTEMPTS else "failed",
                 str(e), job_id),
            )
        print(f"[job] {job_id} error stage={stage}: {e}")


def _attempts(job_id):
    with db.connect() as c:
        return c.execute("SELECT attempts FROM job WHERE id=%s", (job_id,)).fetchone()[0]


def drain(max_batch=200):
    """Process pending jobs until none remain (or batch cap). Returns count."""
    n = 0
    while n < max_batch:
        job = claim()
        if not job:
            break
        _process(job)
        n += 1
    return n
