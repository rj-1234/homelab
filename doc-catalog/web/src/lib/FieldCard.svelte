<script>
  import { revealField } from '$lib/api.js';
  import Icon from '$lib/Icon.svelte';

  // field: { id, label, value_masked, entity_class, expiry }
  let { field } = $props();

  let revealed = $state(null);   // plaintext once fetched, else null (masked)
  let copied = $state(false);
  let busy = $state(false);
  let timer;

  async function value() {
    if (revealed == null) revealed = await revealField(field.id);
    return revealed;
  }
  async function toggleReveal() {
    if (revealed != null) { remask(); return; }
    busy = true;
    try { await value(); clearTimeout(timer); timer = setTimeout(remask, 15000); }
    finally { busy = false; }
  }
  function remask() { revealed = null; clearTimeout(timer); }
  async function copy() {
    busy = true;
    try {
      await navigator.clipboard.writeText(await value());
      copied = true; setTimeout(() => (copied = false), 1400);
      clearTimeout(timer); timer = setTimeout(remask, 15000);
    } finally { busy = false; }
  }

  const shown = $derived(revealed != null);
  const expired = $derived(field.expiry && new Date(field.expiry) < new Date());
</script>

<div class="field card" class:expired class:live={shown}>
  <div class="row">
    <span class="label mono">{field.label}</span>
    {#if field.expiry}
      <span class="exp mono" class:warn={expired}>
        {expired ? 'expired' : 'exp'} · {field.expiry}
      </span>
    {/if}
  </div>

  <div class="valrow">
    <button class="val mono" class:on={shown} onclick={toggleReveal}
            title={shown ? 'Hide' : 'Reveal'} disabled={busy}>
      <span class="txt">{revealed ?? field.value_masked}</span>
    </button>
    <div class="acts">
      <button class="ic" onclick={toggleReveal} disabled={busy}
              aria-label={shown ? 'Hide value' : 'Reveal value'}>
        <Icon name={shown ? 'eye-off' : 'eye'} size="17px" />
      </button>
      <button class="ic copy" class:done={copied} onclick={copy} disabled={busy} aria-label="Copy value">
        <Icon name={copied ? 'check' : 'copy'} size="16px" />
      </button>
    </div>
  </div>
</div>

<style>
  .field { padding: 13px 14px 14px; transition: border-color .18s ease, box-shadow .18s ease; }
  .field.live { border-color: color-mix(in srgb, var(--teal) 40%, var(--line)); box-shadow: var(--shadow-lg); }
  .field.expired { opacity: 0.6; }

  .row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .label {
    font-size: var(--t-cap); text-transform: uppercase; letter-spacing: 0.09em;
    color: var(--muted); font-weight: 500;
  }
  .exp { font-size: 0.625rem; color: var(--faint); letter-spacing: 0.04em; }
  .exp.warn { color: var(--stamp); }

  .valrow { display: flex; align-items: center; gap: 8px; margin-top: 11px; }

  /* the redaction bar: a concealed stripe that lifts to a clear teal value */
  .val {
    flex: 1; min-width: 0; text-align: left;
    display: flex; align-items: center;
    height: 38px; padding: 0 12px; border: 0; border-radius: var(--radius-sm);
    cursor: pointer; color: var(--ink);
    background-color: color-mix(in srgb, var(--ink) 7%, transparent);
    background-image: repeating-linear-gradient(
      -45deg, transparent 0 6px,
      color-mix(in srgb, var(--ink) 5%, transparent) 6px 12px);
    transition: background .18s ease, color .18s ease, box-shadow .18s ease;
  }
  .val .txt {
    font-size: 0.9375rem; letter-spacing: 0.14em;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .val:hover { background-color: color-mix(in srgb, var(--ink) 11%, transparent); }
  .val.on {
    color: var(--teal); background-image: none;
    background-color: var(--teal-wash);
    box-shadow: inset 0 -2px 0 var(--teal);
  }
  .val.on .txt { letter-spacing: 0.04em; }

  .acts { display: flex; gap: 5px; flex: none; }
  .ic {
    width: 36px; height: 36px; display: grid; place-items: center;
    border: 1px solid var(--line); border-radius: var(--radius-sm);
    background: var(--card); color: var(--muted); cursor: pointer;
    transition: border-color .15s ease, color .15s ease, background .15s ease;
  }
  .ic:hover { border-color: var(--teal); color: var(--teal); background: var(--teal-wash); }
  .ic:disabled { opacity: 0.5; cursor: default; }
  .ic.copy.done { border-color: var(--teal); color: var(--teal); background: var(--teal-wash); }
</style>
