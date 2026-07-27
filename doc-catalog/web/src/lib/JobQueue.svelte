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
  <div class="head">
    <h2>Pipeline</h2>
    <span class="mono muted">{active} active</span>
  </div>

  <div class="grid">
    {#each STAGES as stage}
      <div class="card qcard">
        <div class="stage mono">{stage}</div>
        <div class="pills">
          {#each STATES as st}
            {@const n = byStage[stage]?.[st] ?? 0}
            <span class="pill {st}" class:zero={n === 0}>
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
  .head { display: flex; align-items: baseline; justify-content: space-between; margin: 0 0 12px; }
  .head h2 { margin: 0; font-size: 16px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: var(--gap); }
  .qcard { padding: 14px 16px; }
  .stage { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin-bottom: 10px; }
  .pills { display: flex; flex-wrap: wrap; gap: 6px; }
  .pill {
    display: inline-flex; align-items: center; gap: 5px;
    font-family: var(--font-mono); font-size: 11px; padding: 3px 8px;
    border-radius: 999px; border: 1px solid var(--line); color: var(--muted);
  }
  .pill .n { font-weight: 600; color: var(--ink); }
  .pill.zero { opacity: .38; }
  .pill.running:not(.zero) { border-color: var(--teal); color: var(--teal); }
  .pill.running:not(.zero) .n { color: var(--teal); }
  .pill.failed:not(.zero) { border-color: var(--stamp); color: var(--stamp); }
  .pill.failed:not(.zero) .n { color: var(--stamp); }
  .pill.done:not(.zero) .n { color: var(--blue); }

  .fails { margin-top: var(--gap); padding: 12px 16px; }
  .failrow { display: flex; align-items: center; gap: 10px; padding: 6px 0; border-top: 1px solid var(--line); }
  .failrow:first-of-type { border-top: none; }
  .ftitle { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .stamp { color: var(--stamp); }
</style>
