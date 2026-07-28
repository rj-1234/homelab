<script>
  import { onMount } from 'svelte';
  import { status } from '$lib/status.js';
  import { listFields } from '$lib/api.js';
  import { intoGroups } from '$lib/fields.js';
  import FieldCard from '$lib/FieldCard.svelte';
  import Icon from '$lib/Icon.svelte';

  let fields = $state([]);
  let loading = $state(true);
  let error = $state('');

  async function load() {
    try { fields = await listFields(); error = ''; }
    catch (e) { error = String(e.message ?? e); }
    finally { loading = false; }
  }
  onMount(load);

  const groups = $derived(intoGroups(fields));
  const review = $derived($status?.fields?.review ?? 0);

  // Re-pull the shelf when the confirmed-count changes (a confirm over in /review),
  // so it stays live without polling. Guarded so it doesn't loop.
  let seenConfirmed = $state(null);
  $effect(() => {
    const c = $status?.fields?.confirmed;
    if (c != null && c !== seenConfirmed) { seenConfirmed = c; load(); }
  });
</script>

<main class="wrap">
  {#if review > 0}
    <a class="reviewbar" href="/review">
      <span class="ic"><Icon name="alert-triangle" size="18px" /></span>
      <span class="txt">
        <strong>{review}</strong> candidate{review === 1 ? '' : 's'} to confirm
      </span>
      <span class="go mono">Review <Icon name="chevron-right" size="14px" /></span>
    </a>
  {/if}

  {#if loading}
    <p class="muted">Loading vault…</p>
  {:else if error}
    <p class="stamp">Couldn’t load the vault: {error}</p>
  {:else if fields.length === 0}
    <div class="empty card">
      <span class="empty-ic"><Icon name="shield" size="26px" stroke={1.5} /></span>
      <h2>Your vault is empty</h2>
      {#if review > 0}
        <p class="muted">
          {review} field{review === 1 ? '' : 's'} were extracted from your documents.
          Confirm the ones you want and they’ll appear here, copy-ready.
        </p>
        <a class="btn" href="/review">Review {review} candidates <Icon name="chevron-right" size="14px" /></a>
      {:else}
        <p class="muted">Upload or sync documents — extracted fields will show up to confirm.</p>
      {/if}
    </div>
  {:else}
    {#each groups as g}
      <section class="group">
        <h2 class="eyebrow">{g.title}</h2>
        <div class="grid">
          {#each g.fields as f (f.id)}
            <FieldCard field={f} />
          {/each}
        </div>
      </section>
    {/each}
  {/if}
</main>

<style>
  .reviewbar {
    display: flex; align-items: center; gap: var(--s-3);
    background: var(--stamp-wash);
    border: 1px solid color-mix(in srgb, var(--stamp) 22%, var(--line));
    color: var(--ink); border-radius: var(--radius);
    padding: var(--s-3) var(--s-4); margin-bottom: var(--s-6); font-size: var(--t-sm);
    transition: border-color .18s ease, box-shadow .18s ease;
  }
  .reviewbar:hover { text-decoration: none; border-color: var(--stamp); box-shadow: var(--shadow); }
  .reviewbar .ic {
    flex: none; display: grid; place-items: center; width: 34px; height: 34px;
    border-radius: 50%; background: color-mix(in srgb, var(--stamp) 14%, var(--card)); color: var(--stamp);
  }
  .reviewbar .txt { flex: 1; }
  .reviewbar strong { font-family: var(--font-display); }
  .reviewbar .go {
    display: inline-flex; align-items: center; gap: 2px;
    color: var(--stamp); font-size: var(--t-sm); font-weight: 500; flex: none;
  }

  .group { margin-bottom: var(--s-6); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: var(--gap); }

  .empty { padding: var(--s-7) var(--s-5); text-align: center; }
  .empty-ic {
    display: inline-grid; place-items: center; width: 56px; height: 56px;
    border-radius: 50%; margin: 0 auto var(--s-4);
    background: var(--teal-wash); color: var(--teal);
  }
  .empty h2 { margin: 0 0 var(--s-2); }
  .empty p { max-width: 44ch; margin: 0 auto var(--s-4); }
</style>
