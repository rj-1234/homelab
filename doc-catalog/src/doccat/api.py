"""Dumb list view + JSON. Phase 1: prove provenance is captured end to end.

Run: uvicorn doccat.api:app --host 0.0.0.0 --port 8000
"""
import html

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from . import db

app = FastAPI(title="Document Catalog")


@app.get("/healthz")
def healthz():
    conn = db.connect()
    with conn, conn.cursor() as cur:
        cur.execute("SELECT 1")
    return {"ok": True}


def _rows(sql, args=()):
    conn = db.connect()
    with conn, conn.cursor() as cur:
        cur.execute(sql, args)
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@app.get("/api/documents")
def api_documents():
    # Canonical documents only (canonical_document_id IS NULL = "I am canonical").
    # Return the list directly so FastAPI's jsonable_encoder serializes datetimes.
    return _rows(
        "SELECT d.id, d.title, d.doc_type, d.status, d.created_at,"
        " b.mime, b.size, d.primary_blob_sha"
        " FROM document d JOIN blob b ON b.sha256 = d.primary_blob_sha"
        " WHERE d.canonical_document_id IS NULL"
        " ORDER BY d.created_at DESC LIMIT 500"
    )


@app.get("/", response_class=HTMLResponse)
def index():
    docs = _rows(
        "SELECT d.id, d.title, d.status, d.created_at, b.mime, b.size,"
        " (SELECT count(*) FROM source_event s WHERE s.blob_sha = d.primary_blob_sha) AS events"
        " FROM document d JOIN blob b ON b.sha256 = d.primary_blob_sha"
        " WHERE d.canonical_document_id IS NULL"
        " ORDER BY d.created_at DESC LIMIT 500"
    )
    rows = "\n".join(
        f"<tr><td>{d['id']}</td><td>{html.escape(d['title'] or '')}</td>"
        f"<td>{html.escape(d['mime'])}</td><td>{d['size']:,}</td>"
        f"<td>{d['events']}</td><td>{html.escape(d['status'])}</td>"
        f"<td>{d['created_at']:%Y-%m-%d %H:%M}</td></tr>"
        for d in docs
    )
    return (
        "<!doctype html><meta charset=utf-8><title>Document Catalog</title>"
        "<style>body{font:14px system-ui;margin:2rem}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{border-bottom:1px solid #ddd;padding:.4rem .6rem;text-align:left}"
        "th{color:#555}</style>"
        f"<h1>Document Catalog <small>({len(docs)})</small></h1>"
        "<table><tr><th>id</th><th>title</th><th>mime</th><th>bytes</th>"
        "<th>events</th><th>status</th><th>ingested</th></tr>"
        f"{rows}</table>"
    )
