<script>
  import { fmtBytes, fmtDate, fileIcon, highlight } from '$lib/docmeta.js';
  import Icon from '$lib/Icon.svelte';

  // doc: { id, title, status, doc_type, mime, size, created_at, sha, pages, tags }
  // snippet: string|null with @@HL@@/@@EHL@@ markers (search mode only)
  let { doc, snippet = null } = $props();

  const TAG_CAP = 4;
  const tags = $derived(doc.tags ?? []);
  const shownTags = $derived(tags.slice(0, TAG_CAP));
  const extraTags = $derived(Math.max(0, tags.length - TAG_CAP));
  const segments = $derived(highlight(snippet));
</script>

<a class="doc card" href={`/doc/${doc.id}`}>
  <span class="icon" aria-hidden="true"><Icon name={fileIcon(doc.mime)} size="19px" stroke={1.6} /></span>
  <span class="body">
    <span class="title">{doc.title || 'Untitled document'}</span>
    <span class="meta mono">
      {fmtDate(doc.created_at)}{#if doc.pages != null} · {doc.pages} p{#if doc.pages !== 1}p{/if}{/if}{#if doc.size != null} · {fmtBytes(doc.size)}{/if}{#if doc.doc_type} · {doc.doc_type}{/if}
    </span>

    {#if segments.length}
      <span class="snippet">
        {#each segments as seg, i (i)}
          {#if seg.hl}<mark>{seg.text}</mark>{:else}{seg.text}{/if}
        {/each}
      </span>
    {/if}

    {#if tags.length}
      <span class="tags">
        {#each shownTags as t}<span class="tag mono">{t}</span>{/each}
        {#if extraTags > 0}<span class="tag more mono">+{extraTags}</span>{/if}
      </span>
    {/if}
  </span>
  <span class="chev" aria-hidden="true"><Icon name="chevron-right" size="16px" /></span>
</a>

<style>
  .doc {
    display: flex; gap: 13px; align-items: flex-start;
    padding: 14px 14px 15px; min-height: 44px; color: var(--ink);
    transition: border-color .18s ease, box-shadow .18s ease, transform .06s ease;
  }
  .doc:hover {
    text-decoration: none;
    border-color: color-mix(in srgb, var(--blue) 42%, var(--line));
    box-shadow: var(--shadow-lg);
  }
  .doc:hover .chev { color: var(--blue); transform: translateX(2px); }

  /* documents wear a quiet --blue identity through the icon chip, not a side rule */
  .icon {
    flex: none; width: 40px; height: 40px; display: grid; place-items: center;
    border-radius: 10px; color: var(--blue);
    background: var(--blue-wash);
    border: 1px solid color-mix(in srgb, var(--blue) 18%, var(--line));
  }

  .body { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1; }

  .title {
    font-family: var(--font-display); font-weight: 500; font-size: 1.0625rem;
    line-height: 1.25; letter-spacing: -0.005em;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow: hidden; word-break: break-word;
  }

  .meta { font-size: var(--t-sm); color: var(--muted); overflow-wrap: anywhere; }

  .snippet {
    font-size: 0.8125rem; color: var(--ink-2); margin-top: 2px;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow: hidden; word-break: break-word;
  }
  .snippet mark {
    background: color-mix(in srgb, var(--blue) 24%, transparent);
    color: var(--ink); border-radius: 3px; padding: 0 3px;
  }

  .tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
  .tag {
    font-size: 0.6875rem; color: var(--blue);
    background: var(--blue-wash);
    border: 1px solid color-mix(in srgb, var(--blue) 16%, var(--line));
    border-radius: var(--radius-pill); padding: 2px 9px; line-height: 1.35;
  }
  .tag.more { color: var(--muted); background: var(--paper-2); border-color: var(--line); }

  .chev { flex: none; align-self: center; color: var(--faint); transition: color .15s ease, transform .15s ease; }
  @media (max-width: 480px) { .chev { display: none; } }
</style>
