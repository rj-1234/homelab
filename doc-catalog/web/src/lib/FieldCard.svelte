<script>
  import { revealField } from '$lib/api.js';

  // field: { id, label, value_masked, entity_class, expiry }
  let { field } = $props();

  let revealed = $state(null);   // plaintext once fetched, else null (masked)
  let copied = $state(false);
  let busy = $state(false);
  let timer;

  async function value() {
    // fetch once, keep for the reveal window
    if (revealed == null) revealed = await revealField(field.id);
    return revealed;
  }

  async function toggleReveal() {
    if (revealed != null) { remask(); return; }
    busy = true;
    try {
      await value();
      clearTimeout(timer);
      timer = setTimeout(remask, 15000);   // auto re-mask
    } finally { busy = false; }
  }

  function remask() { revealed = null; clearTimeout(timer); }

  async function copy() {
    busy = true;
    try {
      await navigator.clipboard.writeText(await value());
      copied = true;
      setTimeout(() => (copied = false), 1400);
      clearTimeout(timer);
      timer = setTimeout(remask, 15000);
    } finally { busy = false; }
  }

  const expired = $derived(
    field.expiry && new Date(field.expiry) < new Date()
  );
</script>

<div class="field" class:expired>
  <div class="row">
    <span class="label mono">{field.label}</span>
    {#if field.expiry}
      <span class="exp mono" class:warn={expired}>
        {expired ? 'expired' : 'exp'} {field.expiry}
      </span>
    {/if}
  </div>

  <div class="valrow">
    <!-- the signature: a redaction that lifts on reveal -->
    <button class="val mono" class:on={revealed != null} onclick={toggleReveal}
            title={revealed != null ? 'Hide' : 'Reveal'} disabled={busy}>
      {revealed ?? field.value_masked}
    </button>
    <div class="acts">
      <button class="ic" onclick={toggleReveal} disabled={busy}
              aria-label={revealed != null ? 'Hide' : 'Reveal'}>
        {revealed != null ? '🙈' : '👁'}
      </button>
      <button class="ic" onclick={copy} disabled={busy} aria-label="Copy">
        {copied ? '✓' : '⧉'}
      </button>
    </div>
  </div>
</div>

<style>
  .field {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 12px 14px;
  }
  .field.expired { opacity: 0.55; }
  .row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }
  .exp { font-size: 10px; color: var(--muted); }
  .exp.warn { color: var(--stamp); }

  .valrow { display: flex; align-items: center; gap: 8px; margin-top: 8px; }

  /* the value reads as a redaction bar until revealed */
  .val {
    flex: 1; text-align: left; min-width: 0;
    font-size: 15px; letter-spacing: 0.12em;
    color: var(--ink); background: color-mix(in srgb, var(--ink) 6%, transparent);
    border: 0; border-radius: 6px; padding: 6px 10px; cursor: pointer;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    transition: background 0.15s, color 0.15s, letter-spacing 0.15s;
  }
  .val:hover { background: color-mix(in srgb, var(--ink) 10%, transparent); }
  .val.on {
    letter-spacing: 0.04em; color: var(--teal);
    background: color-mix(in srgb, var(--teal) 12%, transparent);
    box-shadow: inset 0 -2px 0 var(--teal);
  }

  .acts { display: flex; gap: 4px; flex-shrink: 0; }
  .ic {
    width: 32px; height: 32px; display: grid; place-items: center;
    border: 1px solid var(--line); border-radius: 8px; background: var(--card);
    cursor: pointer; font-size: 14px; line-height: 1;
  }
  .ic:hover { border-color: var(--teal); }
  .ic:disabled { opacity: 0.5; cursor: default; }
</style>
