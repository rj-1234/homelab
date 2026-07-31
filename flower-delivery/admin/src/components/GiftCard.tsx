import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Copy, Check, ExternalLink, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { deleteGift, type Gift, type GiftStatus } from "@/api";

const PUBLIC_BASE_URL = "https://flowers.ch33ky.org";

const STATUS_META: Record<GiftStatus, { label: string; className: string }> = {
  not_opened: { label: "Not opened", className: "bg-muted text-muted-foreground" },
  live: { label: "Live", className: "bg-success text-success-foreground" },
  expired: { label: "Expired", className: "" },
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function formatRelative(iso: string | null): string {
  if (!iso) return "—";
  const diffMs = new Date(iso).getTime() - Date.now();
  const future = diffMs > 0;
  const abs = Math.abs(diffMs);
  const min = Math.round(abs / 60_000);
  const hr = Math.round(abs / 3_600_000);
  const day = Math.round(abs / 86_400_000);
  if (min < 1) return "just now";
  const mag = min < 60 ? `${min}m` : hr < 24 ? `${hr}h` : `${day}d`;
  return future ? `in ${mag}` : `${mag} ago`;
}

function formatLifetime(ms: number): string {
  const hours = ms / 3_600_000;
  if (hours % 24 === 0) {
    const days = hours / 24;
    return days === 1 ? "1 day" : `${days} days`;
  }
  return `${hours} hours`;
}

function speciesLabel(species: string): string {
  return species.charAt(0).toUpperCase() + species.slice(1);
}

const AVATAR_TONES = [
  "bg-primary/10 text-primary",
  "bg-secondary/10 text-secondary",
  "bg-accent/10 text-accent",
  "bg-success/10 text-success",
];
function avatarTone(name: string): string {
  const code = name.trim().charCodeAt(0) || 0;
  return AVATAR_TONES[code % AVATAR_TONES.length];
}

interface GiftCardProps {
  gift: Gift;
  onDeleted: (id: string) => void;
}

export function GiftCard({ gift, onDeleted }: GiftCardProps) {
  const [deleting, setDeleting] = useState(false);
  const [copied, setCopied] = useState(false);
  const shareUrl = `${PUBLIC_BASE_URL}/g/${gift.id}`;
  const initial = (gift.sender || "?").trim().charAt(0).toUpperCase() || "?";
  const noteCount = gift.stems.filter((s) => s.note?.trim()).length;
  const statusMeta = STATUS_META[gift.status];

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteGift(gift.id);
      toast.success(`Deleted ${gift.sender || "that"}'s gift`);
      onDeleted(gift.id);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not delete this gift.");
      setDeleting(false);
    }
  }

  function handleCopy() {
    navigator.clipboard.writeText(shareUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    });
  }

  return (
    <Card className="gift-card gap-4 py-5">
      <CardHeader className="px-5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Avatar>
              <AvatarFallback className={avatarTone(gift.sender || "?")}>{initial}</AvatarFallback>
            </Avatar>
            <div className="flex flex-col">
              <span className="font-semibold leading-tight">{gift.sender || "—"}</span>
              <span className="text-xs text-muted-foreground">
                {formatRelative(gift.created_at)} · {formatLifetime(gift.lifetime_ms)}
              </span>
            </div>
          </div>
          {gift.status === "expired" ? (
            <Badge variant="destructive">Expired</Badge>
          ) : (
            <Badge className={statusMeta.className}>{statusMeta.label}</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 px-5">
        <p className="line-clamp-2 text-sm text-foreground/90">{gift.message}</p>
        <div className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
          <span>{gift.stems.map((s) => speciesLabel(s.species)).join(", ")}</span>
          {noteCount > 0 && (
            <Badge variant="outline" className="ml-1 h-4 px-1.5 text-[10px]">
              {noteCount} note{noteCount === 1 ? "" : "s"}
            </Badge>
          )}
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Opened {formatDate(gift.opened_at)}</span>
          <span>Expires {formatRelative(gift.expires_at)}</span>
        </div>
        <div className="flex items-center gap-2 pt-1">
          <Button variant="outline" size="sm" onClick={handleCopy}>
            {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
            {copied ? "Copied" : "Copy link"}
          </Button>
          <Button variant="ghost" size="sm" asChild>
            <a href={`${shareUrl}?dev=1`} target="_blank" rel="noreferrer">
              <ExternalLink className="size-3.5" /> Open
            </a>
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                className="ml-auto text-destructive hover:bg-destructive/10 hover:text-destructive"
                disabled={deleting}
              >
                <Trash2 className="size-3.5" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this gift permanently?</AlertDialogTitle>
                <AlertDialogDescription>
                  The link will stop working immediately for {gift.sender || "the recipient"} and this
                  can't be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleDelete} className="bg-destructive text-white hover:bg-destructive/90">
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
}
