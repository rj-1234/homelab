<script>
  import '../app.css';
  import { connected } from '$lib/status.js';
  let { children } = $props();
</script>

<header class="topbar">
  <div class="bar wrap">
    <a class="brand" href="/">
      <span class="stamp">◗</span>
      <span class="title">Document Catalog</span>
    </a>
    <span class="live" class:on={$connected} title={$connected ? 'Live' : 'Reconnecting…'}>
      <span class="dot"></span>{$connected ? 'live' : 'offline'}
    </span>
  </div>
</header>

{@render children()}

<style>
  .topbar { border-bottom: 1px solid var(--line); background: var(--card); }
  .bar { display: flex; align-items: center; justify-content: space-between; padding-top: 14px; padding-bottom: 14px; }
  .brand { display: inline-flex; align-items: center; gap: 10px; color: var(--ink); }
  .brand:hover { text-decoration: none; }
  .stamp { color: var(--stamp); font-size: 20px; line-height: 1; }
  .title { font-family: var(--font-display); font-weight: 600; font-size: 18px; letter-spacing: -.01em; }
  .live {
    display: inline-flex; align-items: center; gap: 7px;
    font-family: var(--font-mono); font-size: 12px; color: var(--muted);
    text-transform: uppercase; letter-spacing: .04em;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); }
  .live.on .dot { background: var(--teal); box-shadow: 0 0 0 3px color-mix(in srgb, var(--teal) 22%, transparent); }
</style>
