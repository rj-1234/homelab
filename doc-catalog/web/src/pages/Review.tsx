import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { ReviewRow } from "@/components/ReviewRow";
import { intoGroups } from "@/lib/fields";
import { listReview } from "@/api";
import type { ReviewCandidate } from "@/api";

export function Review() {
  const [rows, setRows] = useState<ReviewCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listReview()
      .then((r) => {
        setRows(r);
        setError("");
      })
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  }, []);

  // remove a row locally once confirmed/rejected (SSE updates the badge)
  function done(id: string) {
    setRows((r) => r.filter((row) => row.id !== id));
  }

  const groups = intoGroups(rows);

  return (
    <main className="mx-auto max-w-[1040px] px-5 pt-6 pb-16">
      <div className="mb-1 flex items-baseline justify-between">
        <h1 className="text-3xl font-semibold tracking-tight">Review</h1>
        <span className="mono text-sm text-muted-foreground">
          {rows.length} candidate{rows.length === 1 ? "" : "s"}
        </span>
      </div>
      <p className="mb-8 max-w-[66ch] text-sm text-muted-foreground">
        Confirm the fields worth keeping — they move to your vault. Reveal to check a value, edit if OCR got it
        wrong, or reject noise. Nothing shows on the shelf until you confirm.
      </p>

      {loading ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : error ? (
        <p className="text-danger">{error}</p>
      ) : rows.length === 0 ? (
        <Card className="items-center gap-4 px-5 py-14 text-center">
          <span className="flex size-14 items-center justify-center rounded-full bg-primary/10 text-primary">
            <CheckCircle2 className="size-[26px]" strokeWidth={1.5} />
          </span>
          <h2 className="text-xl font-semibold">Nothing to review</h2>
          <p className="text-muted-foreground">
            Every extracted field has been handled.{" "}
            <Link to="/" className="text-accent hover:underline">
              Back to the vault →
            </Link>
          </p>
        </Card>
      ) : (
        groups.map((g) => (
          <section key={g.title} className="mb-8">
            <h2 className="eyebrow">
              {g.title} · {g.fields.length}
            </h2>
            <Card className="gap-0 overflow-hidden py-0">
              {g.fields.map((r) => (
                <ReviewRow key={r.id} row={r} ondone={done} />
              ))}
            </Card>
          </section>
        ))
      )}
    </main>
  );
}
