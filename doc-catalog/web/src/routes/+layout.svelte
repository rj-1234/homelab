<script>
  import '../app.css';
  import { status, connected } from '$lib/status.js';
  let { children } = $props();

  const review = $derived($status?.fields?.review ?? 0);
</script>

<header class="topbar">
  <div class="bar wrap">
    <a class="brand" href="/">
      <span class="stamp">◗</span>
      <span class="title">Vault</span>
    </a>

    <nav class="nav mono">
      <a href="/">Vault</a>
      <a href="/review" class="rev">
        Review{#if review > 0}<span class="badge">{review}</span>{/if}
      </a>
      <a href="/status">Status</a>
    </nav>

    <span class="live" class:on={$connected} title={$connected ? 'Live' : 'Reconnecting…'}>
      <span class="dot"></span>{$connected ? 'live' : 'offline'}
    </span>
  </div>
</header>

{@render children()}

<style>
  .topbar { border-bottom: 1px solid var(--line); background: var(--card); position: sticky; top: 0; z-index: 10; }
  .bar { display: flex; align-items: center; gap: 20px; padding-top: 12px; padding-bottom: 12px; }
  .brand { display: inline-flex; align-items: center; gap: 9px; color: var(--ink); }
  .brand:hover { text-decoration: none; }
  .stamp { color: var(--stamp); font-size: 20px; line-height: 1; }
  .title { font-family: var(--font-display); font-weight: 600; font-size: 18px; letter-spacing: -0.01em; }

  .nav { display: flex; gap: 16px; margin-right: auto; font-size: 13px; }
  .nav a { color: var(--muted); }
  .nav a:hover { color: var(--ink); text-decoration: none; }
  .rev { display: inline-flex; align-items: center; gap: 6px; }
  .badge {
    background: var(--stamp); color: #fff; font-size: 11px; line-height: 1;
    padding: 2px 6px; border-radius: 999px; font-weight: 600;
  }

  .live {
    display: inline-flex; align-items: center; gap: 7px;
    font-family: var(--font-mono); font-size: 12px; color: var(--muted);
    text-transform: uppercase; letter-spacing: 0.04em;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); }
  .live.on .dot { background: var(--teal); box-shadow: 0 0 0 3px color-mix(in srgb, var(--teal) 22%, transparent); }
</style>
