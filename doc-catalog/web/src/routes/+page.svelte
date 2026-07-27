<script>
  import { onMount } from 'svelte';
  import { status } from '$lib/status.js';
  import { listFields } from '$lib/api.js';
  import { intoGroups } from '$lib/fields.js';
  import FieldCard from '$lib/FieldCard.svelte';

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
      <span><strong>{review}</strong> candidate{review === 1 ? '' : 's'} to confirm</span>
      <span class="go">Review →</span>
    </a>
  {/if}

  {#if loading}
    <p class="muted">Loading vault…</p>
  {:else if error}
    <p class="stamp">Couldn’t load the vault: {error}</p>
  {:else if fields.length === 0}
    <div class="empty card">
      <h2>Your vault is empty</h2>
      {#if review > 0}
        <p class="muted">
          {review} field{review === 1 ? '' : 's'} were extracted from your documents.
          Confirm the ones you want and they’ll appear here, copy-ready.
        </p>
        <a class="btn" href="/review">Review {review} candidates →</a>
      {:else}
        <p class="muted">Upload or sync documents — extracted fields will show up to confirm.</p>
      {/if}
    </div>
  {:else}
    {#each groups as g}
      <section class="group">
        <h2 class="gtitle mono">{g.title}</h2>
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
    display: flex; align-items: center; justify-content: space-between;
    background: color-mix(in srgb, var(--stamp) 8%, var(--card));
    border: 1px solid color-mix(in srgb, var(--stamp) 30%, var(--line));
    color: var(--ink); border-radius: var(--radius);
    padding: 12px 16px; margin-bottom: 24px; font-size: 14px;
  }
  .reviewbar:hover { text-decoration: none; border-color: var(--stamp); }
  .reviewbar strong { font-family: var(--font-display); }
  .reviewbar .go { color: var(--stamp); font-family: var(--font-mono); font-size: 12px; }

  .group { margin-bottom: 28px; }
  .gtitle {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--muted); margin: 0 0 12px; font-weight: 500;
  }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: var(--gap); }

  .empty { padding: 40px 28px; text-align: center; }
  .empty h2 { margin: 0 0 8px; font-size: 20px; }
  .empty p { max-width: 44ch; margin: 0 auto 18px; }

  .btn {
    display: inline-block; background: var(--teal); color: #fff;
    padding: 10px 18px; border-radius: 999px; font-size: 14px; font-weight: 500;
  }
  .btn:hover { text-decoration: none; filter: brightness(1.05); }
</style>
