import { readable } from 'svelte/store';

// Live pipeline status via Server-Sent Events (/api/events). One held connection,
// pushed on every job/document change — no polling. EventSource auto-reconnects
// on error, so a worker/api restart heals itself. `connected` tracks the link so
// the UI can show a live/offline dot.
function makeStatus() {
  let setConn;
  const connected = readable(false, (set) => { setConn = set; });

  const status = readable(/** @type {any} */ (null), (set) => {
    if (typeof EventSource === 'undefined') return; // SSR guard
    const es = new EventSource('/api/events');
    es.onopen = () => setConn?.(true);
    es.onmessage = (e) => {
      try { set(JSON.parse(e.data)); } catch { /* heartbeat / partial */ }
    };
    es.onerror = () => setConn?.(false); // browser retries automatically
    return () => es.close();
  });

  return { status, connected };
}

export const { status, connected } = makeStatus();
