<script>
  import { onMount } from 'svelte';
  import { status } from '$lib/status.js';
  import { listDocuments } from '$lib/api.js';
  import JobQueue from '$lib/JobQueue.svelte';

  let docs = $state([]);
  let loading = $state(true);
  let error = $state('');
  let q = $state('');

  async function load() {
    loading = true; error = '';
    try { docs = await listDocuments(q); }
    catch (e) { error = String(e.message ?? e); }
    finally { loading = false; }
  }
  onMount(load);

  // documents count is pushed live over SSE; fall back to the fetched list
  let count = $derived($status?.documents ?? docs.length);
</script>

<main class="wrap">
  <div class="stats">
    <div class="stat card">
      <div class="n">{count}</div>
      <div class="l mono">documents</div>
    </div>
    {#each ($status?.sources ?? []) as s}
      <div class="stat card">
        <div class="n">{s.n}</div>
        <div class="l mono">{s.source}</div>
      </div>
    {/each}
  </div>

  <JobQueue />

  <div class="reg">
    <div class="head">
      <h2>Registry</h2>
      <form onsubmit={(e) => { e.preventDefault(); load(); }} class="search">
        <input class="mono" placeholder="search…" bind:value={q} />
      </form>
    </div>

    {#if loading}
      <p class="muted">Loading…</p>
    {:else if error}
      <p class="stamp">Couldn’t load documents: {error}</p>
    {:else if docs.length === 0}
      <p class="muted">No documents yet.</p>
    {:else}
      <ul class="docs">
        {#each docs as d}
          <li class="doc card">
            <div class="main">
              <a class="dtitle" href={`/doc/${d.id}`}>{d.title || `#${d.id}`}</a>
              <div class="tags">
                {#each (d.tags ?? []) as t}<span class="tag mono">{t}</span>{/each}
              </div>
            </div>
            <div class="meta mono muted">
              <span class="st st-{d.status}">{d.status}</span>
              <span>{d.pages ?? 0}p</span>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</main>

<style>
  .stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: var(--gap); margin-bottom: 24px; }
  .stat { padding: 16px; }
  .stat .n { font-family: var(--font-display); font-size: 28px; font-weight: 600; }
  .stat .l { font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin-top: 2px; }

  .reg { margin-top: 28px; }
  .head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 12px; }
  .head h2 { margin: 0; font-size: 16px; }
  .search input { font-size: 13px; padding: 7px 12px; border: 1px solid var(--line); border-radius: 999px; background: var(--card); color: var(--ink); }

  .docs { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
  .doc { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 12px 16px; }
  .dtitle { font-weight: 500; color: var(--ink); }
  .dtitle:hover { color: var(--teal); }
  .tags { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }
  .tag { font-size: 11px; padding: 2px 7px; border-radius: 999px; border: 1px solid var(--line); color: var(--muted); }
  .meta { display: flex; align-items: center; gap: 12px; font-size: 12px; white-space: nowrap; }
  .st { padding: 2px 8px; border-radius: 999px; border: 1px solid var(--line); }
  .st-tagged, .st-text_extracted { color: var(--teal); border-color: color-mix(in srgb, var(--teal) 40%, var(--line)); }
  .st-ocr_failed, .st-no_text { color: var(--stamp); border-color: color-mix(in srgb, var(--stamp) 40%, var(--line)); }

  @media (max-width: 560px) {
    .doc { flex-direction: column; align-items: flex-start; gap: 8px; }
  }
</style>
