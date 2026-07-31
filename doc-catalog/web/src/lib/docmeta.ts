// Small display helpers for document rows/detail — dependency-free so DocCard
// and the detail page can both use them without pulling in a lib.

export function fmtBytes(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "";
  if (n < 1024) return `${n} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let v = n / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v < 10 ? 1 : 0)} ${units[i]}`;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "";
  // Accept "YYYY-MM-DDTHH:MM:SS..." or "YYYY-MM-DD ..." without pulling in a TZ lib.
  const m = String(iso).match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : String(iso);
}

// Returns a lucide-react icon name, not an emoji.
const ICONS: [RegExp, string][] = [
  [/^image\//, "Image"],
  [/sheet|excel|officedocument\.spreadsheetml/, "Sheet"],
  [
    /pdf|word|msword|officedocument\.wordprocessingml|text|presentation|powerpoint|officedocument\.presentationml/,
    "FileText",
  ],
];

export function fileIcon(mime: string | null | undefined): "Image" | "Sheet" | "FileText" | "File" {
  if (!mime) return "File";
  for (const [re, name] of ICONS) if (re.test(mime)) return name as "Image" | "Sheet" | "FileText";
  return "File";
}

export interface HighlightSegment {
  text: string;
  hl: boolean;
}

// Split a snippet containing @@HL@@..@@EHL@@ markers into text segments so the
// caller can render them as text nodes (never dangerouslySetInnerHTML — the
// source is untrusted document text, not markup we control).
export function highlight(snippet: string | null | undefined): HighlightSegment[] {
  if (!snippet) return [];
  const parts = snippet.split(/(@@HL@@.*?@@EHL@@)/gs);
  const out: HighlightSegment[] = [];
  for (const part of parts) {
    if (!part) continue;
    if (part.startsWith("@@HL@@") && part.endsWith("@@EHL@@")) {
      out.push({ text: part.slice(6, -7), hl: true });
    } else {
      out.push({ text: part, hl: false });
    }
  }
  return out;
}
