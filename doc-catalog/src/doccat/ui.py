"""Server-rendered UI: the "Registry" design system + render helpers.

Direction: a card-catalog / archival records office. Documents are index cards
with a status spine and a mono metadata line. Palette: cool paper, green-ink,
filing-teal, stamp-red. Type: Space Grotesk (display) / IBM Plex Sans (body) /
IBM Plex Mono (data). Light + dark. Fonts load in the viewer's browser only —
no document data leaves the tailnet.
"""
import html

# Human-facing status: (label, css-class, spine intent). Active-voice labels.
STATUS = {
    "ingested":       ("New",       "s-new"),
    "text_extracted": ("Indexed",   "s-ok"),
    "needs_ocr":      ("Needs OCR", "s-warn"),
    "no_text":        ("No text",   "s-muted"),
}

STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
:root{
  --paper:#FBFAF7; --card:#FFFFFF; --ink:#1A1D1A; --muted:#6B7169;
  --teal:#0E7C6B; --stamp:#B23A2E; --blue:#2F6D8F; --line:#E7E4DB; --line2:#CFCcC2;
  --shadow:0 1px 2px rgba(26,29,26,.05),0 6px 20px rgba(26,29,26,.04);
}
@media (prefers-color-scheme:dark){:root{
  --paper:#14160F; --card:#1C1F17; --ink:#EDEBE0; --muted:#9A9E90;
  --teal:#4FBFA8; --stamp:#E4796B; --blue:#7FB4CE; --line:#2C3025; --line2:#3C4133;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.25);
}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font:400 15px/1.55 'IBM Plex Sans',system-ui,sans-serif;
  -webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
.mono{font-family:'IBM Plex Mono',ui-monospace,monospace}

/* top bar */
header.bar{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--paper) 88%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.bar .in{max-width:1080px;margin:0 auto;padding:.85rem 1.25rem;display:flex;gap:1.25rem;align-items:center}
.brand{display:flex;align-items:center;gap:.6rem;font-family:'Space Grotesk';font-weight:700;
  font-size:1.02rem;letter-spacing:-.01em;white-space:nowrap}
.brand .glyph{display:inline-grid;place-items:center;width:26px;height:26px;border:1.5px solid var(--ink);
  border-radius:5px;font-size:.62rem;font-weight:700;transform:rotate(-4deg)}
.brand small{color:var(--muted);font-weight:500;font-family:'IBM Plex Mono';font-size:.72rem;
  letter-spacing:.02em;text-transform:uppercase}
form.search{flex:1;display:flex}
form.search input{flex:1;font:400 .95rem 'IBM Plex Sans';color:var(--ink);background:var(--card);
  border:1px solid var(--line2);border-radius:8px 0 0 8px;padding:.55rem .8rem;outline:none}
form.search input:focus{border-color:var(--teal);box-shadow:0 0 0 3px color-mix(in srgb,var(--teal) 18%,transparent)}
form.search button{font:600 .9rem 'Space Grotesk';background:var(--ink);color:var(--paper);
  border:1px solid var(--ink);border-radius:0 8px 8px 0;padding:0 1rem;cursor:pointer}

/* layout */
.wrap{max-width:1080px;margin:0 auto;padding:1.6rem 1.25rem 4rem;
  display:grid;grid-template-columns:200px 1fr;gap:1.8rem}
@media(max-width:720px){.wrap{grid-template-columns:1fr;gap:1rem}}
.rail{position:sticky;top:74px;align-self:start;display:flex;flex-direction:column;gap:1.3rem}
@media(max-width:720px){.rail{position:static}}
.eyebrow{font:500 .68rem/1 'IBM Plex Mono';letter-spacing:.11em;text-transform:uppercase;color:var(--muted);margin:0 0 .55rem}
.rail a{display:flex;justify-content:space-between;gap:.5rem;padding:.28rem 0;color:var(--muted);font-size:.9rem}
.rail a.on,.rail a:hover{color:var(--ink)}
.rail a .n{font-family:'IBM Plex Mono';font-size:.78rem;color:var(--muted)}

h1.title{font-family:'Space Grotesk';font-weight:700;font-size:1.5rem;letter-spacing:-.02em;margin:.1rem 0 .2rem}
.count{color:var(--muted);font-family:'IBM Plex Mono';font-size:.85rem}
.stack{display:flex;flex-direction:column;gap:.75rem;margin-top:1.1rem}

/* index card — the signature element */
.card{position:relative;background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:.85rem 1.05rem .85rem 1.35rem;box-shadow:var(--shadow);overflow:hidden;transition:border-color .15s}
.card:hover{border-color:var(--line2)}
.card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--muted)}
.card.s-ok::before{background:var(--teal)} .card.s-warn::before{background:var(--stamp)}
.card.s-new::before{background:var(--blue)} .card.s-muted::before{background:var(--line2)}
.card .row1{display:flex;align-items:baseline;gap:.6rem}
.card .doc{font-family:'Space Grotesk';font-weight:600;font-size:1.02rem;letter-spacing:-.01em;flex:1;min-width:0;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.card .doc:hover{color:var(--teal)}
.meta{font-family:'IBM Plex Mono';font-size:.74rem;color:var(--muted);margin-top:.3rem;
  display:flex;gap:.55rem;flex-wrap:wrap}
.meta b{color:var(--ink);font-weight:500}
.snip{color:var(--muted);font-size:.9rem;margin-top:.45rem;line-height:1.45}
.snip mark{background:color-mix(in srgb,var(--teal) 24%,transparent);color:inherit;padding:0 .12em;border-radius:2px}

.chip{font:500 .66rem/1 'IBM Plex Mono';letter-spacing:.05em;text-transform:uppercase;
  padding:.32em .5em;border-radius:5px;border:1px solid;white-space:nowrap}
.s-ok .chip,.chip.s-ok{color:var(--teal);border-color:color-mix(in srgb,var(--teal) 45%,var(--line))}
.s-warn .chip,.chip.s-warn{color:var(--stamp);border-color:color-mix(in srgb,var(--stamp) 45%,var(--line))}
.s-new .chip,.chip.s-new{color:var(--blue);border-color:color-mix(in srgb,var(--blue) 45%,var(--line))}
.s-muted .chip,.chip.s-muted{color:var(--muted);border-color:var(--line2)}
.tags{display:flex;gap:.35rem;flex-wrap:wrap;margin-top:.5rem}
.tag{font:500 .72rem 'IBM Plex Sans';color:var(--muted);background:color-mix(in srgb,var(--muted) 9%,transparent);
  border:1px solid var(--line);border-radius:20px;padding:.12em .6em}

.empty{border:1px dashed var(--line2);border-radius:10px;padding:2.2rem 1.5rem;text-align:center;color:var(--muted)}
.empty b{display:block;color:var(--ink);font-family:'Space Grotesk';font-size:1.05rem;margin-bottom:.3rem}

/* detail sheet */
.back{font-family:'IBM Plex Mono';font-size:.8rem;color:var(--muted)}
.back:hover{color:var(--ink)}
.sheet{background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);
  padding:1.5rem 1.6rem;margin-top:.7rem}
