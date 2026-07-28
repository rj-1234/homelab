<script>
  import { uploadFiles } from '$lib/api.js';
  import Icon from '$lib/Icon.svelte';

  // compact: icon+label button only, no dropzone (used inline in list headers).
  let { compact = false } = $props();

  let input = $state();
  let busy = $state(false);
  let toast = $state('');
  let toastKind = $state('ok'); // 'ok' | 'err'
  let dragging = $state(false);
  let toastTimer;

  function flash(msg, kind = 'ok') {
    toast = msg;
    toastKind = kind;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast = ''), 3200);
  }

  async function send(fileList) {
    if (!fileList || fileList.length === 0) return;
    busy = true;
    try {
      const r = await uploadFiles(fileList);
      const n = r?.queued?.length ?? fileList.length;
      flash(`Queued ${n} file${n === 1 ? '' : 's'}`, 'ok');
    } catch (e) {
      flash(`Upload failed: ${String(e.message ?? e)}`, 'err');
    } finally {
      busy = false;
    }
  }

  function onChange(e) {
    send(e.target.files);
    e.target.value = '';
  }

  function openPicker() { input?.click(); }

  function onDrop(e) {
    e.preventDefault();
    dragging = false;
    send(e.dataTransfer?.files);
  }
  function onDragOver(e) { e.preventDefault(); dragging = true; }
  function onDragLeave() { dragging = false; }
</script>

<div class="uploader" class:compact>
  <input
    bind:this={input}
    type="file"
    multiple
    hidden
    accept=".pdf,.png,.jpg,.jpeg,.tiff,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
    onchange={onChange}
  />

  {#if compact}
    <button class="btn" onclick={openPicker} disabled={busy}>
      <Icon name={busy ? 'upload' : 'plus'} size="15px" />
      {busy ? 'Uploading…' : 'Add documents'}
    </button>
  {:else}
    <button
      class="dropzone"
      class:over={dragging}
      onclick={openPicker}
      ondrop={onDrop}
      ondragover={onDragOver}
      ondragleave={onDragLeave}
      disabled={busy}
      type="button"
    >
      <span class="dz-icon" aria-hidden="true"><Icon name="upload" size="20px" stroke={1.6} /></span>
      <span class="dz-title">Add documents</span>
      <span class="dz-sub muted">Drop files here, or tap to choose</span>
    </button>
  {/if}

  {#if toast}
    <span class="toast mono" class:err={toastKind === 'err'}>{toast}</span>
  {/if}
</div>

<style>
  .uploader { display: inline-flex; flex-direction: column; gap: 6px; }

  /* documents-context button: blue outline (vault primary stays teal) */
  .btn {
    display: inline-flex; align-items: center; gap: var(--s-2); min-height: 40px;
    border: 1px solid var(--blue); color: var(--blue); background: var(--card);
    padding: 0 16px; border-radius: var(--radius-pill); font-size: var(--t-sm); font-weight: 500;
    cursor: pointer; transition: background .15s ease;
  }
  .btn:hover:not(:disabled) { background: var(--blue-wash); }
  .btn:disabled { opacity: 0.6; cursor: default; }

  .dropzone {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 4px; width: 100%; min-height: 96px; box-sizing: border-box;
    border: 1px dashed var(--line); border-radius: var(--radius);
    background: var(--card); color: var(--ink); cursor: pointer;
    padding: 16px; text-align: center;
    transition: border-color 0.15s, background 0.15s;
  }
  .dropzone:hover:not(:disabled) { border-color: color-mix(in srgb, var(--blue) 50%, var(--line)); }
  .dropzone.over {
    border-color: var(--blue);
    background: color-mix(in srgb, var(--blue) 8%, var(--card));
  }
  .dropzone:disabled { opacity: 0.6; cursor: default; }
  .dz-icon {
    display: grid; place-items: center; width: 40px; height: 40px; margin-bottom: 2px;
    border-radius: 10px; color: var(--blue);
    background: var(--blue-wash); border: 1px solid color-mix(in srgb, var(--blue) 18%, var(--line));
  }
  .dz-title { font-family: var(--font-display); font-weight: 500; font-size: var(--t-1); }
  .dz-sub { font-size: var(--t-sm); }

  .toast { font-size: var(--t-sm); color: var(--teal); }
  .toast.err { color: var(--stamp); }
</style>
