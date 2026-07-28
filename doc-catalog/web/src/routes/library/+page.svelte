<script>
  import { onMount } from 'svelte';
  import { listDocuments, listTags, getTaxonomy } from '$lib/api.js';
  import DocCard from '$lib/DocCard.svelte';
  import Uploader from '$lib/Uploader.svelte';
  import Icon from '$lib/Icon.svelte';

  let query = $state('');
  let tag = $state('');
  let statusFilter = $state('');
  let tags = $state([]);
  let statuses = $state([]);
  let docs = $state([]);
  let loading = $state(true);
  let error = $state('');

  const searching = $derived(query.trim().length > 0);

  let debounceTimer;
  let reqId = 0;

  async function load() {
    const my = ++reqId;
    loading = true;
    try {
      const q = query.trim();
      const rows = q ? await listDocuments({ q }) : await listDocuments({ tag, status: statusFilter });
      if (my !== reqId) return; // a newer request has since started
      docs = rows;
      error = '';
    } catch (e) {
      if (my !== reqId) return;
      error = String(e.message ?? e);
    } finally {
      if (my === reqId) loading = false;
    }
  }

  function onInput() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(load, 250);
  }

  function selectTag(t) {
    tag = t;
    query = '';
    load();
  }

  function selectStatus(s) {
    statusFilter = s;
    query = '';
    load();
  }

  onMount(async () => {
    load();
    try { tags = await listTags(); } catch { /* filter chips are best-effort */ }
    try { statuses = (await getTaxonomy()).statuses ?? []; } catch { /* filter chips are best-effort */ }
  });
</script>

<main class="wrap">
  <div class="head">
    <h1>Library</h1>
    <span class="mono muted count">
      {docs.length} {searching ? `result${docs.length === 1 ? '' : 's'}` : `document${docs.length === 1 ? '' : 's'}`}
    </span>
    <Uploader compact />
  </div>

  <div class="search-bar">
    <span class="search-ic" aria-hidden="true"><Icon name="search" size="17px" /></span>
    <input
      type="search"
      class="search mono"
      placeholder="Search documents…"
      bind:value={query}
      oninput={onInput}
    />
  </div>

  <div class="chips">
    <button class="chip" class:active={!tag} onclick={() => selectTag('')}>All</button>
    {#each tags.slice(0, 12) as t}
      <button class="chip" class:active={tag === t.name} onclick={() => selectTag(t.name)}>
        {t.name} <span class="n">{t.n}</span>
      </button>
    {/each}
  </div>

  {#if statuses.length}
    <div class="chips statuschips">
      <button class="chip status" class:active={!statusFilter} onclick={() => selectStatus('')}>Any status</button>
      {#each statuses as s (s.key)}
        <button class="chip status" class:active={statusFilter === s.key} onclick={() => selectStatus(s.key)}>
          {s.label}
        </button>
      {/each}
    </div>
  {/if}

  {#if loading}
    <p class="muted">Loading documents…</p>
  {:else if error}
    <p class="stamp">Couldn’t load the library: {error}</p>
  {:else if docs.length === 0}
    <div class="empty card">
      <span class="empty-ic"><Icon name={searching ? 'search' : 'inbox'} size="26px" stroke={1.5} /></span>
      {#if searching}
        <h2>No matches</h2>
        <p class="muted">Nothing found for “{query}”. Try a different term.</p>
      {:else if tag}
        <h2>No documents tagged “{tag}”</h2>
        <p class="muted">Try another tag or clear the filter.</p>
      {:else}
        <h2>No documents yet</h2>
        <p class="muted">Upload or sync a source — documents will show up here.</p>
      {/if}
    </div>
  {:else}
    <div class="grid">
      {#each docs as d (d.id)}
        <DocCard doc={d} snippet={searching ? d.snippet : null} />
      {/each}
    </div>
  {/if}
</main>

<style>
  .head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--s-3); margin-bottom: var(--s-4); flex-wrap: wrap; }
  .count { font-size: var(--t-sm); }

  .search-bar {
    position: sticky; top: 57px; z-index: 5; background: var(--paper);
    padding: 4px 0 var(--s-4); display: flex; align-items: center;
  }
  .search-ic {
    position: relative; margin-right: -36px; z-index: 1;
    display: grid; place-items: center; width: 36px; color: var(--faint);
    pointer-events: none;
  }
  .search {
    width: 100%; box-sizing: border-box;
    background: var(--card); color: var(--ink);
    border: 1px solid var(--line); border-radius: var(--radius-pill);
    padding: 11px 16px 11px 38px; font-size: var(--t-0);
    min-height: 44px;
  }
  .search::placeholder { color: var(--faint); }
  .search:focus-visible { outline: 2px solid var(--blue); outline-offset: 1px; }

  .chips {
    display: flex; gap: var(--s-2); overflow-x: auto; -webkit-overflow-scrolling: touch;
    padding-bottom: 4px; margin-bottom: var(--s-5); scrollbar-width: none;
  }
  .chips::-webkit-scrollbar { display: none; }
  .chip {
    flex-shrink: 0; font-family: var(--font-mono); font-size: 0.6875rem;
    color: var(--muted); background: var(--card); border: 1px solid var(--line);
    border-radius: var(--radius-pill); padding: 8px 14px; min-height: 36px; cursor: pointer;
    white-space: nowrap;
  }
  .chip .n { color: var(--muted); opacity: 0.8; }
  .chip.active {
    color: var(--blue); border-color: color-mix(in srgb, var(--blue) 40%, var(--line));
    background: var(--blue-wash);
  }
  .chip:hover { border-color: var(--blue); }

  /* status row reuses the same chip shape, tinted --teal instead of --blue so
     it reads as a distinct filter axis without adding a new hue */
  .statuschips { margin-top: -12px; }
  .chip.status.active {
    color: var(--teal); border-color: color-mix(in srgb, var(--teal) 40%, var(--line));
    background: var(--teal-wash);
  }
  .chip.status:hover { border-color: var(--teal); }

  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: var(--gap); }

  .empty { padding: var(--s-7) var(--s-5); text-align: center; }
  .empty-ic {
    display: inline-grid; place-items: center; width: 56px; height: 56px;
    border-radius: 50%; margin: 0 auto var(--s-4);
    background: var(--blue-wash); color: var(--blue);
  }
  .empty h2 { margin: 0 0 var(--s-2); }
  .empty p { max-width: 44ch; margin: 0 auto; }
</style>
