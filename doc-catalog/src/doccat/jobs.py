"""Postgres-as-queue job runner. Claims via SELECT ... FOR UPDATE SKIP LOCKED
so multiple workers never grab the same job. Phase 2 handles the 'text' stage
(Tier-0 text-layer extraction); unknown stages are marked done as no-ops.
"""
import json
import os
import urllib.request

from . import config, db, extract, log

MAX_ATTEMPTS = 5


def claim(stages=None):
    """Atomically take one *eligible* pending job and mark it running. Returns
    (job_id, document_id, stage) or None. When `stages` is given, only those
    stages are claimed (lets a dedicated worker drain one stage). Eligibility
    enforces exponential backoff between attempts: a job that just errored waits
    2**attempts minutes (2, 4, 8, 16) before it can be reclaimed. Fresh jobs
    (locked_at NULL) run immediately. state='running' keeps other workers from
    re-claiming it."""
    where = ("state='pending' AND (locked_at IS NULL OR "
             "now() >= locked_at + (interval '1 minute' * power(2, attempts)))")
    params = []
    if stages:
        where += " AND stage = ANY(%s)"
        params.append(list(stages))
    conn = db.connect()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, document_id, stage FROM job WHERE " + where +
                " ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1", params)
            row = cur.fetchone()
            if not row:
                return None
            cur.execute(
                "UPDATE job SET state='running', locked_at=now(), "
                "attempts=attempts+1 WHERE id=%s",
                (row[0],),
            )
    return row


def reconcile(stages=None):
    """Requeue retryable jobs so nothing stalls forever. Two cases: (a) 'failed'
    jobs that haven't exhausted MAX_ATTEMPTS (failed under an older cap, or a
    manual re-run), and (b) 'running' jobs whose lock is older than
    JOB_STALE_SECONDS — a worker that died mid-job leaves them 'running', and
    claim() only takes 'pending', so without this they'd never retry. Scoped to
    `stages` when given. Idempotent; called once per loop."""
    stage_clause, stage_param = "", []
    if stages:
        stage_clause = " AND stage = ANY(%s)"
        stage_param = [list(stages)]
    with db.connect() as c:
        n = c.execute(
            "UPDATE job SET state='pending' WHERE state='failed' AND attempts < %s"
            + stage_clause, [MAX_ATTEMPTS] + stage_param).rowcount
        n += c.execute(
            "UPDATE job SET state='pending' WHERE state='running'"
            " AND locked_at < now() - make_interval(secs => %s) AND attempts < %s"
            + stage_clause,
            [config.JOB_STALE_SECONDS, MAX_ATTEMPTS] + stage_param).rowcount
    if n:
        log.info("jobs.reconciled", requeued=n, stages=list(stages) if stages else "all")
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
    elif mime in extract.OFFICE_EXTRACTORS:
        fn, engine = extract.OFFICE_EXTRACTORS[mime]
        pages = fn(path)
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
        cur.execute("INSERT INTO job(document_id,stage) VALUES(%s,'embed')", (doc_id,))
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
        engine, conf = "rapidocr", 0.0
        try:
            text, conf = ocr.ocr_png(png)
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
    if any_text:
        cur.execute("INSERT INTO job(document_id,stage) VALUES(%s,'embed')", (doc_id,))
    status = "text_extracted" if any_text else "ocr_failed"
    cur.execute("UPDATE document SET status=%s WHERE id=%s", (status, doc_id))
    return status


