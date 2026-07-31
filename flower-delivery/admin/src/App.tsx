import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { RefreshCw } from "lucide-react";
import { fetchGifts, type Gift } from "@/api";
import { KpiCard } from "@/components/KpiCard";
import { GiftCard } from "@/components/GiftCard";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { motionState } from "@/lib/motion";

export default function App() {
  const [gifts, setGifts] = useState<Gift[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const gridRef = useRef<HTMLDivElement>(null);

  async function load() {
    setError(null);
    try {
      setGifts(await fetchGifts());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
  }

  useEffect(() => {
    load();
  }, []);

  // Re-render every 30s so relative timestamps ("3h ago") stay current
  // without re-fetching or re-triggering the load-in animation below.
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 30_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!gifts || !gridRef.current) return;
    const cards = gridRef.current.querySelectorAll(".gift-card");
    if (cards.length === 0) return;
    gsap.from(cards, {
      autoAlpha: 0,
      y: 12,
      duration: motionState.reduceMotion ? 0 : 0.4,
      stagger: motionState.reduceMotion ? 0 : 0.04,
      ease: "power2.out",
    });
  }, [gifts]);

  function handleDeleted(id: string) {
    setGifts((prev) => prev?.filter((g) => g.id !== id) ?? null);
  }

  const counts = {
    total: gifts?.length ?? 0,
    live: gifts?.filter((g) => g.status === "live").length ?? 0,
    not_opened: gifts?.filter((g) => g.status === "not_opened").length ?? 0,
    expired: gifts?.filter((g) => g.status === "expired").length ?? 0,
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header className="mb-6 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <h1 className="text-2xl font-bold tracking-tight">Flowers — sent bouquets</h1>
          <span className="relative flex size-2.5" title="Live data">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-75" />
            <span className="relative inline-flex size-2.5 rounded-full bg-success" />
          </span>
        </div>
        <Button variant="outline" size="sm" onClick={load}>
          <RefreshCw className="size-3.5" /> Refresh
        </Button>
      </header>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <KpiCard label="Total gifts" value={counts.total} tone="default" />
        <KpiCard label="Live" value={counts.live} tone="success" />
        <KpiCard label="Not opened" value={counts.not_opened} tone="muted" />
        <KpiCard label="Expired" value={counts.expired} tone="destructive" />
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-8 text-center">
          <h2 className="mb-2 font-semibold">Couldn't load gifts</h2>
          <p className="mb-4 text-sm text-muted-foreground">{error}</p>
          <Button variant="outline" onClick={load}>
            Try again
          </Button>
        </div>
      )}

      {!error && gifts === null && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      )}

      {!error && gifts !== null && gifts.length === 0 && (
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          <h2 className="mb-2 font-semibold text-foreground">No bouquets sent yet</h2>
          <p className="text-sm">Once someone composes one at the public site, it'll show up here.</p>
        </div>
      )}

      {!error && gifts !== null && gifts.length > 0 && (
        <div ref={gridRef} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {gifts.map((g) => (
            <GiftCard key={g.id} gift={g} onDeleted={handleDeleted} />
          ))}
        </div>
      )}
    </div>
  );
}
