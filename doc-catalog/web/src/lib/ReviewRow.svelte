<script>
  import { revealField, confirmField, deleteField } from '$lib/api.js';

  // row: { id, entity_class, label, value_masked, score, title }
  // ondone: (id) => void  — parent removes the row after an action
  let { row, ondone } = $props();

  let shown = $state(row.value_masked);
  let revealed = $state(false);
  let editing = $state(false);
  let draft = $state('');
  let busy = $state(false);

  async function reveal() {
    if (revealed) return;
    shown = await revealField(row.id);
    revealed = true;
  }

  async function startEdit() {
    if (!revealed) await reveal();
    draft = shown;
    editing = true;
  }

  async function confirm() {
    busy = true;
    try {
      await confirmField(row.id, editing && draft.trim() ? { value: draft.trim() } : null);
      ondone?.(row.id);
    } finally { busy = false; }
  }

  async function reject() {
    busy = true;
    try { await deleteField(row.id); ondone?.(row.id); }
    finally { busy = false; }
  }
</script>

<div class="row">
  <div class="meta">
    <span class="label mono">{row.label}</span>
    <a class="src" href={`/doc/${row.document_id}`} title={row.title}>{row.title}</a>
  </div>

  <div class="val mono">
    {#if editing}
      <input class="mono" bind:value={draft} spellcheck="false" />
    {:else}
      <button class="reveal" class:on={revealed} onclick={reveal}
              title={revealed ? '' : 'Reveal to check'}>{shown}</button>
    {/if}
  </div>

  <div class="acts">
    <button class="ic ok" onclick={confirm} disabled={busy} title="Confirm">✓</button>
    <button class="ic" onclick={startEdit} disabled={busy} title="Edit value">✎</button>
    <button class="ic no" onclick={reject} disabled={busy} title="Not a field / reject">✕</button>
  </div>
</div>

<style>
  .row {
    display: grid; grid-template-columns: 1fr 1.2fr auto; gap: 12px; align-items: center;
    padding: 10px 14px; border-top: 1px solid var(--line);
  }
  .row:first-child { border-top: 0; }
  .meta { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }
  .src { font-size: 12px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .src:hover { color: var(--teal); }

  .val { min-width: 0; }
  .reveal {
    width: 100%; text-align: left; border: 0; cursor: pointer;
    background: color-mix(in srgb, var(--ink) 6%, transparent);
    border-radius: 6px; padding: 6px 10px; color: var(--ink);
    letter-spacing: 0.1em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .reveal.on { letter-spacing: 0.03em; color: var(--teal); background: color-mix(in srgb, var(--teal) 12%, transparent); }
  input { width: 100%; padding: 6px 10px; border: 1px solid var(--teal); border-radius: 6px; background: var(--card); color: var(--ink); }

  .acts { display: flex; gap: 4px; }
  .ic {
    width: 30px; height: 30px; display: grid; place-items: center;
    border: 1px solid var(--line); border-radius: 8px; background: var(--card); cursor: pointer;
  }
  .ic:hover { border-color: var(--muted); }
  .ic.ok:hover { border-color: var(--teal); color: var(--teal); }
  .ic.no:hover { border-color: var(--stamp); color: var(--stamp); }
  .ic:disabled { opacity: 0.5; cursor: default; }
</style>