# --- embed + semantic tagging ------------------------------------------------
def _embed(texts, is_query=False):
    """Call the embedder service; returns a list of L2-normalized vectors."""
    body = json.dumps({"texts": texts, "is_query": is_query}).encode()
    req = urllib.request.Request(
        config.EMBEDDER_URL + "/embed", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["vectors"]


_proto_state = {"protos": None, "confirmed": -1}


def _prototypes():
    """Category prototypes, in document (passage) space so they compare directly
    to a doc vector. Base = the zero-shot description embedding; a category with
    at least CLASSIFY_MIN_CENTROID user-confirmed documents is replaced by the
    centroid of those documents' doc-level vectors. Rebuilt whenever the count of
    confirmed tags changes (cheap invalidation) so corrections take effect."""
    import numpy as np
    from . import classify

    with db.connect() as c:
        confirmed = c.execute(
            "SELECT count(*) FROM document_tag WHERE source='user'").fetchone()[0]
    if _proto_state["protos"] is not None and _proto_state["confirmed"] == confirmed:
        return _proto_state["protos"]

    nd = classify.category_descriptions()
    desc_vecs = _embed([d for _, d in nd])            # passage space (no instruct)
    protos = {name: np.array(v) for (name, _), v in zip(nd, desc_vecs)}

    with db.connect() as c:
        for name in list(protos):
            members = classify.category_members(name)
            rows = c.execute(
                "SELECT DISTINCT ch.document_id, ch.embedding::text FROM chunk ch"
                " JOIN document_tag dt ON dt.document_id=ch.document_id"
                " JOIN tag t ON t.id=dt.tag_id"
                " WHERE ch.page_no IS NULL AND dt.source='user' AND t.name = ANY(%s)",
                (members,)).fetchall()
            if len(rows) >= config.CLASSIFY_MIN_CENTROID:
                mat = np.array([json.loads(r[1]) for r in rows])
                c_vec = mat.mean(axis=0)
                norm = float(np.linalg.norm(c_vec))
                if norm > 0:
                    protos[name] = c_vec / norm     # L2-normalized centroid

    _proto_state.update(protos=protos, confirmed=confirmed)
    return protos


def _pgvec(a):
    return "[" + ",".join(f"{x:.6f}" for x in a) + "]"


def _run_embed(cur, doc_id, pages=None):
    """Embed the document, store vectors, and assign taxonomy tags. `pages`
    overrides config.EMBED_PAGES for this run (the UI 'Embed pages' trigger)."""
    import numpy as np
    from . import classify

    do_pages = config.EMBED_PAGES if pages is None else pages

    pages = cur.execute(
        "SELECT page_no, text FROM page WHERE document_id=%s ORDER BY page_no",
        (doc_id,)).fetchall()
    page_texts = [(pno, t or "") for pno, t in pages if (t or "").strip()]
    doc_text = "\n\n".join(t for _, t in page_texts).strip()[:config.EMBED_MAX_CHARS]
    if not doc_text:
        cur.execute("UPDATE document SET status='no_text' WHERE id=%s", (doc_id,))
        return "no_text"

    row = cur.execute(
        "SELECT string_agg(DISTINCT coalesce(se.sender,''),' ') FROM source_event se"
        " JOIN document d ON d.primary_blob_sha=se.blob_sha WHERE d.id=%s",
        (doc_id,)).fetchone()
    sender = row[0] if row and row[0] else ""

    # doc-level vector always (drives tagging); per-page chunks only when enabled
    # (they're for future page-level search and are the slow part on CPU).
    inputs = [doc_text]
    if do_pages:
        inputs += [t[:4000] for _, t in page_texts]
    vecs = _embed(inputs)
    doc_vec = np.array(vecs[0])

    cur.execute("DELETE FROM chunk WHERE document_id=%s", (doc_id,))
    cur.execute("INSERT INTO chunk(document_id,page_no,text,embedding)"
                " VALUES(%s,NULL,%s,%s::vector)",
                (doc_id, doc_text[:8000], _pgvec(doc_vec)))
    if do_pages:
        for (pno, t), v in zip(page_texts, vecs[1:]):
            cur.execute("INSERT INTO chunk(document_id,page_no,text,embedding)"
                        " VALUES(%s,%s,%s,%s::vector)",
                        (doc_id, pno, t[:8000], _pgvec(np.array(v))))

    protos = _prototypes()
    tags = classify.classify(doc_vec, protos, doc_text, sender)

    # refresh auto tags without clobbering user-confirmed ones
    cur.execute("DELETE FROM document_tag WHERE document_id=%s AND source='auto'",
                (doc_id,))
    for name in sorted(tags):
        cur.execute("INSERT INTO tag(name) VALUES(%s) ON CONFLICT (name) "
                    "DO UPDATE SET name=EXCLUDED.name RETURNING id", (name,))
        tid = cur.fetchone()[0]
        cur.execute("INSERT INTO document_tag(document_id,tag_id,source) "
                    "VALUES(%s,%s,'auto') ON CONFLICT (document_id,tag_id) "
                    "DO NOTHING", (doc_id, tid))

    scores = {n: round(float(np.dot(doc_vec, protos[n])), 4) for n in protos}
    cur.execute(
        "INSERT INTO extraction(document_id,schema_version,model,model_version,"
        "params_hash,payload,confidence) VALUES(%s,'tags-v1',%s,'zeroshot',%s,%s,%s)",
        (doc_id, config.EMBED_MODEL, str(config.CLASSIFY_THRESHOLD),
         json.dumps({"tags": sorted(tags), "scores": scores}),
         max(scores.values()) if scores else None))

    cur.execute("UPDATE document SET status='tagged' WHERE id=%s", (doc_id,))
    return "tagged:" + ",".join(sorted(tags))


_STAGES = {
    "text": _run_text,
    "ocr": _run_ocr,
    "embed": _run_embed,
    "embed_pages": lambda cur, doc_id: _run_embed(cur, doc_id, pages=True),
}


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


def drain(stages=None, max_batch=200):
    """Process pending jobs (optionally only `stages`) until none remain or the
    batch cap. Returns count."""
    n = 0
    while n < max_batch:
        job = claim(stages)
        if not job:
            break
        _process(job)
        n += 1
    return n
