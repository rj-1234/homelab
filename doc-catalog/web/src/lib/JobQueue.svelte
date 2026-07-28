<script>
  import { status } from '$lib/status.js';

  const STAGES = ['text', 'ocr', 'embed', 'embed_pages'];
  const STATES = ['running', 'pending', 'failed', 'done'];

  // status.jobs is [{stage, state, n}] -> {stage: {state: n}}
  let byStage = $derived.by(() => {
    const m = {};
    for (const s of STAGES) m[s] = {};
    for (const row of $status?.jobs ?? []) {
      (m[row.stage] ??= {})[row.state] = row.n;
    }
    return m;
  });

  let active = $derived(
    ($status?.jobs ?? [])
      .filter((r) => r.state === 'pending' || r.state === 'running')
      .reduce((a, r) => a + r.n, 0)
  );
</script>

<section>
  <h2 class="eyebrow">Pipeline · {active} active</h2>

  <div class="grid">
    {#each STAGES as stage}
      <div class="card qcard">
        <div class="stage mono">{stage}</div>
        <div class="pills">
          {#each STATES as st}
            {@const n = byStage[stage]?.[st] ?? 0}
            <span class="pill {st} mono" class:zero={n === 0}>
              <span class="dot" aria-hidden="true"></span>
              <span class="n">{n}</span>{st}
            </span>
          {/each}
        </div>
      </div>
    {/each}
  </div>

  {#if $status?.failures?.length}
    <div class="fails card">
      <div class="stage mono">failed jobs</div>
      {#each $status.failures as f}
        <div class="failrow">
          <span class="mono stamp">#{f.id} {f.stage}</span>
          <span class="ftitle">{f.title}</span>
          <span class="mono muted">×{f.attempts}</span>
        </div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: var(--gap); }
  .qcard { padding: var(--s-4); }
  .stage {
    font-size: var(--t-cap); text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--muted); margin-bottom: var(--s-3);
  }
  .pills { display: flex; flex-wrap: wrap; gap: 6px; }
  .pill {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 0.6875rem; padding: 3px 9px 3px 7px;
    border-radius: var(--radius-pill); border: 1px solid var(--line); color: var(--muted);
  }
  .pill .n { font-weight: 600; color: var(--ink); }
  .pill .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--faint); flex: none; }
  .pill.zero { opacity: 0.4; }
  .pill.running:not(.zero) { border-color: var(--teal); color: var(--teal); }
  .pill.running:not(.zero) .n { color: var(--teal); }
  .pill.running .dot { background: var(--teal); }
  .pill.pending .dot { background: var(--muted); }
  .pill.failed:not(.zero) { border-color: var(--stamp); color: var(--stamp); }
  .pill.failed:not(.zero) .n { color: var(--stamp); }
  .pill.failed .dot { background: var(--stamp); }
  .pill.done:not(.zero) .n { color: var(--blue); }
  .pill.done .dot { background: var(--faint); }

  .fails { margin-top: var(--gap); padding: var(--s-3) var(--s-4); }
  .failrow { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-2) 0; border-top: 1px solid var(--line); }
  .failrow:first-of-type { border-top: none; }
  .ftitle { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
