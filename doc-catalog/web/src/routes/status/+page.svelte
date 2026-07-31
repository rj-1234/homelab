<script>
  import { onMount } from 'svelte';
  import { status } from '$lib/status.js';
  import { listSenderRules, addSenderRule, delSenderRule } from '$lib/api.js';
  import JobQueue from '$lib/JobQueue.svelte';
  import Icon from '$lib/Icon.svelte';

  const docs = $derived($status?.documents ?? 0);
  const sources = $derived($status?.sources ?? []);
  const accounts = $derived($status?.accounts ?? []);
  const vault = $derived($status?.fields ?? { confirmed: 0, review: 0 });

  // --- Gmail sender rules ---
  let rules = $state([]);
  let ruleError = $state('');
  let formState = $state({}); // account_id -> { pattern, action }
  let addingId = $state(null); // account_id currently submitting
  let removingKey = $state(null); // "account_id|pattern|action" currently removing

  async function loadRules() {
    try { rules = await listSenderRules(); ruleError = ''; }
    catch (e) { ruleError = String(e.message ?? e); }
  }
  onMount(loadRules);

  // Ensure each account has a form entry once accounts arrive/change.
  $effect(() => {
    for (const a of accounts) {
      if (!formState[a.id]) formState[a.id] = { pattern: '', action: 'allow' };
    }
  });

  function rulesFor(accountId) {
    return rules.filter((r) => r.account_id === accountId);
  }

  function ruleKey(r) { return `${r.account_id}|${r.pattern}|${r.action}`; }

  // Lazily creates (or returns) the per-account form entry. Only called from
  // event handlers, never during render, so mutating $state here is safe.
  function ensureForm(accountId) {
    if (!formState[accountId]) formState[accountId] = { pattern: '', action: 'allow' };
    return formState[accountId];
  }

  async function addRule(accountId) {
    const f = ensureForm(accountId);
    const pattern = f.pattern?.trim();
    if (!pattern) return;
    addingId = accountId;
    try {
      await addSenderRule({ account_id: accountId, pattern, action: f.action });
      f.pattern = '';
      await loadRules();
    } catch (e) {
      ruleError = String(e.message ?? e);
    } finally {
      addingId = null;
    }
  }

  async function removeRule(r) {
    removingKey = ruleKey(r);
    try {
      await delSenderRule({ account_id: r.account_id, pattern: r.pattern, action: r.action });
      await loadRules();
    } catch (e) {
      ruleError = String(e.message ?? e);
    } finally {
      removingKey = null;
    }
  }
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
      <h2 class="eyebrow">Gmail</h2>
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

    <section class="rules">
      <h2 class="eyebrow">Sender rules</h2>
      <p class="muted intro">
        Allow or deny senders so ingest skips what you don’t want catalogued.
      </p>
      {#if ruleError}<p class="stamp">{ruleError}</p>{/if}

      <div class="grid">
        {#each accounts as a (a.id)}
          <div class="acct card">
            <div class="email">{a.email}</div>

            {#if rulesFor(a.id).length}
              <div class="rulechips">
                {#each rulesFor(a.id) as r (ruleKey(r))}
                  <span class="rulechip {r.action}">
                    <span class="mono">{r.pattern}</span>
                    <button
                      class="x"
                      onclick={() => removeRule(r)}
                      disabled={removingKey === ruleKey(r)}
                      aria-label={`Remove rule ${r.pattern}`}
                    ><Icon name="x" size="12px" /></button>
                  </span>
                {/each}
              </div>
            {:else}
              <p class="muted norules">No rules yet.</p>
            {/if}

            <div class="addform">
              <input
                class="input"
                type="text"
                placeholder="sender or domain pattern"
                value={formState[a.id]?.pattern ?? ''}
                oninput={(e) => { ensureForm(a.id).pattern = e.target.value; }}
              />
              <select
                class="input select"
                value={formState[a.id]?.action ?? 'allow'}
                onchange={(e) => { ensureForm(a.id).action = e.target.value; }}
              >
                <option value="allow">Allow</option>
                <option value="deny">Deny</option>
              </select>
              <button
                class="btn add"
                onclick={() => addRule(a.id)}
                disabled={addingId === a.id || !(formState[a.id]?.pattern ?? '').trim()}
              >
                <Icon name="plus" size="14px" />
                {addingId === a.id ? 'Adding…' : 'Add'}
              </button>
            </div>
          </div>
        {/each}
      </div>
    </section>
  {/if}
</main>

<style>
  h1 { margin: 0 0 var(--s-5); }
  .stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: var(--gap); margin-bottom: var(--s-6); }
  .stat { padding: var(--s-4); }
  .stat .n { font-family: var(--font-display); font-size: var(--t-3); font-weight: 600; line-height: 1.1; }
  .stat .l { font-family: var(--font-mono); font-size: var(--t-cap); text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-top: var(--s-1); }

  .gmail { margin-top: var(--s-6); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--gap); }
  .acct { padding: var(--s-4); display: flex; flex-direction: column; gap: var(--s-3); }
  .email { font-weight: 500; }

  .rules { margin-top: var(--s-6); }
  .rules .intro { font-size: var(--t-sm); max-width: 60ch; margin: 0 0 var(--s-4); }

  .rulechips { display: flex; flex-wrap: wrap; gap: var(--s-2); }
  .rulechip {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: var(--t-sm); border-radius: var(--radius-pill); padding: 5px 5px 5px 11px;
    border: 1px solid var(--line);
  }
  .rulechip.allow {
    color: var(--teal); border-color: color-mix(in srgb, var(--teal) 34%, var(--line));
    background: var(--teal-wash);
  }
  .rulechip.deny {
    color: var(--stamp); border-color: color-mix(in srgb, var(--stamp) 34%, var(--line));
    background: var(--stamp-wash);
  }
  .rulechip .x {
    width: 22px; height: 22px; display: grid; place-items: center;
    border: 0; border-radius: 50%; background: transparent; color: inherit;
    cursor: pointer; opacity: 0.75; transition: opacity .15s ease, background .15s ease;
  }
  .rulechip .x:hover:not(:disabled) { opacity: 1; background: color-mix(in srgb, currentColor 16%, transparent); }
  .rulechip .x:disabled { opacity: 0.4; cursor: default; }

  .norules { font-size: var(--t-sm); margin: 0; }

  .addform { display: flex; flex-wrap: wrap; gap: var(--s-2); }
  .addform .input { flex: 1 1 160px; min-width: 0; }
  .select { flex: 0 0 auto; min-width: 96px; }
  .input {
    font-family: var(--font-body); font-size: var(--t-0); color: var(--ink);
    background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius-sm);
    padding: 9px 10px; min-height: 40px; box-sizing: border-box;
  }
  .input:focus-visible { outline: 2px solid var(--teal); outline-offset: 1px; }

  .btn.add { flex-shrink: 0; }

  /* Mobile: form stacks vertically instead of wrapping mid-row. */
  @media (max-width: 480px) {
    .addform { flex-direction: column; align-items: stretch; }
    .addform .input, .select, .btn.add { flex: 1 1 auto; }
  }
</style>
