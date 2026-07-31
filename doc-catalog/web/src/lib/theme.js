// Manual light/dark override on top of the OS preference.
// null  = follow the system (prefers-color-scheme)
// 'light' | 'dark' = user pinned it (persisted, wins over the OS)
// The <html data-theme> attribute is what the stylesheet keys off; a no-flash
// script in app.html sets it before first paint, and this store keeps it in sync.
import { writable } from 'svelte/store';

const KEY = 'vault-theme';

function stored() {
  if (typeof localStorage === 'undefined') return null;
  const v = localStorage.getItem(KEY);
  return v === 'light' || v === 'dark' ? v : null;
}

function apply(v) {
  if (typeof document === 'undefined') return;
  const el = document.documentElement;
  if (v) el.dataset.theme = v;
  else delete el.dataset.theme;
}

export const theme = writable(stored());

theme.subscribe((v) => {
  if (typeof localStorage !== 'undefined') {
    if (v) localStorage.setItem(KEY, v);
    else localStorage.removeItem(KEY);
  }
  apply(v);
});

// Resolve what's actually showing right now (pinned value, or the OS otherwise).
export function resolved(v) {
  if (v === 'light' || v === 'dark') return v;
  if (typeof window !== 'undefined' && window.matchMedia)
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  return 'light';
}

// Flip relative to what's currently on screen, then pin it.
export function toggleTheme() {
  theme.update((v) => (resolved(v) === 'dark' ? 'light' : 'dark'));
}
