import { useRef, useState } from "react";
import { Upload, Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { uploadFiles } from "@/api";

// compact: icon+label button only, no dropzone (used inline in list headers).
export function Uploader({ compact = false }: { compact?: boolean }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);

  async function send(fileList: FileList | File[] | null | undefined) {
    if (!fileList || fileList.length === 0) return;
    setBusy(true);
    try {
      const r = await uploadFiles(fileList);
      const n = r?.queued?.length ?? fileList.length;
      toast.success(`Queued ${n} file${n === 1 ? "" : "s"}`);
    } catch (e) {
      toast.error(`Upload failed: ${String((e as Error).message ?? e)}`);
    } finally {
      setBusy(false);
    }
  }

  function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    send(e.target.files);
    e.target.value = "";
  }

  function openPicker() {
    inputRef.current?.click();
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    send(e.dataTransfer?.files);
  }
  function onDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragging(true);
  }

  return (
    <div className="inline-flex flex-col gap-1.5">
      <input
        ref={inputRef}
        type="file"
        multiple
        hidden
        accept=".pdf,.png,.jpg,.jpeg,.tiff,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
        onChange={onChange}
      />

      {compact ? (
        <Button variant="outline" onClick={openPicker} disabled={busy} className="border-accent text-accent hover:bg-accent/10">
          {busy ? <Upload /> : <Plus />}
          {busy ? "Uploading…" : "Add documents"}
        </Button>
      ) : (
        <Card
          onClick={openPicker}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={() => setDragging(false)}
          className={cn(
            "min-h-24 cursor-pointer flex-col items-center justify-center gap-1 border-dashed p-4 text-center transition-colors",
            dragging && "border-accent bg-accent/5",
          )}
        >
          <span className="mb-0.5 flex size-10 items-center justify-center rounded-[10px] border border-accent/20 bg-accent/10 text-accent">
            <Upload className="size-5" strokeWidth={1.6} />
          </span>
          <span className="font-semibold">Add documents</span>
          <span className="text-sm text-muted-foreground">Drop files here, or tap to choose</span>
        </Card>
      )}
    </div>
  );
}
