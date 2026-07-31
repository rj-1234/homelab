import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, Filter, X, Inbox } from "lucide-react";
import { Card } from "@/components/ui/card";
import { DocCard } from "@/components/DocCard";
import { Uploader } from "@/components/Uploader";
import { cn } from "@/lib/utils";
import { listDocuments, listTags, getTaxonomy } from "@/api";
import type { Doc, Tag, StatusOption } from "@/api";

export function Library() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const [tag, setTag] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [fieldFilter, setFieldFilter] = useState(searchParams.get("field") ?? "");
  const [fieldLabel, setFieldLabel] = useState(searchParams.get("label") ?? "");
  const [tags, setTags] = useState<Tag[]>([]);
  const [statuses, setStatuses] = useState<StatusOption[]>([]);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const searching = query.trim().length > 0;
  const debounceTimer = useRef<ReturnType<typeof setTimeout>>();
  const reqId = useRef(0);

  async function load(opts: { q?: string; tag?: string; status?: string; field?: string }) {
    const my = ++reqId.current;
    setLoading(true);
    try {
      const q = (opts.q ?? "").trim();
      const rows = q
        ? await listDocuments({ q })
        : opts.field
          ? await listDocuments({ field: opts.field })
          : await listDocuments({ tag: opts.tag, status: opts.status });
      if (my !== reqId.current) return;
      setDocs(rows);
      setError("");
    } catch (e) {
      if (my !== reqId.current) return;
      setError(String((e as Error).message ?? e));
    } finally {
      if (my === reqId.current) setLoading(false);
    }
  }

  function clearField() {
    setFieldFilter("");
    setFieldLabel("");
    setSearchParams({}, { replace: true });
    load({ q: query, tag, status: statusFilter });
  }

  function onInput(v: string) {
    setQuery(v);
    if (fieldFilter) clearField();
    clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => load({ q: v, tag, status: statusFilter }), 250);
  }

  function selectTag(t: string) {
    if (fieldFilter) clearField();
    setTag(t);
    setQuery("");
    load({ tag: t, status: statusFilter });
  }

  function selectStatus(s: string) {
    if (fieldFilter) clearField();
    setStatusFilter(s);
    setQuery("");
    load({ tag, status: s });
  }

  useEffect(() => {
    load({ field: fieldFilter, tag, status: statusFilter });
    listTags()
      .then(setTags)
      .catch(() => {});
    getTaxonomy()
      .then((t) => setStatuses(t.statuses ?? []))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="mx-auto max-w-[1040px] px-5 pt-6 pb-16">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
        <h1 className="text-3xl font-semibold tracking-tight">Library</h1>
        <span className="mono text-sm text-muted-foreground">
          {docs.length} {searching ? `result${docs.length === 1 ? "" : "s"}` : `document${docs.length === 1 ? "" : "s"}`}
        </span>
        <Uploader compact />
      </div>

      <div className="sticky top-[57px] z-10 flex items-center bg-background py-1 pb-4">
        <Search className="pointer-events-none absolute ml-3 size-[17px] text-muted-foreground/60" />
        <input
          type="search"
          placeholder="Search documents…"
          value={query}
          onChange={(e) => onInput(e.target.value)}
          className="mono h-11 w-full rounded-full border bg-card py-2.5 pr-4 pl-10 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
        />
      </div>

      {fieldFilter && (
        <div className="mb-4 flex items-center gap-3 rounded-xl border border-primary/25 bg-primary/10 px-3 py-2.5 text-sm">
          <Filter className="size-[15px] flex-none text-primary" />
          <span>
            Documents containing{fieldLabel ? <strong className="font-semibold"> {fieldLabel}</strong> : " this field"}
          </span>
          <button
            type="button"
            onClick={clearField}
            className="mono ml-auto flex flex-none items-center gap-1 rounded-full border border-primary/30 px-2.5 py-1 text-[0.6875rem] text-primary hover:bg-primary/15"
          >
            <X className="size-3" /> Clear
          </button>
        </div>
      )}

      <div className="scrollbar-none mb-5 flex gap-2 overflow-x-auto pb-1">
        <button
          type="button"
          onClick={() => selectTag("")}
          className={cn(
            "mono flex-shrink-0 whitespace-nowrap rounded-full border px-3.5 py-2 text-[0.6875rem] text-muted-foreground hover:border-accent",
            !tag && "border-accent/40 bg-accent/10 text-accent",
          )}
        >
          All
        </button>
        {tags.slice(0, 12).map((t) => (
          <button
            key={t.name}
            type="button"
            onClick={() => selectTag(t.name)}
            className={cn(
              "mono flex-shrink-0 whitespace-nowrap rounded-full border px-3.5 py-2 text-[0.6875rem] text-muted-foreground hover:border-accent",
              tag === t.name && "border-accent/40 bg-accent/10 text-accent",
            )}
          >
            {t.name} <span className="opacity-80">{t.n}</span>
          </button>
        ))}
      </div>

      {statuses.length > 0 && (
        <div className="scrollbar-none -mt-3 mb-5 flex gap-2 overflow-x-auto pb-1">
          <button
            type="button"
            onClick={() => selectStatus("")}
            className={cn(
              "mono flex-shrink-0 whitespace-nowrap rounded-full border px-3.5 py-2 text-[0.6875rem] text-muted-foreground hover:border-primary",
              !statusFilter && "border-primary/40 bg-primary/10 text-primary",
            )}
          >
            Any status
          </button>
          {statuses.map((s) => (
            <button
              key={s.key}
              type="button"
              onClick={() => selectStatus(s.key)}
              className={cn(
                "mono flex-shrink-0 whitespace-nowrap rounded-full border px-3.5 py-2 text-[0.6875rem] text-muted-foreground hover:border-primary",
                statusFilter === s.key && "border-primary/40 bg-primary/10 text-primary",
              )}
            >
              {s.label}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <p className="text-muted-foreground">Loading documents…</p>
      ) : error ? (
        <p className="text-danger">Couldn't load the library: {error}</p>
      ) : docs.length === 0 ? (
        <Card className="items-center gap-4 px-5 py-14 text-center">
          <span className="flex size-14 items-center justify-center rounded-full bg-accent/10 text-accent">
            {searching ? <Search className="size-[26px]" strokeWidth={1.5} /> : <Inbox className="size-[26px]" strokeWidth={1.5} />}
          </span>
          {searching ? (
            <>
              <h2 className="text-xl font-semibold">No matches</h2>
              <p className="text-muted-foreground">Nothing found for "{query}". Try a different term.</p>
            </>
          ) : tag ? (
            <>
              <h2 className="text-xl font-semibold">No documents tagged "{tag}"</h2>
              <p className="text-muted-foreground">Try another tag or clear the filter.</p>
            </>
          ) : (
            <>
              <h2 className="text-xl font-semibold">No documents yet</h2>
              <p className="text-muted-foreground">Upload or sync a source — documents will show up here.</p>
            </>
          )}
        </Card>
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(320px,1fr))] gap-4">
          {docs.map((d) => (
            <DocCard key={d.id} doc={d} snippet={searching ? d.snippet : null} />
          ))}
        </div>
      )}
    </main>
  );
}
