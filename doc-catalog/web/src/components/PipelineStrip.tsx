import { CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Job } from "@/api";

// Compact, display-only stage strip for the doc detail page. Mirrors the
// shape of JobQueue's status vocabulary (pending/running/done/failed) but
// scoped to a single document's jobs.
const LABELS: Record<string, string> = { text: "text", ocr: "ocr", embed: "tag" };

function stateOf(jobs: Job[], stage: string): "failed" | "active" | "done" | "todo" {
  const rows = jobs.filter((j) => j.stage === stage);
  if (rows.some((r) => r.state === "failed")) return "failed";
  if (rows.some((r) => r.state === "pending" || r.state === "running")) return "active";
  if (rows.some((r) => r.state === "done")) return "done";
  return "todo";
}

export function PipelineStrip({ jobs = [], status }: { jobs?: Job[]; status?: string }) {
  const showOcr = jobs.some((j) => j.stage === "ocr") || status === "needs_ocr" || status === "ocr_failed";
  const stages = ["text", ...(showOcr ? ["ocr"] : []), "embed"].map((stage) => ({
    stage,
    label: LABELS[stage] ?? stage,
    state: stateOf(jobs, stage),
  }));

  const allQuiet = stages.every((s) => s.state !== "active" && s.state !== "failed");
  const isDone = status === "tagged" && allQuiet;

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2">
      {stages.map((s) => (
        <span
          key={s.stage}
          className={cn(
            "mono inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11.5px] uppercase tracking-wide text-muted-foreground",
            s.state === "todo" && "opacity-55",
            s.state === "active" && "border-accent/45 bg-accent/10 text-accent",
            s.state === "done" && "text-muted-foreground",
            s.state === "failed" && "border-danger/45 bg-danger-wash text-danger",
          )}
        >
          <span
            className={cn(
              "size-1.5 rounded-full bg-current opacity-60",
              s.state === "active" && "animate-pulse opacity-100",
              s.state === "done" && "bg-vault opacity-80",
            )}
          />
          {s.label}
        </span>
      ))}
      {isDone && (
        <span className="inline-flex items-center gap-1.5 text-sm text-vault">
          <CheckCircle2 className="size-3.5" /> Done
        </span>
      )}
    </div>
  );
}
