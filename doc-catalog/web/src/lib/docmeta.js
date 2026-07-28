// Small display helpers for document rows/detail — kept dependency-free so
// DocCard and the detail page can both use them without pulling in a lib.

export function fmtBytes(n) {
  if (n == null || Number.isNaN(n)) return '';
  if (n < 1024) return `${n} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let v = n / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(v < 10 ? 1 : 0)} ${units[i]}`;
}

export function fmtDate(iso) {
  if (!iso) return '';
  // Accept "YYYY-MM-DDTHH:MM:SS..." or "YYYY-MM-DD ..." without pulling in a TZ lib.
  const m = String(iso).match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : String(iso);
}

// Returns an Icon.svelte name (SVG line icon), not an emoji.
const ICONS = [
  [/^image\//, 'image'],
  [/sheet|excel|officedocument\.spreadsheetml/, 'sheet'],
  [/pdf|word|msword|officedocument\.wordprocessingml|text|presentation|powerpoint|officedocument\.presentationml/, 'file-text']
];

export function fileIcon(mime) {
  if (!mime) return 'file';
  for (const [re, name] of ICONS) if (re.test(mime)) return name;
  return 'file';
}

// Split a snippet containing @@HL@@..@@EHL@@ markers into text segments so the
// caller can render them as text nodes (never {@html} — the source is untrusted
// document text, not markup we control).
export function highlight(snippet) {
  if (!snippet) return [];
  const parts = snippet.split(/(@@HL@@.*?@@EHL@@)/gs);
  const out = [];
  for (const part of parts) {
    if (!part) continue;
    if (part.startsWith('@@HL@@') && part.endsWith('@@EHL@@')) {
      out.push({ text: part.slice(6, -7), hl: true });
    } else {
      out.push({ text: part, hl: false });
    }
  }
  return out;
}
