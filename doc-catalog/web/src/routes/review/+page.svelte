<script>
  import { onMount } from 'svelte';
  import { listReview } from '$lib/api.js';
  import { intoGroups } from '$lib/fields.js';
  import ReviewRow from '$lib/ReviewRow.svelte';
  import Icon from '$lib/Icon.svelte';

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
      <span class="empty-ic"><Icon name="check-circle" size="26px" stroke={1.5} /></span>
      <h2>Nothing to review</h2>
      <p class="muted">Every extracted field has been handled. <a href="/">Back to the vault →</a></p>
    </div>
  {:else}
    {#each groups as g}
      <section class="group">
        <h2 class="eyebrow">{g.title} · {g.fields.length}</h2>
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
  .head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--s-1); }
  .intro { max-width: 66ch; margin: 0 0 var(--s-6); font-size: var(--t-sm); }

  .group { margin-bottom: var(--s-6); }
  .list { overflow: hidden; }

  .empty { padding: var(--s-7) var(--s-5); text-align: center; }
  .empty-ic {
    display: inline-grid; place-items: center; width: 56px; height: 56px;
    border-radius: 50%; margin: 0 auto var(--s-4);
    background: var(--teal-wash); color: var(--teal);
  }
  .empty h2 { margin: 0 0 var(--s-2); }
</style>
