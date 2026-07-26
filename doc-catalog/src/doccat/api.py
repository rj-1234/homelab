"""Browse + full-text search UI (Phase 3) over the ingested corpus.

Run: uvicorn doccat.api:app --host 0.0.0.0 --port 8000
"""
import html

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from . import db

app = FastAPI(title="Document Catalog")


@app.get("/healthz")
def healthz():
    with db.connect() as c:
        c.execute("SELECT 1")
    return {"ok": True}


def _rows(sql, args=()):
    with db.connect() as c:
        cur = c.execute(sql, args)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


# --- JSON --------------------------------------------------------------------
@app.get("/api/documents")
def api_documents():
    return _rows(
        "SELECT d.id, d.title, d.doc_type, d.status, d.created_at, b.mime, b.size"
        " FROM document d JOIN blob b ON b.sha256 = d.primary_blob_sha"
        " WHERE d.canonical_document_id IS NULL"
        " ORDER BY d.created_at DESC LIMIT 500"
    )


@app.get("/api/search")
def api_search(q: str):
    return _rows(
        "SELECT DISTINCT ON (d.id) d.id, d.title, b.mime,"
        " ts_rank(p.tsv, plainto_tsquery('english', %s)) AS rank"
        " FROM page p JOIN document d ON d.id = p.document_id"
        " JOIN blob b ON b.sha256 = d.primary_blob_sha"
        " WHERE p.tsv @@ plainto_tsquery('english', %s)"
        " AND d.canonical_document_id IS NULL"
        " ORDER BY d.id, rank DESC",
        (q, q),
    )


# --- HTML --------------------------------------------------------------------
_STYLE = (
    "<style>body{font:14px system-ui;margin:2rem;max-width:1000px}"
    "table{border-collapse:collapse;width:100%}"
    "th,td{border-bottom:1px solid #ddd;padding:.4rem .6rem;text-align:left;vertical-align:top}"
    "th{color:#555}mark{background:#fe6;padding:0 .1em}"
    "input[type=search]{font:inherit;padding:.4rem .6rem;width:60%}"
    ".snip{color:#444;font-size:.9em}.meta{color:#888;font-size:.85em}</style>"
)


def _search_box(q):
    return (
        "<form method=get action=/>"
        f"<input type=search name=q placeholder='Search documents…' value=\"{html.escape(q or '')}\">"
        " <button>Search</button>"
        + (" · <a href=/>clear</a>" if q else "")
        + "</form>"
    )


def _hl(snippet):
    # ts_headline emits our safe markers; escape everything, then re-mark.
    return (
        html.escape(snippet or "")
        .replace("@@HL@@", "<mark>")
        .replace("@@EHL@@", "</mark>")
    )


@app.get("/", response_class=HTMLResponse)
def index(q: str = "", status: str = ""):
    if q:
        docs = _rows(
            "SELECT * FROM ("
            "  SELECT DISTINCT ON (d.id) d.id, d.title, d.status, b.mime, d.created_at,"
            "    ts_rank(p.tsv, plainto_tsquery('english', %s)) AS rank,"
            "    ts_headline('english', p.text, plainto_tsquery('english', %s),"
            "      'StartSel=@@HL@@, StopSel=@@EHL@@, MaxFragments=2, MinWords=5,"
            "       MaxWords=18, FragmentDelimiter= … ') AS snippet"
            "  FROM page p JOIN document d ON d.id = p.document_id"
            "  JOIN blob b ON b.sha256 = d.primary_blob_sha"
            "  WHERE p.tsv @@ plainto_tsquery('english', %s)"
            "  AND d.canonical_document_id IS NULL"
            "  ORDER BY d.id, rank DESC"
            ") s ORDER BY rank DESC LIMIT 100",
            (q, q, q),
        )
    else:
        args, where = [], "WHERE d.canonical_document_id IS NULL"
        if status:
            where += " AND d.status = %s"
            args.append(status)
        docs = _rows(
            "SELECT d.id, d.title, d.status, b.mime, d.created_at, NULL AS snippet"
            " FROM document d JOIN blob b ON b.sha256 = d.primary_blob_sha"
            f" {where} ORDER BY d.created_at DESC LIMIT 500",
            tuple(args),
        )

    body = []
    for d in docs:
        snip = f"<div class=snip>{_hl(d['snippet'])}</div>" if d.get("snippet") else ""
        body.append(
            f"<tr><td>{d['id']}</td>"
            f"<td>{html.escape(d['title'] or '')}{snip}</td>"
            f"<td class=meta>{html.escape(d['mime'])}</td>"
            f"<td class=meta>{html.escape(d['status'])}</td>"
            f"<td class=meta>{d['created_at']:%Y-%m-%d}</td></tr>"
        )
    heading = f"Search: “{html.escape(q)}”" if q else "Document Catalog"
    return (
        "<!doctype html><meta charset=utf-8><title>Document Catalog</title>" + _STYLE
        + f"<h1>{heading} <small>({len(docs)})</small></h1>"
        + _search_box(q)
        + "<table><tr><th>id</th><th>title</th><th>mime</th><th>status</th><th>date</th></tr>"
        + "\n".join(body)
        + "</table>"
    )
