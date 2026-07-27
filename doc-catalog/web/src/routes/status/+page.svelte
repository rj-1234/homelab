<script>
  import { status } from '$lib/status.js';
  import JobQueue from '$lib/JobQueue.svelte';

  const docs = $derived($status?.documents ?? 0);
  const sources = $derived($status?.sources ?? []);
  const accounts = $derived($status?.accounts ?? []);
  const vault = $derived($status?.fields ?? { confirmed: 0, review: 0 });
</script>

<main class="wrap">
  <h1>Status</h1>

  <div class="stats">
    <div class="stat card"><div class="n">{docs}</div><div class="l mono">documents</div></div>
    <div class="stat card"><div class="n">{vault.confirmed}</div><div class="l mono">vault fields</div></div>
    <div class="stat card"><div class="n">{vault.review}</div><div class="l mono">to review</div></div>
    {#each sources as s}
      <div class="stat card"><div class="n">{s.n}</div><div class="l mono">{s.source}</div></div>
    {/each}
  </div>

  <JobQueue />

  {#if accounts.length}
    <section class="gmail">
      <h2>Gmail</h2>
      <div class="grid">
        {#each accounts as a}
          <div class="acct card">
            <div class="email">{a.email}</div>
            <div class="mono muted">
              {a.synced ? 'synced' : 'not synced'} · {a.attachments} attachment{a.attachments === 1 ? '' : 's'}
            </div>
          </div>
        {/each}
      </div>
    </section>
  {/if}
</main>

<style>
  h1 { font-size: 22px; margin: 0 0 20px; }
  .stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: var(--gap); margin-bottom: 28px; }
  .stat { padding: 16px; }
  .stat .n { font-family: var(--font-display); font-size: 28px; font-weight: 600; }
  .stat .l { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin-top: 2px; }

  .gmail { margin-top: 28px; }
  .gmail h2 { font-size: 16px; margin: 0 0 12px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--gap); }
  .acct { padding: 14px 16px; }
  .email { font-weight: 500; margin-bottom: 4px; }
</style>