.sheet h1{font-family:'Space Grotesk';font-weight:700;font-size:1.45rem;letter-spacing:-.02em;margin:.2rem 0 .5rem}
.section{border-top:1px solid var(--line);margin-top:1.4rem;padding-top:1.2rem}
.prov{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:.5rem}
.prov li{font-size:.9rem;display:flex;gap:.7rem}
.prov .when{font-family:'IBM Plex Mono';font-size:.78rem;color:var(--muted);white-space:nowrap;padding-top:.15rem}
.prov .pv{display:flex;flex-wrap:wrap;gap:.4rem .55rem;align-items:baseline}
.prov .src{font:600 .6rem/1 'IBM Plex Mono';letter-spacing:.06em;text-transform:uppercase;
  padding:.28em .5em;border-radius:5px;border:1px solid var(--line2);color:var(--muted)}
.prov .src.gmail{color:var(--stamp);border-color:color-mix(in srgb,var(--stamp) 45%,var(--line))}
.prov .src.upload{color:var(--blue);border-color:color-mix(in srgb,var(--blue) 45%,var(--line))}
.prov .to{font-family:'IBM Plex Mono';font-size:.78rem;color:var(--teal)}
.prov .frm{font-size:.85rem;color:var(--ink)}
.prov .subj{font-size:.85rem;color:var(--muted);font-style:italic}
details.page{border:1px solid var(--line);border-radius:8px;margin-top:.5rem;background:var(--paper)}
details.page>summary{cursor:pointer;padding:.55rem .8rem;font-family:'IBM Plex Mono';font-size:.8rem;color:var(--muted)}
details.page[open]>summary{color:var(--ink);border-bottom:1px solid var(--line)}
details.page pre{margin:0;padding:.8rem;white-space:pre-wrap;font:400 .82rem/1.5 'IBM Plex Mono';max-height:340px;overflow:auto}
.field{display:flex;flex-direction:column;gap:.3rem;margin-bottom:.85rem}
.field label{font:500 .68rem/1 'IBM Plex Mono';letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.field input,.field select{font:400 .92rem 'IBM Plex Sans';color:var(--ink);background:var(--paper);
  border:1px solid var(--line2);border-radius:7px;padding:.5rem .65rem;outline:none}
.field input:focus,.field select:focus{border-color:var(--teal);box-shadow:0 0 0 3px color-mix(in srgb,var(--teal) 16%,transparent)}
.act{display:flex;gap:.6rem;align-items:center;margin-top:.4rem}
.btn{font:600 .88rem 'Space Grotesk';background:var(--teal);color:#fff;border:none;border-radius:7px;padding:.55rem 1.1rem;cursor:pointer}
.btn.ghost{background:transparent;color:var(--muted);border:1px solid var(--line2)}
.btn.danger{background:transparent;color:var(--stamp);border:1px solid color-mix(in srgb,var(--stamp) 45%,var(--line2))}
.btn.danger:hover{background:color-mix(in srgb,var(--stamp) 10%,transparent)}
.saved{color:var(--teal);font-family:'IBM Plex Mono';font-size:.8rem;opacity:0;transition:opacity .2s}
.saved.show{opacity:1}

/* add-document button + upload dialog */
.add{font:600 .85rem 'Space Grotesk';background:var(--card);color:var(--ink);border:1px solid var(--line2);
  border-radius:8px;padding:.55rem .85rem;cursor:pointer;white-space:nowrap}
.add:hover{border-color:var(--teal);color:var(--teal)}
/* phone: brand + Add on row one, search stretches to its own row below */
@media(max-width:560px){
  .bar .in{flex-wrap:wrap;gap:.55rem .75rem;padding:.7rem .95rem}
  .brand{order:1} .brand small{display:none}
  .add{order:2;margin-left:auto}
  form.search{order:3;flex-basis:100%}
}
dialog.up{border:1px solid var(--line2);border-radius:14px;padding:0;max-width:460px;width:92vw;
  background:var(--card);color:var(--ink);box-shadow:0 24px 64px rgba(0,0,0,.34)}
dialog.up::backdrop{background:rgba(10,12,8,.45);backdrop-filter:blur(2px)}
.up form{padding:1.3rem 1.4rem 1.2rem}
.uphead{display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem}
.uphead b{font-family:'Space Grotesk';font-size:1.12rem}
.up .x{background:none;border:none;color:var(--muted);font-size:1.05rem;cursor:pointer;line-height:1}
.drop{display:grid;place-items:center;text-align:center;min-height:118px;padding:1rem;cursor:pointer;
  border:1.5px dashed var(--line2);border-radius:10px;background:var(--paper);color:var(--muted);transition:.15s}
.drop:hover,.drop.over{border-color:var(--teal);color:var(--ink);
  background:color-mix(in srgb,var(--teal) 6%,var(--paper))}
.drop u{color:var(--teal)}
.uplist{list-style:none;margin:.8rem 0 0;padding:0;display:flex;flex-direction:column;gap:.3rem;max-height:150px;overflow:auto}
.uplist li{font:400 .8rem 'IBM Plex Mono';display:flex;justify-content:space-between;gap:.6rem;color:var(--ink);
  border:1px solid var(--line);border-radius:6px;padding:.35rem .6rem}
.uplist li span{color:var(--muted);white-space:nowrap}
.upact{display:flex;gap:.6rem;justify-content:flex-end;margin-top:1.1rem}
.upnote{font:400 .74rem/1.45 'IBM Plex Sans';color:var(--muted);margin:.9rem 0 0}

/* status page */
.navlink{font:600 .85rem 'Space Grotesk';color:var(--muted);white-space:nowrap}
.navlink:hover{color:var(--teal)}
.statgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.8rem;margin-top:.6rem}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.9rem 1rem;box-shadow:var(--shadow)}
.stat .k{font:500 .64rem/1 'IBM Plex Mono';letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.stat .v{font-family:'Space Grotesk';font-weight:700;font-size:1.55rem;margin-top:.35rem;letter-spacing:-.02em}
.stat .sub{font:400 .75rem 'IBM Plex Mono';color:var(--muted);margin-top:.15rem}
.acct{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:.85rem 1rem;box-shadow:var(--shadow);margin-top:.6rem}
.acctrow{display:flex;align-items:center;gap:.8rem;flex-wrap:wrap}
.acct .em{font-family:'Space Grotesk';font-weight:600;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}
.acct .m{font:400 .78rem 'IBM Plex Mono';color:var(--muted)}
.rules{border-top:1px solid var(--line);margin-top:.8rem;padding-top:.7rem}
.rulelist{display:flex;gap:.4rem;flex-wrap:wrap;margin:.1rem 0 .7rem}
.rule{display:inline-flex;align-items:center;gap:.4rem;font:500 .78rem 'IBM Plex Mono';
  border:1px solid var(--line2);border-radius:20px;padding:.15em .3em .15em .7em}
.rule.allow{color:var(--teal);border-color:color-mix(in srgb,var(--teal) 45%,var(--line))}
.rule.deny{color:var(--stamp);border-color:color-mix(in srgb,var(--stamp) 45%,var(--line))}
.rule .ra{font-size:.62rem;text-transform:uppercase;letter-spacing:.06em;opacity:.7}
.rule .rx{background:none;border:none;color:inherit;cursor:pointer;font-size:1rem;line-height:1;opacity:.6;padding:0 .1em}
.rule .rx:hover{opacity:1}
.ruleadd{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center}
.ruleadd input{flex:1;min-width:180px;font:400 .88rem 'IBM Plex Sans';color:var(--ink);background:var(--paper);
  border:1px solid var(--line2);border-radius:7px;padding:.45rem .6rem;outline:none}
.ruleadd input:focus{border-color:var(--teal);box-shadow:0 0 0 3px color-mix(in srgb,var(--teal) 16%,transparent)}
.ruleadd select{font:400 .88rem 'IBM Plex Sans';color:var(--ink);background:var(--paper);
  border:1px solid var(--line2);border-radius:7px;padding:.45rem .5rem}
.ruleadd .btn{padding:.45rem .9rem}
.qtable{width:100%;border-collapse:collapse;margin-top:.6rem;font-size:.88rem}
.qtable th,.qtable td{text-align:left;padding:.45rem .6rem;border-bottom:1px solid var(--line)}
.qtable th{font:500 .64rem/1 'IBM Plex Mono';letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.qtable td.num{font-family:'IBM Plex Mono';text-align:right}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:.45rem;vertical-align:middle}
.dot.ok{background:var(--teal)} .dot.warn{background:var(--stamp)}
.dot.run{background:var(--blue)} .dot.idle{background:var(--line2)}
"""

# Injected once per page by shell(); the <dialog> the "+ Add document" button opens.
_UPLOAD = """
<dialog id=up class=up>
  <form id=upform>
    <div class=uphead><b>Add to the Registry</b>
      <button type=button class=x onclick="document.getElementById('up').close()">✕</button></div>
    <label class=drop id=updrop>
      <input type=file id=upfiles multiple hidden>
      <span id=uphint>Drop files here, or <u>browse</u></span>
    </label>
    <ul id=uplist class=uplist></ul>
    <div class=upact>
      <button type=button class='btn ghost' onclick="document.getElementById('up').close()">Cancel</button>
      <button type=submit class=btn id=upbtn>Upload</button>
    </div>
    <p class=upnote>Files land in the catalog within a minute — dedupe and text
      extraction run automatically. Uploading a file already on record just adds
      provenance; it is not stored twice.</p>
  </form>
</dialog>
<script>
(function(){
  var dlg=document.getElementById('up'); if(!dlg) return;
  var inp=document.getElementById('upfiles'), drop=document.getElementById('updrop'),
      list=document.getElementById('uplist'), form=document.getElementById('upform'),
      btn=document.getElementById('upbtn'), hint=document.getElementById('uphint');
  function kb(n){return n<1024?n+' B':(n<1048576?(n/1024|0)+' KB':(n/1048576).toFixed(1)+' MB');}
  function render(){
    list.innerHTML=[].map.call(inp.files,function(f){
      return '<li><span class=fn>'+f.name+'</span><span>'+kb(f.size)+'</span></li>';}).join('');
  }
  inp.addEventListener('change',render);
  ['dragover','dragenter'].forEach(function(e){drop.addEventListener(e,function(ev){
    ev.preventDefault();drop.classList.add('over');});});
  ['dragleave','drop'].forEach(function(e){drop.addEventListener(e,function(ev){
    ev.preventDefault();drop.classList.remove('over');});});
  drop.addEventListener('drop',function(ev){inp.files=ev.dataTransfer.files;render();});
  dlg.addEventListener('close',function(){inp.value='';list.innerHTML='';
    btn.disabled=false;btn.textContent='Upload';});
  form.addEventListener('submit',function(ev){
    ev.preventDefault();
    if(!inp.files.length){drop.classList.add('over');return;}
    var fd=new FormData();
    [].forEach.call(inp.files,function(f){fd.append('files',f);});
    btn.disabled=true;btn.textContent='Uploading…';
    fetch('/api/upload',{method:'POST',body:fd}).then(function(r){
      if(r.ok){location.reload();}
      else{btn.textContent='Failed — retry';btn.disabled=false;}
    }).catch(function(){btn.textContent='Failed — retry';btn.disabled=false;});
  });
})();
</script>
"""


def esc(s):
    return html.escape(str(s) if s is not None else "")


def status_bits(status):
    return STATUS.get(status, (status or "—", "s-muted"))


def shell(title, body, q=""):
    return (
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{esc(title)} · Registry</title><style>{STYLE}</style></head><body>"
        "<header class=bar><div class=in>"
        "<a class=brand href=/><span class=glyph>DC</span>The Registry"
        "<small>doc&nbsp;catalog</small></a>"
        f"<form class=search method=get action=/>"
        f"<input name=q placeholder='Search the catalog…' value=\"{esc(q)}\" autocomplete=off>"
        "<button>Search</button></form>"
        "<a class=navlink href=/status>Status</a>"
        "<button class=add type=button onclick=\"document.getElementById('up').showModal()\">"
        "+ Add document</button>"
        "</div></header>"
        f"{body}{_UPLOAD}</body></html>"
    )


def hl(snippet):
    return (
        esc(snippet).replace("@@HL@@", "<mark>").replace("@@EHL@@", "</mark>")
        if snippet else ""
    )


def card(d):
    label, cls = status_bits(d["status"])
    sha = (d.get("sha") or "")[:12]
    meta = (
        f"<span class=mono>#{d['id']}</span>"
        f"<span>{esc(sha)}</span>"
        f"<span>{esc(d['mime'])}</span>"
        f"<span>{d['created_at']:%Y-%m-%d}</span>"
        + (f"<span><b>{d['pages']}</b>&nbsp;pp</span>" if d.get("pages") else "")
    )
    snip = f"<div class=snip>{hl(d.get('snippet'))}</div>" if d.get("snippet") else ""
    chips = ""
    if d.get("doc_type"):
        chips += f"<span class=tag>{esc(d['doc_type'])}</span>"
    chips += "".join(f"<span class=tag>{esc(t)}</span>" for t in (d.get("tags") or []))
    tagrow = f"<div class=tags>{chips}</div>" if chips else ""
    return (
        f"<a class='card {cls}' href='/doc/{d['id']}'>"
        f"<div class=row1><span class=doc>{esc(d['title'])}</span>"
        f"<span class=chip>{esc(label)}</span></div>"
        f"<div class=meta>{meta}</div>{snip}{tagrow}"
        "</a>"
    )
