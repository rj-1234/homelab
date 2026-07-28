<script>
  import '../app.css';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { status, connected } from '$lib/status.js';
  import { theme, toggleTheme } from '$lib/theme.js';
  import Icon from '$lib/Icon.svelte';
  let { children } = $props();

  // reflect the OS preference so the toggle icon is right even when unpinned
  let systemDark = $state(false);
  onMount(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    systemDark = mq.matches;
    const on = (e) => (systemDark = e.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  });
  const isDark = $derived($theme ? $theme === 'dark' : systemDark);

  const review = $derived($status?.fields?.review ?? 0);
  const path = $derived($page.url.pathname);
  const active = (href) => (href === '/' ? path === '/' : path.startsWith(href));

  // one source of truth for header tabs + mobile bottom bar
  const nav = [
    { href: '/', label: 'Vault', icon: 'shield' },
    { href: '/library', label: 'Library', icon: 'file-text' },
    { href: '/review', label: 'Review', icon: 'inbox', badge: true },
    { href: '/status', label: 'Status', icon: 'activity' }
  ];
</script>

<header class="topbar">
  <div class="bar wrap">
    <a class="brand" href="/" aria-label="Field Vault — home">
      <span class="seal"><Icon name="shield" size="20px" stroke={1.6} /></span>
      <span class="word">
        <span class="name">The Archive</span>
        <span class="sub mono">field vault</span>
      </span>
    </a>

    <nav class="nav desktop" aria-label="Primary">
      {#each nav as n}
        <a href={n.href} class="tab" class:on={active(n.href)}>
          <span>{n.label}</span>
          {#if n.badge && review > 0}<span class="badge mono">{review}</span>{/if}
        </a>
      {/each}
    </nav>

    <span class="live mono" class:on={$connected} title={$connected ? 'Live updates connected' : 'Reconnecting…'}>
      <span class="dot"></span><span class="lbl">{$connected ? 'live' : 'offline'}</span>
    </span>

    <button class="themebtn" onclick={toggleTheme} type="button"
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            title={isDark ? 'Light mode' : 'Dark mode'}>
      <Icon name={isDark ? 'sun' : 'moon'} size="17px" />
    </button>
  </div>
</header>

{@render children()}

<!-- mobile: bottom tab bar for thumb-reach navigation -->
<nav class="tabbar" aria-label="Primary">
  {#each nav as n}
    <a href={n.href} class="btab" class:on={active(n.href)}>
      <span class="bico">
        <Icon name={n.icon} size="21px" stroke={active(n.href) ? 2 : 1.6} />
        {#if n.badge && review > 0}<span class="bbadge mono">{review > 9 ? '9+' : review}</span>{/if}
      </span>
      <span class="blabel">{n.label}</span>
    </a>
  {/each}
</nav>

<style>
  .topbar {
    position: sticky; top: 0; z-index: 20;
    background: color-mix(in srgb, var(--paper) 86%, transparent);
    backdrop-filter: saturate(1.4) blur(10px);
    border-bottom: 1px solid var(--line);
  }
  .bar {
    display: flex; align-items: center; gap: var(--s-5);
    padding-top: var(--s-3); padding-bottom: var(--s-3);
  }

  .brand { display: inline-flex; align-items: center; gap: var(--s-3); color: var(--ink); margin-right: auto; }
  .brand:hover { text-decoration: none; }
  .seal {
    display: grid; place-items: center; width: 34px; height: 34px; flex: none;
    color: var(--teal); border-radius: 10px;
    background: var(--teal-wash);
    border: 1px solid color-mix(in srgb, var(--teal) 24%, var(--line));
  }
  .word { display: flex; flex-direction: column; line-height: 1; }
  .name { font-family: var(--font-display); font-weight: 500; font-size: 1.2rem; letter-spacing: -0.01em; }
  .sub { font-size: 0.625rem; text-transform: uppercase; letter-spacing: 0.22em; color: var(--faint); margin-top: 3px; }

  .nav.desktop { display: flex; align-items: center; gap: var(--s-2); }
  .tab {
    display: inline-flex; align-items: center; gap: var(--s-2);
    padding: 7px 12px; border-radius: var(--radius-pill);
    font-family: var(--font-mono); font-size: var(--t-sm); font-weight: 500;
    color: var(--muted); letter-spacing: 0.01em;
    transition: color .15s ease, background .15s ease;
  }
  .tab:hover { color: var(--ink); text-decoration: none; background: var(--paper-2); }
  .tab.on { color: var(--teal); background: var(--teal-wash); }
  .badge {
    min-width: 18px; height: 18px; padding: 0 5px; display: inline-grid; place-items: center;
    background: var(--stamp); color: #fff; font-size: 0.6875rem; font-weight: 500;
    border-radius: var(--radius-pill); line-height: 1;
  }

  .live {
    display: inline-flex; align-items: center; gap: 7px; flex: none; margin-left: var(--s-4);
    font-size: 0.6875rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--faint);
  }
  .dot {
    width: 7px; height: 7px; border-radius: 50%; background: var(--faint);
    transition: background .2s ease, box-shadow .2s ease;
  }
  .live.on .dot {
    background: var(--teal);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--teal) 20%, transparent);
  }

  .themebtn {
    flex: none; display: grid; place-items: center;
    width: 36px; height: 36px; margin-left: var(--s-3);
    border: 1px solid var(--line); border-radius: var(--radius-pill);
    background: var(--card); color: var(--muted); cursor: pointer;
    transition: color .15s ease, border-color .15s ease, background .15s ease;
  }
  .themebtn:hover { color: var(--teal); border-color: var(--teal); background: var(--teal-wash); }

  /* bottom tab bar — hidden on desktop, shown on mobile */
  .tabbar { display: none; }

  @media (max-width: 620px) {
    .nav.desktop { display: none; }
    .brand .sub { display: none; }
    .live .lbl { display: none; }
    .live { margin-left: auto; }

    .tabbar {
      display: grid; grid-template-columns: repeat(4, 1fr);
      position: fixed; left: 0; right: 0; bottom: 0; z-index: 30;
      background: color-mix(in srgb, var(--paper) 94%, transparent);
      backdrop-filter: saturate(1.4) blur(12px);
      border-top: 1px solid var(--line);
      padding-bottom: env(safe-area-inset-bottom);
    }
    .btab {
      display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px;
      padding: 9px 0 8px; min-height: 54px; color: var(--muted);
      font-family: var(--font-mono); font-size: 0.625rem; letter-spacing: 0.03em;
    }
    .btab:hover { text-decoration: none; }
    .btab.on { color: var(--teal); }
    .bico { position: relative; display: grid; place-items: center; }
    .bico::after {
      content: ""; position: absolute; inset: -6px -10px; border-radius: var(--radius-pill);
      background: transparent; transition: background .15s ease; z-index: -1;
    }
    .btab.on .bico::after { background: var(--teal-wash); }
    .blabel { line-height: 1; }
    .bbadge {
      position: absolute; top: -6px; right: -9px;
      min-width: 15px; height: 15px; padding: 0 4px; display: grid; place-items: center;
      background: var(--stamp); color: #fff; font-size: 0.5625rem; font-weight: 500;
      border-radius: var(--radius-pill); line-height: 1;
    }
    /* keep page content clear of the fixed bar */
    :global(body) { padding-bottom: calc(58px + env(safe-area-inset-bottom)); }
  }
</style>
