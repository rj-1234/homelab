<script>
  import Icon from '$lib/Icon.svelte';
  // Compact, display-only stage strip for the doc detail page. Mirrors the
  // shape of JobQueue's status vocabulary (pending/running/done/failed) but
  // scoped to a single document's jobs.
  let { jobs = [], status, hasPages = false } = $props();

  const LABELS = { text: 'text', ocr: 'ocr', embed: 'tag' };

  function stateOf(stage) {
    const rows = jobs.filter((j) => j.stage === stage);
    if (rows.some((r) => r.state === 'failed')) return 'failed';
    if (rows.some((r) => r.state === 'pending' || r.state === 'running')) return 'active';
    if (rows.some((r) => r.state === 'done')) return 'done';
    return 'todo';
  }

  const showOcr = $derived(
    jobs.some((j) => j.stage === 'ocr') ||
      status === 'needs_ocr' ||
      status === 'ocr_failed'
  );

  const stages = $derived(
    ['text', ...(showOcr ? ['ocr'] : []), 'embed'].map((stage) => ({
      stage,
      label: LABELS[stage] ?? stage,
      state: stateOf(stage)
    }))
  );

  const allQuiet = $derived(stages.every((s) => s.state !== 'active' && s.state !== 'failed'));
  const isDone = $derived(status === 'tagged' && allQuiet);
</script>

<div class="strip">
  {#each stages as s (s.stage)}
    <span class="chip {s.state}" class:pulse={s.state === 'active'}>
      <span class="dot" aria-hidden="true"></span>
      {s.label}
    </span>
  {/each}
  {#if isDone}
    <span class="done-badge mono"><Icon name="check-circle" size="14px" /> Done</span>
  {/if}
</div>

<style>
  .strip {
    display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
    margin-bottom: 16px;
  }

  .chip {
    display: inline-flex; align-items: center; gap: 6px;
    font-family: var(--font-mono); font-size: 11.5px; text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 5px 10px; border-radius: 999px;
    border: 1px solid var(--line); color: var(--muted);
    background: var(--card);
  }
  .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: 0.6; }

  .chip.todo { opacity: 0.55; }

  .chip.active {
    color: var(--blue); border-color: color-mix(in srgb, var(--blue) 45%, var(--line));
    background: color-mix(in srgb, var(--blue) 10%, var(--card));
  }
  .chip.active .dot { opacity: 1; }
  .chip.pulse .dot { animation: pulse 1.4s ease-in-out infinite; }

  .chip.done { color: var(--muted); }
  .chip.done .dot { background: var(--teal); opacity: 0.8; }

  .chip.failed {
    color: var(--stamp); border-color: color-mix(in srgb, var(--stamp) 45%, var(--line));
    background: color-mix(in srgb, var(--stamp) 10%, var(--card));
  }

  .done-badge {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: var(--t-sm); color: var(--teal);
  }

  @keyframes pulse {
    0%, 100% { opacity: 0.4; transform: scale(0.85); }
    50% { opacity: 1; transform: scale(1.15); }
  }
</style>
