"""Browse · search · manage UI over the ingested corpus.

Run: uvicorn doccat.api:app --host 0.0.0.0 --port 8000
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from . import db, ui

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


# --- health + JSON -----------------------------------------------------------
@app.get("/healthz")
def healthz():
    with db.connect() as c:
        c.execute("SELECT 1")
    return {"ok": True}


@app.get("/api/documents")
def api_documents():
    return _rows(
        f"SELECT {_DOC_COLS} FROM document d JOIN blob b ON b.sha256=d.primary_blob_sha"
        " WHERE d.canonical_document_id IS NULL ORDER BY d.created_at DESC LIMIT 500"
    )


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


# --- browse + search (HTML) --------------------------------------------------
def _rail(active_status, active_tag):
    counts = _rows(
        "SELECT status, count(*) n FROM document WHERE canonical_document_id IS NULL"
        " GROUP BY status ORDER BY n DESC"
    )
    tags = _rows(
        "SELECT t.name, count(*) n FROM tag t JOIN document_tag dt ON dt.tag_id=t.id"
        " GROUP BY t.name ORDER BY n DESC LIMIT 30"
    )
    total = sum(c["n"] for c in counts)
    st = [f"<a class='{'on' if not active_status else ''}' href='/'>"
          f"All<span class=n>{total}</span></a>"]
    for c in counts:
        label = ui.status_bits(c["status"])[0]
        on = "on" if active_status == c["status"] else ""
        st.append(f"<a class='{on}' href='/?status={ui.esc(c['status'])}'>"
                  f"{ui.esc(label)}<span class=n>{c['n']}</span></a>")
    tg = "".join(
        f"<a class='{'on' if active_tag==t['name'] else ''}' href='/?tag={ui.esc(t['name'])}'>"
        f"{ui.esc(t['name'])}<span class=n>{t['n']}</span></a>" for t in tags
    )
    tag_block = f"<div><p class=eyebrow>Tags</p>{tg}</div>" if tags else ""
    return (
        "<nav class=rail>"
        f"<div><p class=eyebrow>Status</p>{''.join(st)}</div>"
        f"{tag_block}</nav>"
    )


@app.get("/", response_class=HTMLResponse)
def index(q: str = "", status: str = "", tag: str = ""):
    if q:
        docs = _rows(
            "SELECT * FROM ("
            f" SELECT DISTINCT ON (d.id) {_DOC_COLS},"
            "   ts_rank(p.tsv, plainto_tsquery('english', %s)) AS rank,"
            "   ts_headline('english', p.text, plainto_tsquery('english', %s),"
            "     'StartSel=@@HL@@, StopSel=@@EHL@@, MaxFragments=2, MinWords=5,"
            "      MaxWords=18, FragmentDelimiter= … ') AS snippet"
            " FROM page p JOIN document d ON d.id=p.document_id"
            " JOIN blob b ON b.sha256=d.primary_blob_sha"
            " WHERE p.tsv @@ plainto_tsquery('english', %s)"
            " AND d.canonical_document_id IS NULL ORDER BY d.id, rank DESC"
            ") s ORDER BY rank DESC LIMIT 100",
            (q, q, q),
        )
        heading = f"Search · {ui.esc(q)}"
    else:
        where = "WHERE d.canonical_document_id IS NULL"
        args = []
        if status:
            where += " AND d.status=%s"; args.append(status)
        if tag:
            where += (" AND EXISTS (SELECT 1 FROM document_tag dt JOIN tag t"
                      " ON t.id=dt.tag_id WHERE dt.document_id=d.id AND t.name=%s)")
            args.append(tag)
        docs = _rows(
            f"SELECT {_DOC_COLS} FROM document d JOIN blob b ON b.sha256=d.primary_blob_sha"
            f" {where} ORDER BY d.created_at DESC LIMIT 500",
            tuple(args),
        )
        heading = ui.status_bits(status)[0] if status else (f"Tag · {ui.esc(tag)}" if tag else "All documents")

    if docs:
        cards = "<div class=stack>" + "".join(ui.card(d) for d in docs) + "</div>"
    else:
        cards = ("<div class=empty><b>Nothing here yet</b>"
                 "Drop a file into FileBrowser — it lands in the catalog within a minute.</div>"
                 if not (q or status or tag) else
                 "<div class=empty><b>No matches</b>Try a different term or clear the filter.</div>")

    body = (
        "<div class=wrap>"
        + _rail(status, tag)
        + f"<main><h1 class=title>{heading}</h1>"
        + f"<span class=count>{len(docs)} document{'s' if len(docs)!=1 else ''}</span>"
        + cards + "</main></div>"
    )
    return ui.shell(heading, body, q)


# --- detail + manage ---------------------------------------------------------
@app.get("/doc/{doc_id}", response_class=HTMLResponse)
def detail(doc_id: int):
    d = _one(
        f"SELECT {_DOC_COLS}, b.size FROM document d JOIN blob b ON b.sha256=d.primary_blob_sha"
        " WHERE d.id=%s", (doc_id,),
    )
    if not d:
        return HTMLResponse(ui.shell("Not found",
            "<div class=wrap><main><div class=empty><b>No such document</b>"
            "<a href=/>Back to the catalog</a></div></main></div>"), status_code=404)

    prov = _rows("SELECT source, source_ref, sender, received_at, created_at"
                 " FROM source_event WHERE blob_sha=%s ORDER BY created_at", (d["sha"],))
    pages = _rows("SELECT page_no, engine, text FROM page WHERE document_id=%s ORDER BY page_no",
                  (doc_id,))
    label, cls = ui.status_bits(d["status"])

    prov_html = "".join(
        f"<li><span class=when>{(p['received_at'] or p['created_at']):%Y-%m-%d %H:%M}</span>"
        f"<span>{ui.esc(p['source'])} · <span class=mono>{ui.esc(p['source_ref'])}</span></span></li>"
        for p in prov
    )
    pages_html = "".join(
        f"<details class=page {'open' if p['page_no']==1 else ''}>"
        f"<summary>Page {p['page_no']} · {ui.esc(p['engine'] or '—')} · {len(p['text'] or '')} chars</summary>"
        f"<pre>{ui.esc(p['text']) or '<em>no text</em>'}</pre></details>"
        for p in pages
    ) or "<p class=count>No text extracted yet.</p>"

    opts = "".join(
        f"<option value='{k}' {'selected' if d['status']==k else ''}>{v[0]}</option>"
        for k, v in ui.STATUS.items()
    )
    tags_val = ", ".join(d["tags"] or [])

    sheet = f"""
    <div class=wrap style="grid-template-columns:1fr">
      <main>
        <a class=back href=/>← Catalog</a>
        <div class=sheet>
          <div class=row1 style="display:flex;align-items:baseline;gap:.7rem">
            <h1 style="flex:1">{ui.esc(d['title'])}</h1>
            <span class='chip {cls}'>{ui.esc(label)}</span>
          </div>
          <div class=meta><span class=mono>#{d['id']}</span>
            <span class=mono>{ui.esc(d['sha'][:24])}…</span>
            <span>{ui.esc(d['mime'])}</span>
            <span>{d['size']:,} bytes</span>
            <span>{d['pages'] or 0} pages</span>
            <span>{d['created_at']:%Y-%m-%d %H:%M}</span></div>
          <div class=act style="margin-top:.8rem">
            <a class='btn ghost' href='/doc/{d['id']}/raw' target=_blank>View original</a>
          </div>

          <div class=section>
            <p class=eyebrow>Manage</p>
            <div class=field><label>Title</label>
              <input id=f_title value="{ui.esc(d['title'])}"></div>
            <div class=field><label>Type</label>
              <input id=f_type placeholder="e.g. tax · statement · medical" value="{ui.esc(d['doc_type'] or '')}"></div>
            <div class=field><label>Status</label>
              <select id=f_status>{opts}</select></div>
            <div class=field><label>Tags (comma-separated)</label>
              <input id=f_tags value="{ui.esc(tags_val)}"></div>
            <div class=act><button class=btn onclick="save({d['id']})">Save changes</button>
              <span class=saved id=saved>Saved</span></div>
          </div>

          <div class=section><p class=eyebrow>Provenance</p>
            <ul class=prov>{prov_html}</ul></div>

          <div class=section><p class=eyebrow>Extracted text</p>
            {pages_html}</div>
        </div>
      </main>
    </div>
    <script>
    async function save(id){{
      const body={{title:f_title.value,doc_type:f_type.value||null,
        status:f_status.value,
        tags:f_tags.value.split(',').map(s=>s.trim()).filter(Boolean)}};
      const r=await fetch('/api/doc/'+id,{{method:'POST',
        headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});
      const s=document.getElementById('saved');
      if(r.ok){{s.textContent='Saved';s.classList.add('show');setTimeout(()=>s.classList.remove('show'),1600);}}
      else{{s.textContent='Save failed';s.classList.add('show');}}
    }}
    </script>
    """
    return ui.shell(d["title"], sheet)


@app.get("/doc/{doc_id}/raw")
def raw(doc_id: int):
    d = _one("SELECT b.path, b.mime, d.title FROM document d"
             " JOIN blob b ON b.sha256=d.primary_blob_sha WHERE d.id=%s", (doc_id,))
    if not d or not Path(d["path"]).exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    # inline so PDFs/images open in the tab; browser still lets you download.
    return FileResponse(
        d["path"], media_type=d["mime"],
        headers={"Content-Disposition": f'inline; filename="{d["title"]}"'},
    )


@app.post("/api/doc/{doc_id}")
async def update(doc_id: int, request: Request):
    p = await request.json()
    with db.connect() as c:
        with c.cursor() as cur:
            cur.execute(
                "UPDATE document SET title=%s, doc_type=%s, status=%s WHERE id=%s",
                (p.get("title"), p.get("doc_type"), p.get("status"), doc_id),
            )
            cur.execute("DELETE FROM document_tag WHERE document_id=%s", (doc_id,))
            for name in {t.strip() for t in p.get("tags", []) if t.strip()}:
                cur.execute("INSERT INTO tag(name) VALUES(%s) ON CONFLICT (name) "
                            "DO UPDATE SET name=EXCLUDED.name RETURNING id", (name,))
                tag_id = cur.fetchone()[0]
                cur.execute("INSERT INTO document_tag(document_id,tag_id) VALUES(%s,%s)"
                            " ON CONFLICT DO NOTHING", (doc_id, tag_id))
    return {"ok": True}
