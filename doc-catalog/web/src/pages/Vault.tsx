import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ChevronRight, Shield } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FieldCard } from "@/components/FieldCard";
import { intoGroups } from "@/lib/fields";
import { useStatus } from "@/lib/status";
import { listFields } from "@/api";
import type { VaultField } from "@/api";

export function Vault() {
  const [fields, setFields] = useState<VaultField[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { status } = useStatus();
  const review = status?.fields?.review ?? 0;

  async function load() {
    try {
      setFields(await listFields());
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  // Re-pull the shelf when the confirmed-count changes (a confirm over in
  // /review), so it stays live without polling. Guarded so it doesn't loop.
  const seenConfirmed = useRef<number | null>(null);
  useEffect(() => {
    const c = status?.fields?.confirmed;
    if (c != null && c !== seenConfirmed.current) {
      seenConfirmed.current = c;
      load();
    }
  }, [status?.fields?.confirmed]);

  const groups = intoGroups(fields);

  return (
    <main className="mx-auto max-w-[1040px] px-5 pt-6 pb-16">
      {review > 0 && (
        <Link
          to="/review"
          className="mb-6 flex items-center gap-3 rounded-xl border border-danger/25 bg-danger-wash px-4 py-3 text-sm transition-colors hover:border-danger"
        >
          <span className="flex size-[34px] flex-none items-center justify-center rounded-full bg-danger/15 text-danger">
            <AlertTriangle className="size-[18px]" />
          </span>
          <span className="flex-1">
            <strong className="font-semibold">{review}</strong> candidate{review === 1 ? "" : "s"} to confirm
          </span>
          <span className="mono inline-flex items-center gap-0.5 text-sm font-medium text-danger">
            Review <ChevronRight className="size-3.5" />
          </span>
        </Link>
      )}

      {loading ? (
        <p className="text-muted-foreground">Loading vault…</p>
      ) : error ? (
        <p className="text-danger">Couldn't load the vault: {error}</p>
      ) : fields.length === 0 ? (
        <Card className="items-center gap-4 px-5 py-14 text-center">
          <span className="flex size-14 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Shield className="size-[26px]" strokeWidth={1.5} />
          </span>
          <h2 className="text-xl font-semibold">Your vault is empty</h2>
          {review > 0 ? (
            <>
              <p className="mx-auto max-w-[44ch] text-muted-foreground">
                {review} field{review === 1 ? "" : "s"} were extracted from your documents. Confirm the ones you want
                and they'll appear here, copy-ready.
              </p>
              <Button asChild>
                <Link to="/review">
                  Review {review} candidates <ChevronRight className="size-3.5" />
                </Link>
              </Button>
            </>
          ) : (
            <p className="mx-auto max-w-[44ch] text-muted-foreground">
              Upload or sync documents — extracted fields will show up to confirm.
            </p>
          )}
        </Card>
      ) : (
        groups.map((g) => (
          <section key={g.title} className="mb-8">
            <h2 className="eyebrow">{g.title}</h2>
            <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-4">
              {g.fields.map((f) => (
                <FieldCard key={f.id} field={f} />
              ))}
            </div>
          </section>
        ))
      )}
    </main>
  );
}
