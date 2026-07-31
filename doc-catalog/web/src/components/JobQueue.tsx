import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useStatus } from "@/lib/status";

const STAGES = ["text", "ocr", "embed", "embed_pages"] as const;
const STATES = ["running", "pending", "failed", "done"] as const;

export function JobQueue() {
  const { status } = useStatus();

  const byStage: Record<string, Record<string, number>> = {};
  for (const s of STAGES) byStage[s] = {};
  for (const row of status?.jobs ?? []) {
    (byStage[row.stage] ??= {})[row.state] = row.n ?? 0;
  }

  const active = (status?.jobs ?? [])
    .filter((r) => r.state === "pending" || r.state === "running")
    .reduce((a, r) => a + (r.n ?? 0), 0);

  return (
    <section>
      <h2 className="eyebrow">Pipeline · {active} active</h2>

      <div className="grid grid-cols-[repeat(auto-fill,minmax(180px,1fr))] gap-4">
        {STAGES.map((stage) => (
          <Card key={stage} className="gap-3 p-4">
            <div className="mono text-xs uppercase tracking-wide text-muted-foreground">{stage}</div>
            <div className="flex flex-wrap gap-1.5">
              {STATES.map((st) => {
                const n = byStage[stage]?.[st] ?? 0;
                return (
                  <span
                    key={st}
                    className={cn(
                      "mono inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 pl-2 text-[11px] text-muted-foreground",
                      n === 0 && "opacity-40",
                      st === "running" && n > 0 && "border-vault text-vault",
                      st === "failed" && n > 0 && "border-danger text-danger",
                    )}
                  >
                    <span
                      className={cn(
                        "size-1.5 flex-none rounded-full bg-muted-foreground/60",
                        st === "running" && "bg-vault",
                        st === "failed" && "bg-danger",
                      )}
                    />
                    <span className="font-semibold text-foreground">{n}</span>
                    {st}
                  </span>
                );
              })}
            </div>
          </Card>
        ))}
      </div>

      {!!status?.failures?.length && (
        <Card className="mt-4 gap-2 p-4">
          <div className="mono text-xs uppercase tracking-wide text-muted-foreground">failed jobs</div>
          {status.failures.map((f) => (
            <div key={f.id} className="flex items-center gap-3 border-t py-2 first:border-t-0">
              <span className="mono text-danger">
                #{f.id} {f.stage}
              </span>
              <span className="flex-1 truncate">{f.title}</span>
              <span className="mono text-muted-foreground">×{f.attempts}</span>
            </div>
          ))}
        </Card>
      )}
    </section>
  );
}
