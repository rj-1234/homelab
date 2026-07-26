"""Postgres-as-queue job runner. Claims via SELECT ... FOR UPDATE SKIP LOCKED
so multiple workers never grab the same job. Phase 2 handles the 'text' stage
(Tier-0 text-layer extraction); unknown stages are marked done as no-ops.
"""
import os

from . import config, db, extract, log

MAX_ATTEMPTS = 5


def claim():
    """Atomically take one *eligible* pending job and mark it running. Returns
    (job_id, document_id, stage) or None. Eligibility enforces exponential
    backoff between attempts: a job that just errored waits 2**attempts minutes
    (2, 4, 8, 16) before it can be reclaimed. Fresh jobs (locked_at NULL) run
    immediately. state='running' keeps other workers from re-claiming it."""
    conn = db.connect()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, document_id, stage FROM job WHERE state='pending' "
                "AND (locked_at IS NULL OR "
                "     now() >= locked_at + (interval '1 minute' * power(2, attempts))) "
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


def reconcile():
    """Requeue jobs that failed but haven't exhausted MAX_ATTEMPTS (e.g. failed
    under an older lower cap, or manually re-run). They retry under the same
    backoff. Idempotent; called once per worker loop. Prior error text is kept
    for visibility until the retry succeeds or truly fails."""
    with db.connect() as c:
        n = c.execute(
            "UPDATE job SET state='pending' "
            "WHERE state='failed' AND attempts < %s", (MAX_ATTEMPTS,)
        ).rowcount
    if n:
        log.info("jobs.reconciled", requeued=n)
    return n


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
    elif mime == "application/pdf" or mime.startswith("image/"):
        status = "needs_ocr"           # scanned PDF / photo -> OCR stage
        cur.execute("INSERT INTO job(document_id,stage) VALUES(%s,'ocr')", (doc_id,))
    else:
        status = "no_text"
    cur.execute("UPDATE document SET status=%s WHERE id=%s", (status, doc_id))
    return status


def _run_ocr(cur, doc_id):
    """PaddleOCR each page; escalate low-confidence pages to Claude vision."""
    from . import ocr
    mime, path = _blob_for(cur, doc_id)
    have_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    any_text = False
    for pno, png in ocr.pages_for(path, mime):
        engine, conf = "paddleocr", 0.0
        try:
            text, conf = ocr.paddle_png(png)
        except Exception as e:  # noqa: BLE001 — a bad page shouldn't kill the doc
            text = ""
            log.warn("ocr.paddle_failed", doc=doc_id, page=pno, error=str(e))
        if have_key and (conf < config.OCR_CONF_THRESHOLD or not text.strip()):
            try:
                escalated = ocr.claude_png(png)
                if escalated.strip():
                    text, engine, conf = escalated, "claude-vision", 1.0
            except Exception as e:  # noqa: BLE001
                log.warn("ocr.claude_failed", doc=doc_id, page=pno, error=str(e))
        text = text.replace("\x00", "")     # Postgres text rejects NUL
        if text.strip():
            any_text = True
        cur.execute(
            "INSERT INTO page(document_id,page_no,text,engine,confidence) "
            "VALUES(%s,%s,%s,%s,%s) ON CONFLICT (document_id,page_no) "
            "DO UPDATE SET text=EXCLUDED.text, engine=EXCLUDED.engine, "
            "confidence=EXCLUDED.confidence",
            (doc_id, pno, text, engine, conf),
        )
    status = "text_extracted" if any_text else "ocr_failed"
    cur.execute("UPDATE document SET status=%s WHERE id=%s", (status, doc_id))
    return status


_STAGES = {"text": _run_text, "ocr": _run_ocr}


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
        log.info("job.done", job=job_id, stage=stage, doc=doc_id, result=info)
    except Exception as e:  # noqa: BLE001 — isolate a bad doc, keep draining
        with db.connect() as c:
            c.execute(
                "UPDATE job SET state=%s, error=%s WHERE id=%s",
                ("pending" if _attempts(job_id) < MAX_ATTEMPTS else "failed",
                 str(e), job_id),
            )
        log.error("job.error", job=job_id, stage=stage, error=str(e))


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
