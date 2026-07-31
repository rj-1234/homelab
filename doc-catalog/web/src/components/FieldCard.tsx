import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Eye, EyeOff, Copy, Check, FileText, ExternalLink } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { revealField } from "@/api";
import type { VaultField, DocField } from "@/api";

// field: minimal shape both VaultField and per-doc DocField satisfy.
export function FieldCard({ field }: { field: VaultField | DocField }) {
  const [revealed, setRevealed] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => () => clearTimeout(timer.current), []);

  async function value(): Promise<string> {
    if (revealed == null) {
      const v = await revealField(field.id);
      setRevealed(v);
      return v;
    }
    return revealed;
  }

  function remask() {
    setRevealed(null);
    clearTimeout(timer.current);
  }

  async function toggleReveal() {
    if (revealed != null) {
      remask();
      return;
    }
    setBusy(true);
    try {
      await value();
      clearTimeout(timer.current);
      timer.current = setTimeout(remask, 15000);
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    setBusy(true);
    try {
      const v = await value();
      await navigator.clipboard.writeText(v);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
      clearTimeout(timer.current);
      timer.current = setTimeout(remask, 15000);
    } finally {
      setBusy(false);
    }
  }

  const shown = revealed != null;
  const expired = !!field.expiry && new Date(field.expiry) < new Date();
  const count = "doc_count" in field ? (field.doc_count ?? 0) : 0;
  const documentId = "document_id" in field ? field.document_id : undefined;
  const srcHref =
    count === 1
      ? `/doc/${documentId}`
      : `/library?field=${field.id}&label=${encodeURIComponent(field.label ?? "")}`;

  return (
    <Card
      className={cn(
        "gap-2 p-4 transition-shadow",
        shown && "border-vault/40 shadow-md",
        expired && "opacity-60",
      )}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="mono text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {field.label}
        </span>
        {field.expiry && (
          <span className={cn("mono text-[11px] tracking-wide text-muted-foreground/70", expired && "text-danger")}>
            {expired ? "expired" : "exp"} · {field.expiry}
          </span>
        )}
      </div>

      <div className="mt-1 flex items-center gap-2">
        <button
          type="button"
          onClick={toggleReveal}
          disabled={busy}
          title={shown ? "Hide" : "Reveal"}
          className={cn(
            "mono flex h-10 min-w-0 flex-1 items-center overflow-hidden rounded-md px-3 text-left text-sm tracking-[0.14em] text-foreground transition-colors",
            "bg-foreground/[0.06] bg-[repeating-linear-gradient(-45deg,transparent_0_6px,color-mix(in_srgb,var(--foreground)_5%,transparent)_6px_12px)] hover:bg-foreground/[0.09]",
            shown && "bg-vault-wash bg-none text-vault tracking-[0.04em] shadow-[inset_0_-2px_0_var(--vault)]",
          )}
        >
          <span className="truncate">{revealed ?? field.value_masked}</span>
        </button>
        <div className="flex flex-none gap-1.5">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                onClick={toggleReveal}
                disabled={busy}
                aria-label={shown ? "Hide value" : "Reveal value"}
              >
                {shown ? <EyeOff /> : <Eye />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{shown ? "Hides again in 15s" : "Reveal (auto-hides in 15s)"}</TooltipContent>
          </Tooltip>
          <Button
            variant="outline"
            size="icon"
            onClick={copy}
            disabled={busy}
            aria-label="Copy value"
            className={cn(copied && "border-vault text-vault bg-vault-wash")}
          >
            {copied ? <Check /> : <Copy />}
          </Button>
        </div>
      </div>

      {count > 0 && (
        <Link
          to={srcHref}
          className="mono mt-1 inline-flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-accent"
        >
          {count === 1 ? <FileText className="size-3.5" /> : <ExternalLink className="size-3.5" />}
          {count === 1 ? "View source" : `${count} documents`}
        </Link>
      )}
    </Card>
  );
}
