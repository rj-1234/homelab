import { useState } from "react";
import { Link } from "react-router-dom";
import { Eye, EyeOff, Check, Pencil, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { revealField, confirmField, deleteField } from "@/api";
import type { ReviewCandidate } from "@/api";

export function ReviewRow({ row, ondone }: { row: ReviewCandidate; ondone: (id: string) => void }) {
  const [shown, setShown] = useState(row.value_masked);
  const [revealed, setRevealed] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  async function reveal() {
    if (revealed) return;
    setShown(await revealField(row.id));
    setRevealed(true);
  }

  async function startEdit() {
    if (!revealed) await reveal();
    setDraft(revealed ? shown : await revealField(row.id));
    setEditing(true);
  }

  async function confirm() {
    setBusy(true);
    try {
      await confirmField(row.id, editing && draft.trim() ? { value: draft.trim() } : null);
      ondone(row.id);
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    setBusy(true);
    try {
      await deleteField(row.id);
      ondone(row.id);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid grid-cols-[1fr_1.2fr_auto] items-center gap-3 border-t px-4 py-3 first:border-t-0 max-[560px]:grid-cols-1 max-[560px]:gap-2">
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="text-xs uppercase tracking-wide text-muted-foreground">{row.label}</span>
        <Link
          to={`/doc/${row.document_id}`}
          title={row.title}
          className="truncate text-sm text-muted-foreground hover:text-accent"
        >
          {row.title}
        </Link>
      </div>

      <div className="min-w-0">
        {editing ? (
          <Input className="mono" value={draft} onChange={(e) => setDraft(e.target.value)} spellCheck={false} />
        ) : (
          <button
            type="button"
            onClick={reveal}
            title={revealed ? "" : "Reveal to check"}
            className={cn(
              "mono flex w-full items-center gap-2 rounded-md bg-foreground/[0.06] px-2.5 py-1.5 text-left tracking-[0.1em] text-muted-foreground transition-colors hover:bg-foreground/[0.09]",
              revealed && "bg-vault-wash tracking-[0.03em] text-vault",
            )}
          >
            {revealed ? <EyeOff className="size-3.5 flex-none" /> : <Eye className="size-3.5 flex-none" />}
            <span className="truncate">{shown}</span>
          </button>
        )}
      </div>

      <div className="flex justify-end gap-1.5 max-[560px]:justify-end">
        <Button
          variant="outline"
          size="icon"
          onClick={confirm}
          disabled={busy}
          aria-label="Confirm"
          className="hover:border-vault hover:bg-vault-wash hover:text-vault"
        >
          <Check />
        </Button>
        <Button variant="outline" size="icon" onClick={startEdit} disabled={busy} aria-label="Edit value">
          <Pencil />
        </Button>
        <Button
          variant="outline"
          size="icon"
          onClick={reject}
          disabled={busy}
          aria-label="Not a field / reject"
          className="hover:border-danger hover:bg-danger-wash hover:text-danger"
        >
          <X />
        </Button>
      </div>
    </div>
  );
}
