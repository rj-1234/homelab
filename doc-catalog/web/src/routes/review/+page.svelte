<script>
  import { onMount } from 'svelte';
  import { listReview } from '$lib/api.js';
  import { intoGroups } from '$lib/fields.js';
  import ReviewRow from '$lib/ReviewRow.svelte';

  let rows = $state([]);
  let loading = $state(true);
  let error = $state('');

  async function load() {
    try { rows = await listReview(); error = ''; }
    catch (e) { error = String(e.message ?? e); }
    finally { loading = false; }
  }
  onMount(load);

  // remove a row locally once confirmed/rejected (SSE updates the badge)
  function done(id) { rows = rows.filter((r) => r.id !== id); }

  const groups = $derived(intoGroups(rows));
</script>

<main class="wrap">
  <div class="head">
    <h1>Review</h1>
    <span class="mono muted">{rows.length} candidate{rows.length === 1 ? '' : 's'}</span>
  </div>
  <p class="muted intro">
    Confirm the fields worth keeping — they move to your vault. Reveal to check a value,
    edit if OCR got it wrong, or reject noise. Nothing shows on the shelf until you confirm.
  </p>

  {#if loading}
    <p class="muted">Loading…</p>
  {:else if error}
    <p class="stamp">{error}</p>
  {:else if rows.length === 0}
    <div class="empty card">
      <h2>Nothing to review</h2>
      <p class="muted">Every extracted field has been handled. <a href="/">Back to the vault →</a></p>
    </div>
  {:else}
    {#each groups as g}
      <section class="group">
        <h2 class="gtitle mono">{g.title} · {g.fields.length}</h2>
        <div class="card list">
          {#each g.fields as r (r.id)}
            <ReviewRow row={r} ondone={done} />
          {/each}
        </div>
      </section>
    {/each}
  {/if}
</main>

<style>
  .head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 4px; }
  .head h1 { margin: 0; font-size: 22px; }
  .intro { max-width: 66ch; margin: 0 0 24px; font-size: 13px; }

  .group { margin-bottom: 24px; }
  .gtitle { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin: 0 0 10px; font-weight: 500; }
  .list { overflow: hidden; }

  .empty { padding: 36px 24px; text-align: center; }
  .empty h2 { margin: 0 0 8px; font-size: 18px; }
</style>
