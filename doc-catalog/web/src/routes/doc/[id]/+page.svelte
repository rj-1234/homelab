<script>
  import { onMount, untrack } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { status } from '$lib/status.js';
  import { getDoc, docFields, updateDoc, reprocessDoc, deleteDoc, getTaxonomy } from '$lib/api.js';
  import { intoGroups } from '$lib/fields.js';
  import { fmtBytes, fmtDate } from '$lib/docmeta.js';
  import FieldCard from '$lib/FieldCard.svelte';
  import PipelineStrip from '$lib/PipelineStrip.svelte';
  import Icon from '$lib/Icon.svelte';

  const id = $derived($page.params.id);

  let doc = $state(null);
  let provenance = $state([]);
  let pagesText = $state([]);
  let fields = $state([]);
  let jobs = $state([]);
  let loading = $state(true);
  let notFound = $state(false);
  let error = $state('');

  async function load(currentId) {
    loading = true;
    notFound = false;
    error = '';
    try {
      const [detail, f] = await Promise.all([getDoc(currentId), docFields(currentId)]);
      doc = detail.doc;
      provenance = detail.provenance ?? [];
      pagesText = detail.pages ?? [];
      fields = f ?? [];
      jobs = detail.jobs ?? [];
    } catch (e) {
      const msg = String(e.message ?? e);
      if (/-> 404$/.test(msg)) notFound = true;
      else error = msg;
    } finally {
      loading = false;
    }
  }

  // Re-pull the whole detail (doc + jobs + provenance + text + fields) WITHOUT
  // the loading spinner, so job transitions and freshly-extracted text/fields
  // appear in place. Used both after an action (instant feedback) and reactively
  // when an SSE change arrives.
  let liveBusy = false; // plain flag (not $state) so it never re-triggers effects
  async function refresh(currentId) {
    if (liveBusy) return;
    liveBusy = true;
    try {
      const [detail, f] = await Promise.all([getDoc(currentId), docFields(currentId)]);
      doc = detail.doc;
      provenance = detail.provenance ?? [];
      pagesText = detail.pages ?? [];
      fields = f ?? [];
      jobs = detail.jobs ?? [];
    } catch { /* best-effort; UI keeps last known state */ }
    finally { liveBusy = false; }
  }

  $effect(() => { load(id); });

  // Realtime: the SSE status store ticks on every job/document change (Postgres
  // NOTIFY, see migration 006). Re-pull the current doc on each tick so the
  // pipeline pill flips active→done, and Save/worker updates land, without a
  // manual refresh. `untrack` keeps `$status` the sole trigger — reading the
  // guards reactively would re-fire the effect when refresh() mutates state.
  $effect(() => {
    $status; // subscribe: re-run whenever a change snapshot arrives
    untrack(() => {
      if (loading || notFound || !doc) return;
      refresh(id);
    });
  });

  const groups = $derived(intoGroups(fields));
  const unconfirmed = $derived(fields.filter((f) => !f.confirmed).length);

  // --- taxonomy + manage form ---
  let taxonomy = $state(null);
  onMount(async () => {
    try { taxonomy = await getTaxonomy(); } catch { /* best-effort */ }
  });

  let title = $state('');
  let docType = $state('');
  let statusSel = $state('');
  let selectedTags = $state([]);
  let customTagsInput = $state('');

  // (Re)seed the manage form whenever the doc or taxonomy changes — both are
  // needed to split doc.tags into "known" chips vs. free-text custom tags.
  $effect(() => {
    if (!doc) return;
    title = doc.title ?? '';
    docType = doc.doc_type ?? '';
    statusSel = doc.status ?? '';
    const known = new Set((taxonomy?.tags ?? []).flatMap((c) => [c.category, ...c.subtags]));
    const docTags = doc.tags ?? [];
    selectedTags = docTags.filter((t) => known.has(t));
    customTagsInput = docTags.filter((t) => !known.has(t)).join(', ');
  });

  function subLabel(s) {
    const i = s.indexOf(':');
    return i === -1 ? s : s.slice(i + 1);
  }

  function toggleChip(v) {
    selectedTags = selectedTags.includes(v)
      ? selectedTags.filter((t) => t !== v)
      : [...selectedTags, v];
  }

  // --- toast ---
  let toast = $state('');
  let toastKind = $state('ok'); // 'ok' | 'err'
  let toastTimer;
  function flash(msg, kind = 'ok') {
    toast = msg;
    toastKind = kind;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast = ''), 3200);
  }

  // --- actions ---
  let busyStage = $state(null); // 'text' | 'ocr' | 'embed' | 'embed_pages' | null
  async function doReprocess(stage) {
    busyStage = stage;
    try {
      await reprocessDoc(id, stage);
      flash(`Queued ${stage}`);
      await refresh(id);
    } catch (e) {
      flash(`Couldn’t queue ${stage}: ${String(e.message ?? e)}`, 'err');
    } finally {
      busyStage = null;
    }
  }

  let busyDelete = $state(false);
  async function doDelete() {
    if (!confirm('Delete this document and its file? This cannot be undone.')) return;
    busyDelete = true;
    try {
      await deleteDoc(id);
      goto('/library');
    } catch (e) {
      flash(`Delete failed: ${String(e.message ?? e)}`, 'err');
      busyDelete = false;
    }
  }

  let busySave = $state(false);
  async function doSave() {
    busySave = true;
    try {
      const custom = customTagsInput.split(',').map((s) => s.trim()).filter(Boolean);
      const tags = Array.from(new Set([...selectedTags, ...custom]));
      await updateDoc(id, { title, doc_type: docType.trim() || null, status: statusSel, tags });
      flash('Saved');
      await refresh(id);
    } catch (e) {
      flash(`Save failed: ${String(e.message ?? e)}`, 'err');
    } finally {
      busySave = false;
    }
  }
