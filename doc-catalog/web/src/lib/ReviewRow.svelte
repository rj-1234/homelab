<script>
  import { onMount } from 'svelte';
  import { revealField, confirmField, deleteField } from '$lib/api.js';
  import Icon from '$lib/Icon.svelte';

  // row: { id, entity_class, label, value_masked, score, title }
  // ondone: (id) => void  — parent removes the row after an action
  let { row, ondone } = $props();

  let shown = $state('');
  let revealed = $state(false);
  onMount(() => { shown = row.value_masked; });
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
              title={revealed ? '' : 'Reveal to check'}>
        <Icon name={revealed ? 'eye-off' : 'eye'} size="14px" />
        <span class="txt">{shown}</span>
      </button>
    {/if}
  </div>

  <div class="acts">
    <button class="ic ok" onclick={confirm} disabled={busy} aria-label="Confirm">
      <Icon name="check" size="16px" />
    </button>
    <button class="ic" onclick={startEdit} disabled={busy} aria-label="Edit value">
      <Icon name="edit" size="15px" />
    </button>
    <button class="ic no" onclick={reject} disabled={busy} aria-label="Not a field / reject">
      <Icon name="x" size="16px" />
    </button>
  </div>
</div>

<style>
  .row {
    display: grid; grid-template-columns: 1fr 1.2fr auto; gap: var(--s-3); align-items: center;
    padding: var(--s-3) var(--s-4); border-top: 1px solid var(--line);
  }
  .row:first-child { border-top: 0; }
  .meta { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .label { font-size: var(--t-cap); text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }
  .src { font-size: var(--t-sm); color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .src:hover { color: var(--teal); }

  .val { min-width: 0; }
  .reveal {
    display: flex; align-items: center; gap: 8px;
    width: 100%; text-align: left; border: 0; cursor: pointer;
    background: color-mix(in srgb, var(--ink) 6%, transparent);
    border-radius: var(--radius-sm); padding: 7px 10px; color: var(--muted);
    letter-spacing: 0.1em; transition: background .15s ease, color .15s ease;
  }
  .reveal .txt { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .reveal:hover { background: color-mix(in srgb, var(--ink) 9%, transparent); }
  .reveal.on {
    letter-spacing: 0.03em; color: var(--teal);
    background: var(--teal-wash);
  }
  input {
    width: 100%; padding: 7px 10px; border: 1px solid var(--teal);
    border-radius: var(--radius-sm); background: var(--card); color: var(--ink);
    box-sizing: border-box;
  }

  .acts { display: flex; gap: 5px; }
  .ic {
    width: 40px; height: 40px; display: grid; place-items: center;
    border: 1px solid var(--line); border-radius: var(--radius-sm);
    background: var(--card); color: var(--muted); cursor: pointer;
    transition: border-color .15s ease, color .15s ease, background .15s ease;
  }
  .ic:hover { border-color: var(--muted); }
  .ic.ok:hover { border-color: var(--teal); color: var(--teal); background: var(--teal-wash); }
  .ic.no:hover { border-color: var(--stamp); color: var(--stamp); background: var(--stamp-wash); }
  .ic:disabled { opacity: 0.5; cursor: default; }

  @media (max-width: 560px) {
    .row { grid-template-columns: 1fr; gap: var(--s-2); }
    .acts { justify-content: flex-end; }
  }
</style>
