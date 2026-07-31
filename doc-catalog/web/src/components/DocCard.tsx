import { Link } from "react-router-dom";
import { FileText, Image, Sheet, File, ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { fmtBytes, fmtDate, fileIcon, highlight } from "@/lib/docmeta";
import type { Doc } from "@/api";

const ICONS = { FileText, Image, Sheet, File };

export function DocCard({ doc, snippet = null }: { doc: Doc; snippet?: string | null }) {
  const TAG_CAP = 4;
  const tags = doc.tags ?? [];
  const shownTags = tags.slice(0, TAG_CAP);
  const extraTags = Math.max(0, tags.length - TAG_CAP);
  const segments = highlight(snippet);
  const Icon = ICONS[fileIcon(doc.mime)];

  return (
    <Link to={`/doc/${doc.id}`}>
      <Card className="flex-row items-start gap-3 p-4 transition-shadow hover:shadow-lg">
        <span className="flex size-10 flex-none items-center justify-center rounded-[10px] border border-accent/20 bg-accent/10 text-accent">
          <Icon className="size-[19px]" strokeWidth={1.6} />
        </span>
        <span className="flex min-w-0 flex-1 flex-col gap-1">
          <span className="line-clamp-2 font-semibold leading-tight tracking-tight break-words">
            {doc.title || "Untitled document"}
          </span>
          <span className="mono text-xs text-muted-foreground [overflow-wrap:anywhere]">
            {fmtDate(doc.created_at)}
            {doc.pages != null && ` · ${doc.pages} p${doc.pages !== 1 ? "p" : ""}`}
            {doc.size != null && ` · ${fmtBytes(doc.size)}`}
            {doc.doc_type && ` · ${doc.doc_type}`}
          </span>

          {segments.length > 0 && (
            <span className="mt-0.5 line-clamp-2 text-sm text-foreground/80 break-words">
              {segments.map((seg, i) =>
                seg.hl ? (
                  <mark key={i} className="rounded-sm bg-accent/25 px-0.5 text-foreground">
                    {seg.text}
                  </mark>
                ) : (
                  <span key={i}>{seg.text}</span>
                ),
              )}
            </span>
          )}

          {tags.length > 0 && (
            <span className="mt-1 flex flex-wrap gap-1.5">
              {shownTags.map((t) => (
                <span
                  key={t}
                  className="mono rounded-full border border-accent/15 bg-accent/10 px-2.5 py-0.5 text-[11px] leading-tight text-accent"
                >
                  {t}
                </span>
              ))}
              {extraTags > 0 && (
                <span className="mono rounded-full border bg-muted px-2.5 py-0.5 text-[11px] leading-tight text-muted-foreground">
                  +{extraTags}
                </span>
              )}
            </span>
          )}
        </span>
        <ChevronRight className="mt-1 size-4 flex-none self-center text-muted-foreground/60 max-[480px]:hidden" />
      </Card>
    </Link>
  );
}