</script>

<main class="wrap">
  <a class="back mono" href="/library"><Icon name="arrow-left" size="15px" /> Library</a>

  {#if loading}
    <p class="muted">Loading document…</p>
  {:else if notFound}
    <div class="empty card">
      <h2>Document not found</h2>
      <p class="muted">It may have been deleted. <a href="/library">Back to the library →</a></p>
    </div>
  {:else if error}
    <p class="stamp">Couldn’t load this document: {error}</p>
  {:else if doc}
    <header class="dhead">
      <h1>{doc.title || 'Untitled document'}</h1>
      <div class="meta mono muted">
        #{doc.id}{#if doc.mime} · {doc.mime}{/if}{#if doc.size != null} · {fmtBytes(doc.size)}{/if}{#if doc.pages != null} · {doc.pages} page{doc.pages === 1 ? '' : 's'}{/if}{#if doc.created_at} · {fmtDate(doc.created_at)}{/if}{#if doc.status} · {doc.status}{/if}
      </div>

      {#if doc.tags?.length}
        <div class="tags">
          {#each doc.tags as t}<span class="tag">{t}</span>{/each}
        </div>
      {/if}
    </header>

    <PipelineStrip {jobs} status={doc.status} hasPages={pagesText.length > 0} />

    <div class="actions-row">
      <a class="btn ghost" href={`/api/doc/${doc.id}/raw`} target="_blank" rel="noopener">
        <Icon name="external-link" size="15px" /> View original
      </a>
      <button class="btn ghost" onclick={() => doReprocess('text')} disabled={busyStage === 'text'}>
        <Icon name="refresh" size="15px" /> {busyStage === 'text' ? 'Queuing…' : 'Re-run text'}
      </button>
      <button class="btn ghost" onclick={() => doReprocess('ocr')} disabled={busyStage === 'ocr'}>
        <Icon name="refresh" size="15px" /> {busyStage === 'ocr' ? 'Queuing…' : 'Re-run OCR'}
      </button>
      <button class="btn ghost" onclick={() => doReprocess('embed_pages')} disabled={busyStage === 'embed_pages'}>
        <Icon name="refresh" size="15px" /> {busyStage === 'embed_pages' ? 'Queuing…' : 'Embed pages'}
      </button>
      <button class="btn primary" onclick={() => doReprocess('embed')} disabled={busyStage === 'embed'}>
        <Icon name="tag" size="15px" /> {busyStage === 'embed' ? 'Queuing…' : 'Re-tag'}
      </button>
      <button class="btn danger" onclick={doDelete} disabled={busyDelete}>
        <Icon name="trash" size="15px" /> {busyDelete ? 'Deleting…' : 'Delete'}
      </button>
    </div>

    {#if toast}
      <p class="toast mono" class:err={toastKind === 'err'}>{toast}</p>
    {/if}

    <details class="manage card">
      <summary class="mono">Manage</summary>
      <div class="manage-body">
        <label class="flabel mono">
          Title
          <input class="input" type="text" bind:value={title} />
        </label>

        <label class="flabel mono">
          Type
          <input class="input" type="text" placeholder="e.g. tax · statement · medical" bind:value={docType} />
        </label>

        <label class="flabel mono">
          Status
          <select class="input" bind:value={statusSel}>
            {#each taxonomy?.statuses ?? [] as s (s.key)}
              <option value={s.key}>{s.label}</option>
            {/each}
          </select>
        </label>

        <div class="tagpick">
          <span class="flabel mono">Tags</span>
          {#each taxonomy?.tags ?? [] as cat (cat.category)}
            <div class="catgroup">
              <button
                type="button"
                class="chip cat"
                class:on={selectedTags.includes(cat.category)}
                onclick={() => toggleChip(cat.category)}
              >{cat.category}</button>
              {#each cat.subtags as sub (sub)}
                <button
                  type="button"
                  class="chip"
                  class:on={selectedTags.includes(sub)}
                  onclick={() => toggleChip(sub)}
                >{subLabel(sub)}</button>
              {/each}
            </div>
          {/each}

          <label class="flabel mono custom">
            Custom tags (comma separated)
            <input class="input" type="text" bind:value={customTagsInput} placeholder="e.g. warranty, receipt" />
          </label>
        </div>

        <button class="btn primary save" onclick={doSave} disabled={busySave}>
          {busySave ? 'Saving…' : 'Save'}
        </button>
      </div>
    </details>

    <section class="block">
      <h2 class="eyebrow">Fields</h2>
      {#if fields.length === 0}
        <p class="muted">No fields extracted from this document.</p>
      {:else}
        {#if unconfirmed > 0}
          <p class="note muted">
            {unconfirmed} field{unconfirmed === 1 ? '' : 's'} awaiting confirmation —
            <a href="/review">review them →</a>
          </p>
        {/if}
        {#each groups as g}
          <div class="fgroup">
            <h3 class="gtitle mono">{g.title}</h3>
            <div class="fgrid">
              {#each g.fields as f (f.id)}
                <FieldCard field={f} />
              {/each}
            </div>
          </div>
        {/each}
      {/if}
    </section>

    {#if provenance.length}
      <section class="block">
        <h2 class="eyebrow">Provenance</h2>
        <div class="card prov-list">
          {#each provenance as p, i (i)}
            <div class="prov-row">
              <span class="src mono">{p.source}</span>
              <span class="prov-details muted">
                {#if p.sender}{p.sender} · {/if}{#if p.subject}“{p.subject}” · {/if}{#if p.received_at}recv {fmtDate(p.received_at)}{:else if p.created_at}added {fmtDate(p.created_at)}{/if}
              </span>
            </div>
          {/each}
        </div>
      </section>
    {/if}

    {#if pagesText.length}
      <section class="block">
        <h2 class="eyebrow">Text</h2>
        {#each pagesText as pg, i (pg.page_no ?? i)}
          <details open={i === 0} class="page-details">
            <summary class="mono">
              Page {pg.page_no ?? i + 1} · {pg.engine ?? 'unknown'} · {(pg.text ?? '').length} chars
            </summary>
            <pre class="ptext mono">{pg.text ?? ''}</pre>
          </details>
        {/each}
      </section>
    {/if}
  {/if}
</main>

<style>
  .back {
    display: inline-flex; align-items: center; gap: 6px; margin-bottom: var(--s-4);
    color: var(--muted); font-size: var(--t-sm);
  }
  .back:hover { color: var(--ink); text-decoration: none; }

  .dhead { margin-bottom: var(--s-5); padding-bottom: var(--s-4); border-bottom: 1px solid var(--line); }
  .dhead h1 { margin: 0 0 8px; font-size: var(--t-3); overflow-wrap: anywhere; }
  .meta { font-size: var(--t-sm); overflow-wrap: anywhere; }

  .tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
  .tag {
    font-family: var(--font-mono); font-size: 0.6875rem; color: var(--blue);
    background: var(--blue-wash);
    border: 1px solid color-mix(in srgb, var(--blue) 16%, var(--line));
    border-radius: var(--radius-pill); padding: 2px 9px;
  }

  .actions-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: var(--s-4); }

  .btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 40px;
    padding: 0 16px; border-radius: var(--radius-pill); font-size: var(--t-sm); font-weight: 500;
    border: 1px solid var(--line); background: var(--card); color: var(--ink);
    cursor: pointer; transition: border-color .15s ease, background .15s ease;
  }
  .btn:hover:not(:disabled) { text-decoration: none; border-color: color-mix(in srgb, var(--ink) 30%, var(--line)); }
  .btn:disabled { opacity: 0.55; cursor: default; }

  .btn.ghost { border-color: var(--line); color: var(--ink); background: var(--card); }

  .btn.primary { border-color: var(--blue); background: var(--blue); color: #fff; }
  .btn.primary:hover:not(:disabled) { filter: brightness(1.05); border-color: var(--blue); }

  .btn.danger { border-color: var(--stamp); color: var(--stamp); background: transparent; }
  .btn.danger:hover:not(:disabled) { background: color-mix(in srgb, var(--stamp) 10%, transparent); border-color: var(--stamp); }

  .toast { font-size: 12.5px; color: var(--teal); margin: 0 0 16px; }
  .toast.err { color: var(--stamp); }

  .manage { margin-bottom: 28px; padding: 0; overflow: hidden; }
  .manage summary {
    cursor: pointer; padding: 12px 16px; font-size: 12.5px; color: var(--muted);
    min-height: 40px; display: flex; align-items: center;
    text-transform: uppercase; letter-spacing: 0.06em;
  }
  .manage summary:hover { color: var(--ink); }
  .manage-body {
    padding: 16px; border-top: 1px solid var(--line);
    display: flex; flex-direction: column; gap: 14px;
  }

  .flabel {
    display: flex; flex-direction: column; gap: 6px;
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted);
  }
  .input {
    font-family: var(--font-body); font-size: 15px; color: var(--ink);
    background: var(--paper); border: 1px solid var(--line); border-radius: 8px;
    padding: 10px 12px; min-height: 40px; box-sizing: border-box; width: 100%;
  }
  .input:focus-visible { outline: 2px solid var(--blue); outline-offset: 1px; }

  .tagpick { display: flex; flex-direction: column; gap: 10px; }
  .catgroup { display: flex; flex-wrap: wrap; gap: 6px; }
  .custom { margin-top: 2px; }

  .chip {
    font-family: var(--font-mono); font-size: 12px; color: var(--muted);
    background: var(--card); border: 1px solid var(--line);
    border-radius: 999px; padding: 7px 12px; min-height: 36px;
    cursor: pointer; white-space: nowrap;
  }
  .chip.cat { font-weight: 600; color: var(--ink); }
  .chip:hover { border-color: var(--blue); }
  .chip.on {
    color: var(--ink); border-color: var(--blue);
    background: color-mix(in srgb, var(--blue) 16%, var(--card));
  }

  .save { align-self: flex-start; }

  .block { margin-bottom: 28px; }
  .gtitle {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--muted); margin: 0 0 12px; font-weight: 500;
  }
  .note { font-size: 13px; margin: 0 0 12px; }

  .fgroup { margin-bottom: 18px; }
  .fgroup .gtitle { font-size: 10px; margin-bottom: 8px; }
  .fgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--gap); }

  .prov-list { padding: 4px 0; max-height: 260px; overflow-y: auto; }
  .prov-row {
    display: flex; flex-direction: column; gap: 2px;
    padding: 10px 16px; border-bottom: 1px solid var(--line);
    font-size: 12.5px;
  }
  .prov-row:last-child { border-bottom: none; }
  .src { color: var(--blue); text-transform: uppercase; font-size: 10.5px; letter-spacing: 0.04em; }
  .prov-details { overflow-wrap: anywhere; }

  .page-details {
    background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
    margin-bottom: 10px; overflow: hidden;
  }
  .page-details summary {
    cursor: pointer; padding: 12px 16px; font-size: 12.5px; color: var(--muted);
    min-height: 40px; display: flex; align-items: center;
  }
  .page-details summary:hover { color: var(--ink); }
  .ptext {
    margin: 0; padding: 14px 16px; border-top: 1px solid var(--line);
    white-space: pre-wrap; word-break: break-word;
    font-size: 12.5px; line-height: 1.6;
    max-height: 420px; overflow: auto;
  }

  .empty { padding: 40px 28px; text-align: center; }
  .empty h2 { margin: 0 0 8px; font-size: 20px; }
</style>
