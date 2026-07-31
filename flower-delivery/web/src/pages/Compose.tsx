import React, { useMemo, useRef, useState } from "react";
import {
  BouquetScene, ORDER, SP, SpeciesKey, buildFillers, buildGarden, speciesIcon,
} from "../engine";
import { useClock, usePrefersReducedMotion } from "../useClock";

const MIN_STEMS = 5;
const MAX_STEMS = 13;
const DEFAULT_STEMS = 7;

const LIFETIME_OPTIONS: { label: string; ms: number }[] = [
  { label: "24 hours", ms: 24 * 3600_000 },
  { label: "3 days", ms: 3 * 24 * 3600_000 },
  { label: "7 days", ms: 7 * 24 * 3600_000 },
  { label: "30 days", ms: 30 * 24 * 3600_000 },
];

export default function Compose() {
  const uid = useRef("c" + Math.random().toString(36).slice(2, 7)).current;
  const reducedMotion = usePrefersReducedMotion();
  const clock = useClock(!reducedMotion);

  const [picks, setPicks] = useState<SpeciesKey[]>([...ORDER]);
  const [maxStems, setMaxStems] = useState(DEFAULT_STEMS);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [sel, setSel] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [sender, setSender] = useState("");
  const [lifetimeMs, setLifetimeMs] = useState(LIFETIME_OPTIONS[0].ms);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ id: string; url: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const garden = useMemo(() => buildGarden(picks), [picks]);
  const fillers = useMemo(() => buildFillers(), []);
  const counts = useMemo(() => {
    const c: Partial<Record<SpeciesKey, number>> = {};
    picks.forEach((k) => { c[k] = (c[k] || 0) + 1; });
    return c;
  }, [picks]);

  function addStem(k: SpeciesKey) {
    setPicks((p) => (p.length >= maxStems ? [...p.slice(1), k] : [...p, k]));
  }
  function clearPicks() {
    setPicks([]);
    setNotes({});
    setSel(null);
  }
  function changeMaxStems(n: number) {
    setMaxStems(n);
    setPicks((p) => p.slice(0, n));
    setNotes((prev) => {
      const next: Record<number, string> = {};
      Object.entries(prev).forEach(([k, v]) => { if (Number(k) < n) next[Number(k)] = v; });
      return next;
    });
    setSel((s) => (s !== null && s >= n ? null : s));
  }

  async function send() {
    setSending(true);
    setError(null);
    try {
      const stems = picks.map((k, i) => {
        const note = notes[i]?.trim();
        return note ? { species: k, note } : { species: k };
      });
      const res = await fetch("/api/gifts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          stems,
          message: message.trim() || "No occasion. Just you.",
          sender: sender.trim() || "Someone",
          lifetime_ms: lifetimeMs,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || "Could not send this bouquet.");
      }
      const body = await res.json();
      setResult(body);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setSending(false);
    }
  }

  if (result) {
    const shareUrl = `${window.location.origin}${result.url}`;
    return (
      <div style={{ minHeight: "100dvh", display: "flex", alignItems: "center", justifyContent: "center", padding: "var(--space-6)", background: "var(--color-bg)" }}>
        <div className="card elev-lg" style={{ maxWidth: 420, width: "100%", padding: "var(--space-6)", gap: "var(--space-4)" }}>
          <span className="card-kicker">it's on its way</span>
          <h2 style={{ margin: 0 }}>Your bouquet is tied.</h2>
          <p className="card-body" style={{ opacity: 1 }}>Send this link. It plays a day of bloom on every visit until the time you chose runs out — then it presses into a keepsake, permanently.</p>
          <div className="field">
            <input className="input" readOnly value={shareUrl} onFocus={(e) => e.currentTarget.select()} />
          </div>
          <div style={{ display: "flex", gap: "var(--space-2)" }}>
            <button type="button" className="btn btn-primary btn-block" onClick={() => {
              navigator.clipboard.writeText(shareUrl).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); });
            }}>{copied ? "Copied" : "Copy link"}</button>
            <a className="btn btn-secondary btn-block" href={`${result.url}?dev=1`} target="_blank" rel="noreferrer">Preview</a>
          </div>
          <button type="button" className="btn btn-ghost" onClick={() => { setResult(null); setPicks([...ORDER]); setMaxStems(DEFAULT_STEMS); setNotes({}); setMessage(""); setSender(""); }}>
            Tie another
          </button>
        </div>
      </div>
    );
  }

  const hasSel = sel !== null;
  const noteDraft = sel !== null ? notes[sel] || "" : "";
  const notePlaceholder = sel !== null ? `A line about this ${SP[picks[sel]].name.toLowerCase()}…` : "";
  const stemLabel = `${picks.length} ${picks.length === 1 ? "stem" : "stems"} — tap a flower above to add another`;

  return (
    <div style={{ position: "relative", width: "100%", height: "100dvh", overflow: "hidden", background: "var(--color-bg)" }}>
      <BouquetScene uid={uid} garden={garden} fillers={fillers} p={0.42} wind={0} waterAt={-9} clock={clock} extra={{}} cycleSeconds={60} liftForCompose />

      <div style={{
        position: "absolute", left: 0, right: 0, bottom: 0, maxHeight: "82dvh", overflowY: "auto",
        background: "var(--color-bg)", borderRadius: "30px 30px 0 0", boxShadow: "0 -18px 44px rgba(32,30,29,0.16)",
        padding: "20px 22px calc(26px + env(safe-area-inset-bottom))", display: "flex", flexDirection: "column", gap: 10,
      }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <h3 style={{ margin: 0, fontSize: 25, lineHeight: 1.1 }}>Tie a bouquet</h3>
          <p style={{ margin: 0, fontSize: 12.5, color: "var(--color-neutral-700)" }}>
            Up to {maxStems} stems. It blooms for a day, drops its petals, then presses itself into a keepsake.
          </p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          <span style={{ fontSize: 11.5, color: "var(--color-neutral-700)" }}>Bouquet size — {maxStems} stems</span>
          <input type="range" min={MIN_STEMS} max={MAX_STEMS} value={maxStems}
            onChange={(e) => changeMaxStems(Number(e.target.value))}
            style={{ width: "100%", accentColor: "var(--color-accent)" }} />
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
          {ORDER.map((k) => (
            <button key={k} type="button" title={SP[k].name} onClick={() => addStem(k)}
              style={{ display: "flex", alignItems: "center", gap: 7, padding: "5px 11px 5px 5px", borderRadius: 999, border: "1px solid var(--color-divider)", background: "var(--color-surface)", cursor: "pointer", font: "inherit", fontSize: 11.5, color: "var(--color-text)" }}>
              <span style={{ width: 30, height: 30, borderRadius: 999, background: "var(--color-neutral-100)", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
                {speciesIcon(uid, k)}
              </span>
              <span>{SP[k].name}</span>
              {!!counts[k] && (
                <span style={{ minWidth: 16, height: 16, padding: "0 4px", borderRadius: 999, background: "var(--color-accent)", color: "var(--color-bg)", fontSize: 10, fontWeight: 700, display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
                  {counts[k]}
                </span>
              )}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
          <span style={{ fontSize: 11.5, color: "var(--color-neutral-700)" }}>{stemLabel}</span>
          <button type="button" onClick={clearPicks} style={{ border: 0, background: "transparent", font: "inherit", fontSize: 11.5, color: "var(--color-accent-700)", cursor: "pointer", padding: "4px 6px", borderRadius: 999 }}>
            Start over
          </button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span style={{ fontSize: 11.5, color: "var(--color-neutral-700)" }}>Pin a line to one stem — they'll find it by tapping that flower</span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {picks.map((k, i) => (
              <button key={k + i} type="button" title={SP[k].name} onClick={() => setSel((s) => (s === i ? null : i))}
                style={{ position: "relative", width: 34, height: 34, padding: 0, borderRadius: 999, border: `1.5px solid ${sel === i ? "var(--color-accent)" : "var(--color-divider)"}`, background: "var(--color-surface)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
                {speciesIcon(uid, k, 26)}
                {!!notes[i]?.trim() && (
                  <span style={{ position: "absolute", right: -1, bottom: -1, width: 10, height: 10, borderRadius: 999, background: "var(--color-accent)", border: "1.5px solid var(--color-bg)" }} />
                )}
              </button>
            ))}
          </div>
          {hasSel && (
            <input className="input" value={noteDraft} placeholder={notePlaceholder}
              onChange={(e) => setNotes((n) => ({ ...n, [sel!]: e.target.value }))} />
          )}
        </div>

        <label style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          <span style={{ fontSize: 11.5, color: "var(--color-neutral-700)" }}>Your note</span>
          <textarea className="input" rows={2} placeholder="No occasion. Just you." value={message} onChange={(e) => setMessage(e.target.value)} maxLength={240} />
        </label>

        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          <span style={{ fontSize: 11.5, color: "var(--color-neutral-700)" }}>How long should the link stay open?</span>
          <div className="seg">
            {LIFETIME_OPTIONS.map((opt) => (
              <label key={opt.ms} className="seg-opt">
                <input type="radio" name="lifetime" checked={lifetimeMs === opt.ms} onChange={() => setLifetimeMs(opt.ms)} />
                {opt.label}
              </label>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", gap: 9, alignItems: "flex-end" }}>
          <label style={{ display: "flex", flexDirection: "column", gap: 5, flex: 1 }}>
            <span style={{ fontSize: 11.5, color: "var(--color-neutral-700)" }}>From</span>
            <input className="input" placeholder="Your name" value={sender} onChange={(e) => setSender(e.target.value)} />
          </label>
          <button type="button" className="btn btn-primary" disabled={picks.length === 0 || sending} onClick={send}>
            {sending ? "Sending…" : "Send it"}
          </button>
        </div>

        {error && <p style={{ margin: 0, fontSize: 12.5, color: "var(--color-accent-700)" }}>{error}</p>}
      </div>
    </div>
  );
}
