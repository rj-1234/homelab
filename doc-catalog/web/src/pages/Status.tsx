import { useEffect, useState } from "react";
import { X, Plus } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { JobQueue } from "@/components/JobQueue";
import { cn } from "@/lib/utils";
import { useStatus } from "@/lib/status";
import { listSenderRules, addSenderRule, delSenderRule } from "@/api";
import type { SenderRule } from "@/api";

interface FormEntry {
  pattern: string;
  action: "allow" | "deny";
}

export function Status() {
  const { status } = useStatus();
  const docs = status?.documents ?? 0;
  const sources = status?.sources ?? [];
  const accounts = status?.accounts ?? [];
  const vault = status?.fields ?? { confirmed: 0, review: 0 };

  const [rules, setRules] = useState<SenderRule[]>([]);
  const [ruleError, setRuleError] = useState("");
  const [formState, setFormState] = useState<Record<string, FormEntry>>({});
  const [addingId, setAddingId] = useState<string | null>(null);
  const [removingKey, setRemovingKey] = useState<string | null>(null);

  async function loadRules() {
    try {
      setRules(await listSenderRules());
      setRuleError("");
    } catch (e) {
      setRuleError(String((e as Error).message ?? e));
    }
  }
  useEffect(() => {
    loadRules();
  }, []);

  // Ensure each account has a form entry once accounts arrive/change.
  useEffect(() => {
    setFormState((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const a of accounts) {
        if (!next[a.id]) {
          next[a.id] = { pattern: "", action: "allow" };
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [accounts]);

  function rulesFor(accountId: string) {
    return rules.filter((r) => r.account_id === accountId);
  }
  function ruleKey(r: SenderRule) {
    return `${r.account_id}|${r.pattern}|${r.action}`;
  }
  function formFor(accountId: string): FormEntry {
    return formState[accountId] ?? { pattern: "", action: "allow" };
  }
  function setForm(accountId: string, patch: Partial<FormEntry>) {
    setFormState((prev) => ({ ...prev, [accountId]: { ...formFor(accountId), ...patch } }));
  }

  async function addRule(accountId: string) {
    const f = formFor(accountId);
    const pattern = f.pattern.trim();
    if (!pattern) return;
    setAddingId(accountId);
    try {
      await addSenderRule({ account_id: accountId, pattern, action: f.action });
      setForm(accountId, { pattern: "" });
      await loadRules();
    } catch (e) {
      setRuleError(String((e as Error).message ?? e));
    } finally {
      setAddingId(null);
    }
  }

  async function removeRule(r: SenderRule) {
    setRemovingKey(ruleKey(r));
    try {
      await delSenderRule({ account_id: r.account_id, pattern: r.pattern, action: r.action });
      await loadRules();
    } catch (e) {
      setRuleError(String((e as Error).message ?? e));
    } finally {
      setRemovingKey(null);
    }
  }

  return (
    <main className="mx-auto max-w-[1040px] px-5 pt-6 pb-16">
      <h1 className="mb-6 text-3xl font-semibold tracking-tight">Status</h1>

      <div className="mb-8 grid grid-cols-[repeat(auto-fill,minmax(130px,1fr))] gap-4">
        <Card className="gap-1 p-4">
          <div className="text-2xl font-bold leading-none tracking-tight">{docs}</div>
          <div className="mono mt-1 text-xs uppercase tracking-wide text-muted-foreground">documents</div>
        </Card>
        <Card className="gap-1 p-4">
          <div className="text-2xl font-bold leading-none tracking-tight">{vault.confirmed}</div>
          <div className="mono mt-1 text-xs uppercase tracking-wide text-muted-foreground">vault fields</div>
        </Card>
        <Card className="gap-1 p-4">
          <div className="text-2xl font-bold leading-none tracking-tight">{vault.review}</div>
          <div className="mono mt-1 text-xs uppercase tracking-wide text-muted-foreground">to review</div>
        </Card>
        {sources.map((s) => (
          <Card key={s.source} className="gap-1 p-4">
            <div className="text-2xl font-bold leading-none tracking-tight">{s.n}</div>
            <div className="mono mt-1 text-xs uppercase tracking-wide text-muted-foreground">{s.source}</div>
          </Card>
        ))}
      </div>

      <JobQueue />

      {accounts.length > 0 && (
        <>
          <section className="mt-8">
            <h2 className="eyebrow">Gmail</h2>
            <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-4">
              {accounts.map((a) => (
                <Card key={a.id} className="gap-3 p-4">
                  <div className="font-medium">{a.email}</div>
                  <div className="mono text-sm text-muted-foreground">
                    {a.synced ? "synced" : "not synced"} · {a.attachments} attachment{a.attachments === 1 ? "" : "s"}
                  </div>
                </Card>
              ))}
            </div>
          </section>

          <section className="mt-8">
            <h2 className="eyebrow">Sender rules</h2>
            <p className="mb-4 max-w-[60ch] text-sm text-muted-foreground">
              Allow or deny senders so ingest skips what you don't want catalogued.
            </p>
            {ruleError && <p className="mb-3 text-danger">{ruleError}</p>}

            <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-4">
              {accounts.map((a) => (
                <Card key={a.id} className="gap-3 p-4">
                  <div className="font-medium">{a.email}</div>

                  {rulesFor(a.id).length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {rulesFor(a.id).map((r) => (
                        <span
                          key={ruleKey(r)}
                          className={cn(
                            "inline-flex items-center gap-1.5 rounded-full border py-1 pr-1 pl-3 text-sm",
                            r.action === "allow"
                              ? "border-vault/35 bg-vault-wash text-vault"
                              : "border-danger/35 bg-danger-wash text-danger",
                          )}
                        >
                          <span className="mono">{r.pattern}</span>
                          <button
                            type="button"
                            onClick={() => removeRule(r)}
                            disabled={removingKey === ruleKey(r)}
                            aria-label={`Remove rule ${r.pattern}`}
                            className="flex size-[22px] items-center justify-center rounded-full opacity-75 transition-opacity hover:bg-current/15 hover:opacity-100 disabled:opacity-40"
                          >
                            <X className="size-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No rules yet.</p>
                  )}

                  <div className="flex flex-wrap gap-2 max-[480px]:flex-col max-[480px]:items-stretch">
                    <Input
                      placeholder="sender or domain pattern"
                      value={formFor(a.id).pattern}
                      onChange={(e) => setForm(a.id, { pattern: e.target.value })}
                      className="min-w-0 flex-1 basis-40"
                    />
                    <Select
                      value={formFor(a.id).action}
                      onValueChange={(v: "allow" | "deny") => setForm(a.id, { action: v })}
                    >
                      <SelectTrigger className="w-24 flex-none">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="allow">Allow</SelectItem>
                        <SelectItem value="deny">Deny</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      onClick={() => addRule(a.id)}
                      disabled={addingId === a.id || !formFor(a.id).pattern.trim()}
                      className="flex-none"
                    >
                      <Plus className="size-3.5" />
                      {addingId === a.id ? "Adding…" : "Add"}
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
