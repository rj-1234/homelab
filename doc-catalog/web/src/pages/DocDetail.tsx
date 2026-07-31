import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, ExternalLink, RefreshCw, Tag, Trash2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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
import { FieldCard } from "@/components/FieldCard";
import { PipelineStrip } from "@/components/PipelineStrip";
import { intoGroups } from "@/lib/fields";
import { cn } from "@/lib/utils";
import { fmtBytes, fmtDate } from "@/lib/docmeta";
import { useStatus } from "@/lib/status";
import { getDoc, docFields, updateDoc, reprocessDoc, deleteDoc, getTaxonomy } from "@/api";
import type { Doc, Provenance, PageText, DocField, Job, Taxonomy } from "@/api";

export function DocDetail() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { status } = useStatus();

  const [doc, setDoc] = useState<Doc | null>(null);
  const [provenance, setProvenance] = useState<Provenance[]>([]);
  const [pagesText, setPagesText] = useState<PageText[]>([]);
  const [fields, setFields] = useState<DocField[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState("");

  async function load(currentId: string) {
    setLoading(true);
    setNotFound(false);
    setError("");
    try {
      const [detail, f] = await Promise.all([getDoc(currentId), docFields(currentId)]);
      setDoc(detail.doc);
      setProvenance(detail.provenance ?? []);
      setPagesText(detail.pages ?? []);
      setFields(f ?? []);
      setJobs(detail.jobs ?? []);
    } catch (e) {
      const msg = String((e as Error).message ?? e);
      if (/-> 404$/.test(msg)) setNotFound(true);
      else setError(msg);
    } finally {
      setLoading(false);
    }
  }

  // Re-pull the whole detail WITHOUT the loading spinner, so job transitions
  // and freshly-extracted text/fields appear in place. Used both after an
  // action (instant feedback) and reactively when an SSE change arrives.
  const liveBusy = useRef(false);
  async function refresh(currentId: string) {
    if (liveBusy.current) return;
    liveBusy.current = true;
    try {
      const [detail, f] = await Promise.all([getDoc(currentId), docFields(currentId)]);
      setDoc(detail.doc);
      setProvenance(detail.provenance ?? []);
      setPagesText(detail.pages ?? []);
      setFields(f ?? []);
      setJobs(detail.jobs ?? []);
    } catch {
      /* best-effort; UI keeps last known state */
    } finally {
      liveBusy.current = false;
    }
  }

  useEffect(() => {
    load(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Realtime: the SSE status snapshot ticks on every job/document change.
  // Re-pull the current doc on each tick so the pipeline pill flips
  // active→done, and Save/worker updates land, without a manual refresh.
  useEffect(() => {
    if (loading || notFound || !doc) return;
    refresh(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const groups = intoGroups(fields);
  const unconfirmed = fields.filter((f) => !f.confirmed).length;

  // --- taxonomy + manage form ---
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null);
  useEffect(() => {
    getTaxonomy()
      .then(setTaxonomy)
      .catch(() => {});
  }, []);

  const [title, setTitle] = useState("");
  const [docType, setDocType] = useState("");
  const [statusSel, setStatusSel] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [customTagsInput, setCustomTagsInput] = useState("");

  // (Re)seed the manage form whenever the doc or taxonomy changes — both are
  // needed to split doc.tags into "known" chips vs. free-text custom tags.
  useEffect(() => {
    if (!doc) return;
    setTitle(doc.title ?? "");
    setDocType(doc.doc_type ?? "");
    setStatusSel(doc.status ?? "");
    const known = new Set((taxonomy?.tags ?? []).flatMap((c) => [c.category, ...c.subtags]));
    const docTags = doc.tags ?? [];
    setSelectedTags(docTags.filter((t) => known.has(t)));
    setCustomTagsInput(docTags.filter((t) => !known.has(t)).join(", "));
  }, [doc, taxonomy]);

  function subLabel(s: string) {
    const i = s.indexOf(":");
    return i === -1 ? s : s.slice(i + 1);
  }

  function toggleChip(v: string) {
    setSelectedTags((prev) => (prev.includes(v) ? prev.filter((t) => t !== v) : [...prev, v]));
  }

  // --- actions ---
  const [busyStage, setBusyStage] = useState<string | null>(null);
  async function doReprocess(stage: string) {
    setBusyStage(stage);
    try {
      await reprocessDoc(id, stage);
      toast.success(`Queued ${stage}`);
      await refresh(id);
    } catch (e) {
      toast.error(`Couldn't queue ${stage}: ${String((e as Error).message ?? e)}`);
    } finally {
      setBusyStage(null);
    }
  }

  const [busyDelete, setBusyDelete] = useState(false);
  async function doDelete() {
    setBusyDelete(true);
    try {
      await deleteDoc(id);
      navigate("/library");
    } catch (e) {
      toast.error(`Delete failed: ${String((e as Error).message ?? e)}`);
      setBusyDelete(false);
    }
  }

  const [busySave, setBusySave] = useState(false);
  async function doSave() {
    setBusySave(true);
    try {
      const custom = customTagsInput
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const tags = Array.from(new Set([...selectedTags, ...custom]));
      await updateDoc(id, { title, doc_type: docType.trim() || null, status: statusSel, tags });
      toast.success("Saved");
      await refresh(id);
    } catch (e) {
      toast.error(`Save failed: ${String((e as Error).message ?? e)}`);
    } finally {
      setBusySave(false);
    }
  }

  return (
    <main className="mx-auto max-w-[1040px] px-5 pt-6 pb-16">
      <Link to="/library" className="mono mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-[15px]" /> Library
      </Link>

      {loading ? (
        <p className="text-muted-foreground">Loading document…</p>
      ) : notFound ? (
        <Card className="px-7 py-10 text-center">
          <h2 className="mb-2 text-xl font-semibold">Document not found</h2>
          <p className="text-muted-foreground">
            It may have been deleted.{" "}
            <Link to="/library" className="text-accent hover:underline">
              Back to the library →
            </Link>
          </p>
        </Card>
      ) : error ? (
        <p className="text-danger">Couldn't load this document: {error}</p>
      ) : doc ? (
        <>
          <header className="mb-5 border-b pb-4">
            <h1 className="mb-2 text-2xl font-semibold tracking-tight break-words">
              {doc.title || "Untitled document"}
            </h1>
            <div className="mono text-sm text-muted-foreground [overflow-wrap:anywhere]">
              #{doc.id}
              {doc.mime && ` · ${doc.mime}`}
              {doc.size != null && ` · ${fmtBytes(doc.size)}`}
              {doc.pages != null && ` · ${doc.pages} page${doc.pages === 1 ? "" : "s"}`}
              {doc.created_at && ` · ${fmtDate(doc.created_at)}`}
              {doc.status && ` · ${doc.status}`}
            </div>
            {doc.tags?.length > 0 && (
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {doc.tags.map((t) => (
                  <span key={t} className="mono rounded-full border border-accent/15 bg-accent/10 px-2.5 py-0.5 text-[11px] text-accent">
                    {t}
                  </span>
                ))}
              </div>
            )}
          </header>

          <PipelineStrip jobs={jobs} status={doc.status} />

          <div className="mb-4 flex flex-wrap gap-2">
            <Button variant="outline" asChild>
              <a href={`/api/doc/${doc.id}/raw`} target="_blank" rel="noopener">
                <ExternalLink className="size-[15px]" /> View original
              </a>
            </Button>
            <Button variant="outline" onClick={() => doReprocess("text")} disabled={busyStage === "text"}>
              <RefreshCw className="size-[15px]" /> {busyStage === "text" ? "Queuing…" : "Re-run text"}
            </Button>
            <Button variant="outline" onClick={() => doReprocess("ocr")} disabled={busyStage === "ocr"}>
              <RefreshCw className="size-[15px]" /> {busyStage === "ocr" ? "Queuing…" : "Re-run OCR"}
            </Button>
            <Button variant="outline" onClick={() => doReprocess("embed_pages")} disabled={busyStage === "embed_pages"}>
              <RefreshCw className="size-[15px]" /> {busyStage === "embed_pages" ? "Queuing…" : "Embed pages"}
            </Button>
            <Button
              onClick={() => doReprocess("embed")}
              disabled={busyStage === "embed"}
              className="bg-accent text-accent-foreground hover:bg-accent/90"
            >
              <Tag className="size-[15px]" /> {busyStage === "embed" ? "Queuing…" : "Re-tag"}
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="outline"
                  disabled={busyDelete}
                  className="border-danger text-danger hover:bg-danger-wash hover:text-danger"
                >
                  <Trash2 className="size-[15px]" /> {busyDelete ? "Deleting…" : "Delete"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete this document?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This deletes the document and its file. This cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={doDelete}
                    className="bg-danger text-white hover:bg-danger/90"
                  >
                    Delete
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>

          <details className="mb-7 overflow-hidden rounded-xl border bg-card">
            <summary className="mono flex min-h-10 cursor-pointer items-center px-4 py-3 text-xs uppercase tracking-wide text-muted-foreground hover:text-foreground">
              Manage
            </summary>
            <div className="flex flex-col gap-3.5 border-t p-4">
              <div className="flex flex-col gap-1.5">
                <Label className="mono text-[11px] uppercase tracking-wide text-muted-foreground">Title</Label>
                <Input value={title} onChange={(e) => setTitle(e.target.value)} />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="mono text-[11px] uppercase tracking-wide text-muted-foreground">Type</Label>
                <Input
                  placeholder="e.g. tax · statement · medical"
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="mono text-[11px] uppercase tracking-wide text-muted-foreground">Status</Label>
                <Select value={statusSel} onValueChange={setStatusSel}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(taxonomy?.statuses ?? []).map((s) => (
                      <SelectItem key={s.key} value={s.key}>
                        {s.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-2.5">
                <Label className="mono text-[11px] uppercase tracking-wide text-muted-foreground">Tags</Label>
                {(taxonomy?.tags ?? []).map((cat) => (
                  <div key={cat.category} className="flex flex-wrap gap-1.5">
                    <button
                      type="button"
                      onClick={() => toggleChip(cat.category)}
                      className={cn(
                        "mono rounded-full border px-3 py-1.5 text-xs font-semibold text-foreground hover:border-accent",
                        selectedTags.includes(cat.category) && "border-accent bg-accent/15",
                      )}
                    >
                      {cat.category}
                    </button>
                    {cat.subtags.map((sub) => (
                      <button
                        key={sub}
                        type="button"
                        onClick={() => toggleChip(sub)}
                        className={cn(
                          "mono rounded-full border px-3 py-1.5 text-xs text-muted-foreground hover:border-accent",
                          selectedTags.includes(sub) && "border-accent bg-accent/15 text-foreground",
                        )}
                      >
                        {subLabel(sub)}
                      </button>
                    ))}
                  </div>
                ))}

                <div className="mt-0.5 flex flex-col gap-1.5">
                  <Label className="mono text-[11px] uppercase tracking-wide text-muted-foreground">
                    Custom tags (comma separated)
                  </Label>
                  <Input
                    placeholder="e.g. warranty, receipt"
                    value={customTagsInput}
                    onChange={(e) => setCustomTagsInput(e.target.value)}
                  />
                </div>
              </div>

              <Button onClick={doSave} disabled={busySave} className="self-start">
                {busySave ? "Saving…" : "Save"}
              </Button>
            </div>
          </details>

          <section className="mb-7">
            <h2 className="eyebrow">Fields</h2>
            {fields.length === 0 ? (
              <p className="text-muted-foreground">No fields extracted from this document.</p>
            ) : (
              <>
                {unconfirmed > 0 && (
                  <p className="mb-3 text-sm text-muted-foreground">
                    {unconfirmed} field{unconfirmed === 1 ? "" : "s"} awaiting confirmation —{" "}
                    <Link to="/review" className="text-accent hover:underline">
                      review them →
                    </Link>
                  </p>
                )}
                {groups.map((g) => (
                  <div key={g.title} className="mb-4">
                    <h3 className="mono mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      {g.title}
                    </h3>
                    <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-4">
                      {g.fields.map((f) => (
                        <FieldCard key={f.id} field={f} />
                      ))}
                    </div>
                  </div>
                ))}
              </>
            )}
          </section>

          {provenance.length > 0 && (
            <section className="mb-7">
              <h2 className="eyebrow">Provenance</h2>
              <Card className="max-h-[260px] gap-0 overflow-y-auto py-1">
                {provenance.map((p, i) => (
                  <div key={i} className="border-b px-4 py-2.5 text-[12.5px] last:border-b-0">
                    <span className="mono text-[10.5px] uppercase tracking-wide text-accent">{p.source}</span>
                    <div className="text-muted-foreground [overflow-wrap:anywhere]">
                      {p.sender && `${p.sender} · `}
                      {p.subject && `"${p.subject}" · `}
                      {p.received_at ? `recv ${fmtDate(p.received_at)}` : p.created_at ? `added ${fmtDate(p.created_at)}` : ""}
                    </div>
                  </div>
                ))}
              </Card>
            </section>
          )}

          {pagesText.length > 0 && (
            <section className="mb-7">
              <h2 className="eyebrow">Text</h2>
              {pagesText.map((pg, i) => (
                <details key={pg.page_no ?? i} open={i === 0} className="mb-2.5 overflow-hidden rounded-xl border bg-card">
                  <summary className="mono flex min-h-10 cursor-pointer items-center px-4 py-3 text-[12.5px] text-muted-foreground hover:text-foreground">
                    Page {pg.page_no ?? i + 1} · {pg.engine ?? "unknown"} · {(pg.text ?? "").length} chars
                  </summary>
                  <pre className="mono m-0 max-h-[420px] overflow-auto whitespace-pre-wrap break-words border-t px-4 py-3.5 text-[12.5px] leading-relaxed">
                    {pg.text ?? ""}
                  </pre>
                </details>
              ))}
            </section>
          )}
        </>
      ) : null}
    </main>
  );
}
