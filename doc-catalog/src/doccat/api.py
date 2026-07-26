"""Browse · search · manage UI over the ingested corpus.

Run: uvicorn doccat.api:app --host 0.0.0.0 --port 8000
"""
import os
import re
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

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
                 "Use <b>Add document</b> up top — it lands in the catalog within a minute.</div>"
                 if not (q or status or tag) else
                 "<div class=empty><b>No matches</b>Try a different term or clear the filter.</div>")

    body = (
        "<div class=wrap>"
        + _rail(status, tag)
        + "<main><div class=titlerow><div>"
        + f"<h1 class=title>{heading}</h1>"
        + f"<span class=count>{len(docs)} document{'s' if len(docs)!=1 else ''}</span></div>"
        + "<label class=refresh><input type=checkbox id=autoref>"
          "<span>Auto-refresh</span></label></div>"
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

    prov = _rows("SELECT source, source_ref, sender, subject, received_at, created_at"
                 " FROM source_event WHERE blob_sha=%s ORDER BY created_at", (d["sha"],))
    pages = _rows("SELECT page_no, engine, text FROM page WHERE document_id=%s ORDER BY page_no",
                  (doc_id,))
    label, cls = ui.status_bits(d["status"])
    accounts = {a["id"]: a["email"] for a in
                _rows("SELECT id, email FROM account WHERE provider='gmail'")}

    def _prov_li(p):
        when = (p["received_at"] or p["created_at"]).strftime("%Y-%m-%d %H:%M")
        src = p["source"]
        bits = [f"<span class='src {ui.esc(src)}'>{ui.esc(src)}</span>"]
        if src == "gmail":
            # source_ref = gmail:<account_id>:<message_id>:<part_id>
            parts = (p["source_ref"] or "").split(":")
            acct = accounts.get(int(parts[1])) if len(parts) > 1 and parts[1].isdigit() else None
            if acct:
                bits.append(f"<span class=to>to {ui.esc(acct)}</span>")
            if p["sender"]:
                bits.append(f"<span class=frm>from {ui.esc(p['sender'])}</span>")
            if p["subject"]:
                bits.append(f"<span class=subj>“{ui.esc(p['subject'])}”</span>")
        else:
            bits.append(f"<span class=mono>{ui.esc(p['source_ref'])}</span>")
        return (f"<li><span class=when>{when}</span>"
                f"<span class=pv>{''.join(bits)}</span></li>")

    prov_html = "".join(_prov_li(p) for p in prov)
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
    # tag picker: taxonomy tags as toggle chips (no typos); custom field for the rest
    applied = set(d["tags"] or [])
    tax = classify.taxonomy_tags()
    known = {c for c, _ in tax} | {s for _, ss in tax for s in ss}
    extra = [t for t in (d["tags"] or []) if t not in known]

    def _chip(tag, label):
        on = " on" if tag in applied else ""
        return (f"<button type=button class='tagopt{on}' data-tag=\"{ui.esc(tag)}\">"
                f"{ui.esc(label)}</button>")

    groups_html = ""
    for cat, subs in tax:
        sel = [t for t in ([cat] + subs) if t in applied]
        badge = f"<span class=tgcount>{len(sel)}</span>" if sel else ""
        chips = _chip(cat, cat) + "".join(_chip(s, s.split(":", 1)[1]) for s in subs)
        # categories that already carry tags open so they're visible/easy to fix;
        # empty ones stay collapsed and out of the way.
        groups_html += (
            f"<details class=taggroup{' open' if sel else ''}>"
            f"<summary>{ui.esc(cat)}{badge}</summary>"
            f"<div class=tgchips>{chips}</div></details>")
    tag_field = (
        "<div class=field><label>Tags</label>"
        f"<div class=tagpick id=f_tags>{groups_html}</div>"
        "<input id=f_extra class=tagextra autocomplete=off "
        "placeholder='+ custom tags, comma-separated' "
        f"value=\"{ui.esc(', '.join(extra))}\"></div>"
    )

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
          <div class=act style="margin-top:.8rem;flex-wrap:wrap">
            <a class='btn ghost' href='/doc/{d['id']}/raw' target=_blank>View original</a>
            <button class='btn ghost' onclick="reprocess({d['id']},'text')">Re-run text</button>
            <button class='btn ghost' onclick="reprocess({d['id']},'ocr')">Re-run OCR</button>
            <button class='btn ghost' onclick="reprocess({d['id']},'embed')">Re-tag</button>
            <button class='btn ghost' onclick="reprocess({d['id']},'embed_pages')" title="Embed each page for page-level semantic search">Embed pages</button>
            <button class='btn danger' onclick="del({d['id']})">Delete</button>
            <span class=saved id=act_msg></span>
          </div>

          <div class=section>
            <p class=eyebrow>Manage</p>
            <div class=field><label>Title</label>
              <input id=f_title value="{ui.esc(d['title'])}"></div>
            <div class=field><label>Type</label>
              <input id=f_type placeholder="e.g. tax · statement · medical" value="{ui.esc(d['doc_type'] or '')}"></div>
            <div class=field><label>Status</label>
              <select id=f_status>{opts}</select></div>
            {tag_field}
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
    document.getElementById('f_tags').addEventListener('click',function(e){{
      const b=e.target.closest('.tagopt'); if(b) b.classList.toggle('on');
    }});
    async function save(id){{
      const picked=[...document.querySelectorAll('#f_tags .tagopt.on')].map(b=>b.dataset.tag);
      const extra=document.getElementById('f_extra').value.split(',').map(s=>s.trim()).filter(Boolean);
      const body={{title:f_title.value,doc_type:f_type.value||null,
        status:f_status.value,
        tags:[...new Set([...picked,...extra])]}};
      const r=await fetch('/api/doc/'+id,{{method:'POST',
        headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});
      const s=document.getElementById('saved');
      if(r.ok){{s.textContent='Saved';s.classList.add('show');setTimeout(()=>s.classList.remove('show'),1600);}}
      else{{s.textContent='Save failed';s.classList.add('show');}}
    }}
    async function reprocess(id,stage){{
      const m=document.getElementById('act_msg');
      const r=await fetch('/api/doc/'+id+'/reprocess',{{method:'POST',
        headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{stage:stage}})}});
      m.textContent=r.ok?('Queued '+stage):'Failed';m.classList.add('show');
      setTimeout(()=>m.classList.remove('show'),2000);
    }}
    async function del(id){{
      if(!confirm('Delete this document, its text, and its stored file? This cannot be undone.'))return;
      const r=await fetch('/api/doc/'+id+'/delete',{{method:'POST'}});
      if(r.ok){{location.href='/';}}
      else{{const m=document.getElementById('act_msg');m.textContent='Delete failed';m.classList.add('show');}}
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
    return {"accounts": accounts, "jobs": jobs, "sources": sources,
            "failures": failures, "documents": docs["n"] if docs else 0}


@app.get("/api/status")
def api_status():
    return _status_data()


_JOB_DOT = {"done": "ok", "failed": "warn", "running": "run", "pending": "idle"}

_RULE_JS = """
<script>
async function _rule(path, body){
  const r = await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)});
  if(r.ok){location.reload();} else {alert('Rule update failed');}
}
function addRule(id){
  const p=document.getElementById('rp'+id).value.trim(); if(!p) return;
  _rule('/api/sender-rule',{account_id:id,pattern:p,
    action:document.getElementById('rq'+id).value});
}
function delRule(id,pattern,action){
  _rule('/api/sender-rule/delete',{account_id:id,pattern:pattern,action:action});
}
</script>
"""


@app.get("/status", response_class=HTMLResponse)
def status_page():
    d = _status_data()

    if d["accounts"]:
        cards = []
        for a in d["accounts"]:
            rules = _rows("SELECT pattern, action FROM sender_rule WHERE account_id=%s"
                          " ORDER BY action, pattern", (a["id"],))
            chips = "".join(
                f"<span class='rule {r['action']}'>{ui.esc(r['pattern'])}"
                f"<span class=ra>{r['action']}</span>"
                f"<button class=rx title=remove onclick=\"delRule({a['id']},"
                f"'{ui.esc(r['pattern'])}','{r['action']}')\">×</button></span>"
                for r in rules) or "<span class=m>no rules — all senders ingested</span>"
            synced = ("synced " + a["last_full_sync_at"].strftime("%Y-%m-%d %H:%M")
                      if a["last_full_sync_at"] else "never synced")
            cards.append(
                "<div class=acct>"
                "<div class=acctrow>"
                f"<span class=em>{ui.esc(a['email'])}</span>"
                f"<span class=m>{a['attachments']} attachments</span>"
                f"<span class=m>{synced}</span>"
                f"<span class='chip {'s-ok' if a['synced'] else 's-muted'}'>"
                f"{'active' if a['status']=='active' else ui.esc(a['status'])}</span>"
                "</div>"
                "<div class=rules><p class=eyebrow>Sender rules</p>"
                f"<div class=rulelist>{chips}</div>"
                "<div class=ruleadd>"
                f"<input id=rp{a['id']} placeholder='sender contains… e.g. chase.com'>"
                f"<select id=rq{a['id']}><option value=allow>allow</option>"
                "<option value=deny>deny</option></select>"
                f"<button class=btn onclick='addRule({a['id']})'>Add</button></div>"
                "<p class=upnote>No rules ingest every sender. Any <b>allow</b> rule "
                "means only matching senders are ingested; a <b>deny</b> always "
                "excludes. Matching is case-insensitive substring on the From header."
                "</p></div></div>")
        acct_html = "".join(cards) + _RULE_JS
    else:
        acct_html = ("<div class=empty><b>No Gmail accounts connected</b>"
                     "Mount a token secret (doccat-gmail) and the worker registers "
                     "accounts on its next poll.</div>")

    src = {s["source"]: s["n"] for s in d["sources"]}
    stats = (
        "<div class=statgrid>"
        f"<div class=stat><div class=k>Documents</div><div class=v>{d['documents']}</div></div>"
        f"<div class=stat><div class=k>From upload</div><div class=v>{src.get('upload',0)}</div>"
        "<div class=sub>source events</div></div>"
        f"<div class=stat><div class=k>From gmail</div><div class=v>{src.get('gmail',0)}</div>"
        "<div class=sub>source events</div></div>"
        "</div>")

    if d["jobs"]:
        by_stage = {}
        for j in d["jobs"]:
            by_stage.setdefault(j["stage"], {})[j["state"]] = j["n"]
        order = ["pending", "running", "done", "failed"]
        cards = []
        for stage in sorted(by_stage):
            states = by_stage[stage]
            total = sum(states.values())
            pills = "".join(
                f"<div class='qs {_JOB_DOT.get(st, 'idle')}'>"
                f"<span class=qn>{states[st]}</span><span class=ql>{st}</span></div>"
                for st in order if st in states)
            cards.append(
                f"<div class=qcard><div class=qhead>"
                f"<span class=qstage>{ui.esc(stage)}</span>"
                f"<span class=qtot>{total}</span></div>"
                f"<div class=qstates>{pills}</div></div>")
        jobs_html = "<div class=qgrid>" + "".join(cards) + "</div>"
    else:
        jobs_html = "<p class=count>No jobs yet.</p>"

    if d["failures"]:
        frows = "".join(
            "<tr>"
            f"<td class=mono>#{f['id']}</td>"
            f"<td class=mono>{ui.esc(f['stage'])}</td>"
            f"<td>{ui.esc(f['title'])}</td>"
            f"<td class=mono>{ui.esc(f['error'])}</td></tr>"
            for f in d["failures"])
        fails_html = ("<div class=section><p class=eyebrow>Recent failures</p>"
                      "<table class=qtable><thead><tr><th>Job</th><th>Stage</th>"
                      "<th>Document</th><th>Error</th></tr></thead><tbody>"
                      + frows + "</tbody></table></div>")
    else:
        fails_html = ""

    body = (
        "<div class=wrap style='grid-template-columns:1fr'><main>"
        "<div class=titlerow><div><h1 class=title>Status</h1>"
        "<span class=count>ingestion &amp; pipeline health</span></div>"
        "<label class=refresh><input type=checkbox id=autoref>"
        "<span>Auto-refresh</span></label></div>"
        f"{stats}"
        "<div class=section><p class=eyebrow>Job queue</p>" + jobs_html + "</div>"
        "<div class=section><p class=eyebrow>Gmail accounts</p>" + acct_html + "</div>"
        f"{fails_html}"
        "</main></div>")
    return ui.shell("Status", body)


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
