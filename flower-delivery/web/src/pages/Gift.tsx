import React, { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import {
  BouquetScene, GardenFlower, SP, SpeciesKey, buildFillers, buildGarden, pressedEl, ss,
} from "../engine";
import { useClock, usePrefersReducedMotion } from "../useClock";

const PLAY_SECONDS = 60;

interface GiftData {
  stems: { species: SpeciesKey; note?: string }[];
  message: string;
  sender: string;
  expires_at: string;
  alive: boolean;
}

type Screen = "arrive" | "gift" | "keepsake";

export default function Gift() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const dev = searchParams.get("dev") === "1";
  const navigate = useNavigate();
  const reducedMotion = usePrefersReducedMotion();

  const [data, setData] = useState<GiftData | null>(null);
  const [notFound, setNotFound] = useState(false);
  const uid = useRef("g" + Math.random().toString(36).slice(2, 7)).current;

  useEffect(() => {
    if (!id) return;
    fetch(`/api/gifts/${id}`)
      .then((res) => {
        if (res.status === 404) { setNotFound(true); return null; }
        return res.json();
      })
      .then((body) => { if (body) setData(body); })
      .catch(() => setNotFound(true));
  }, [id]);

  const [screen, setScreen] = useState<Screen>("arrive");
  const [playing, setPlaying] = useState(true);
  const [sound, setSound] = useState(false);
  const [tip, setTip] = useState<{ name: string; meaning: string; note: string; x: number; y: number } | null>(null);

  const tRef = useRef(0);
  const [p, setP] = useState(0);
  const [wind, setWind] = useState(0);
  const [waterAt, setWaterAt] = useState(-9);
  const [extra, setExtra] = useState<Record<string, number>>({});
  const holdingRef = useRef(false);
  const lastGustRef = useRef(0);
  const lastRef = useRef(performance.now() / 1000);
  const audioRef = useRef<{ ctx: AudioContext } | null>(null);
  const tipTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const staticFrame = reducedMotion && !dev;
  const clock = useClock(!staticFrame && screen === "gift" && data?.alive === true);

  const picks: SpeciesKey[] = useMemo(() => (data ? data.stems.map((s) => s.species) : []), [data]);
  const garden = useMemo(() => buildGarden(picks), [picks]);
  const fillers = useMemo(() => buildFillers(), []);

  function gust() {
    lastGustRef.current = performance.now() / 1000;
    const curP = Math.min(1, tRef.current / PLAY_SECONDS);
    let added = 0;
    setExtra((prev) => {
      const next = { ...prev };
      for (const f of garden) {
        const sp = SP[f.k];
        for (let j = 0; j < sp.dropN && added < 4; j++) {
          const key = f.i + "-" + j;
          if (next[key] || curP > (f.drops[j] ?? 9)) continue;
          const bloom = ss((curP - f.openAt) / f.openDur);
          if (bloom < 0.6) continue;
          next[key] = curP + added * 0.002;
          added++;
        }
        if (added >= 4) break;
      }
      return next;
    });
  }

  useEffect(() => {
    if (staticFrame || !data?.alive || screen !== "gift") return;
    let raf: number;
    const loop = () => {
      const now = performance.now() / 1000;
      const dt = Math.min(0.06, now - lastRef.current);
      lastRef.current = now;
      if (playing) tRef.current += dt;
      holdingRef.current
        ? setWind((w) => Math.min(1, w + dt * 2.4))
        : setWind((w) => Math.max(0, w - dt * 0.7));
      if (holdingRef.current && now - lastGustRef.current > 0.35) gust();
      const next = Math.min(1, tRef.current / PLAY_SECONDS);
      setP(next);
      if (next >= 1) setScreen("keepsake");
      raf = requestAnimationFrame(loop);
    };
    lastRef.current = performance.now() / 1000;
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [staticFrame, data?.alive, screen, playing]);

  useEffect(() => {
    function onMotion(e: DeviceMotionEvent) {
      const a = e.accelerationIncludingGravity;
      if (!a) return;
      const mag = Math.abs(a.x || 0) + Math.abs(a.y || 0) + Math.abs(a.z || 0);
      if (mag > 34) {
        holdingRef.current = true;
        gust();
        window.setTimeout(() => { holdingRef.current = false; }, 300);
      }
    }
    window.addEventListener("devicemotion", onMotion);
    return () => window.removeEventListener("devicemotion", onMotion);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [garden]);

  useEffect(() => () => { if (audioRef.current) audioRef.current.ctx.close(); }, []);

  if (notFound) {
    return (
      <div style={{ minHeight: "100dvh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--color-bg)", padding: "var(--space-6)" }}>
        <p>No bouquet here.</p>
      </div>
    );
  }
  if (!data) return null;

  function openGift() {
    tRef.current = 0;
    setP(staticFrame ? 0.42 : 0);
    setScreen("gift");
    setPlaying(!staticFrame);
  }
  function replay() {
    tRef.current = 0;
    setP(staticFrame ? 0.42 : 0);
    setExtra({});
    setWaterAt(-9);
    setScreen("gift");
    setPlaying(!staticFrame);
    setTip(null);
  }
  function tap(f: GardenFlower) {
    const sp = SP[f.k];
    const note = data?.stems[f.i]?.note || "";
    setTip({ name: sp.name, meaning: sp.meaning, note, x: f.hx, y: f.hy });
    if (tipTimerRef.current) clearTimeout(tipTimerRef.current);
    tipTimerRef.current = setTimeout(() => setTip(null), 3600);
  }
  function toggleSound() {
    if (!sound) {
      if (!audioRef.current) startAudio();
      else audioRef.current.ctx.resume();
    } else if (audioRef.current) {
      audioRef.current.ctx.suspend();
    }
    setSound((s) => !s);
  }
  function startAudio() {
    const AC = window.AudioContext || (window as any).webkitAudioContext;
    const ac: AudioContext = new AC();
    const out = ac.createGain();
    out.gain.value = 0.0001;
    out.connect(ac.destination);
    out.gain.linearRampToValueAtTime(0.5, ac.currentTime + 2.5);
    [147, 220, 294].forEach((hz, i) => {
      const o = ac.createOscillator(), g = ac.createGain();
      o.type = "sine"; o.frequency.value = hz;
      g.gain.value = 0.035 - i * 0.008;
      const lfo = ac.createOscillator(), lg = ac.createGain();
      lfo.frequency.value = 0.05 + i * 0.03; lg.gain.value = 0.02;
      lfo.connect(lg); lg.connect(g.gain); lfo.start();
      o.connect(g); g.connect(out); o.start();
    });
    const len = ac.sampleRate * 3, buf = ac.createBuffer(1, len, ac.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * 0.5;
    const src = ac.createBufferSource(); src.buffer = buf; src.loop = true;
    const lp = ac.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 420;
    const ng = ac.createGain(); ng.gain.value = 0.06;
    src.connect(lp); lp.connect(ng); ng.connect(out); src.start();
    audioRef.current = { ctx: ac };
  }

  const night = ss((p - 0.84) / 0.14);
  const bloomedCount = garden.filter((f) => ss((p - f.openAt) / f.openDur) > 0.5).length;
  const droppedCount = garden.reduce((n, f) => n + f.drops.filter((_, j) => {
    const e = extra[f.i + "-" + j];
    const at = Math.min(f.drops[j] ?? 9, e ?? 9);
    return p > at;
  }).length, 0);
  let phase = "still opening";
  if (p > 0.06 && bloomedCount < picks.length) phase = "opening, one by one";
  if (bloomedCount === picks.length && droppedCount === 0) phase = "wide open";
  if (droppedCount > 0) phase = "letting go";
  if (p > 0.86) phase = "evening light";
  const chromeInk = night > 0.4 ? "#f6ead9" : "#8c491a";

  const showKeepsake = !data.alive || screen === "keepsake";
  const keepsakeSpecies = picks[0] || "rose";

  return (
    <div style={{ position: "relative", width: "100%", height: "100dvh", overflow: "hidden", background: "var(--color-bg)" }}>
      {!showKeepsake && (
        <BouquetScene uid={uid} garden={garden} fillers={fillers} p={p} wind={wind} waterAt={waterAt}
          clock={clock} extra={extra} cycleSeconds={PLAY_SECONDS} onTapStem={screen === "gift" ? tap : undefined} />
      )}

      {!showKeepsake && screen === "arrive" && (
        <div onClick={openGift} style={{
          position: "absolute", inset: 0, background: "rgba(32,30,29,0.28)", backdropFilter: "blur(3px)",
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 18, cursor: "pointer",
        }}>
          <div style={{ width: 292, background: "var(--color-bg)", borderRadius: 26, padding: "30px 26px", boxShadow: "0 26px 60px rgba(32,30,29,0.34)", display: "flex", flexDirection: "column", alignItems: "center", gap: 10, textAlign: "center" }}>
            <span style={{ fontSize: 10.5, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--color-accent-700)" }}>A bouquet arrived</span>
            <h3 style={{ margin: 0, fontSize: 27, lineHeight: 1.12 }}>{data.sender || "Someone"} sent you flowers</h3>
            <p style={{ margin: 0, fontSize: 13, color: "var(--color-neutral-700)" }}>It opens once, and lasts a while. Tap to let it in.</p>
            <span style={{ marginTop: 6, display: "inline-flex", alignItems: "center", gap: 7, padding: "10px 18px", minHeight: 46, borderRadius: 999, background: "var(--color-accent)", color: "var(--color-bg)", fontSize: 13.5 }}>
              Open
            </span>
          </div>
        </div>
      )}

      {!showKeepsake && screen === "gift" && (
        <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
          <div style={{ position: "absolute", top: 62, left: 22, display: "flex", flexDirection: "column", gap: 2 }}>
            <span style={{ fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: chromeInk }}>for you, from</span>
            <span style={{ fontSize: 19, color: chromeInk }}>{data.sender || "someone"}</span>
          </div>

          <div style={{ position: "absolute", right: 16, top: 108, display: "flex", flexDirection: "column", gap: 10, pointerEvents: "auto" }}>
            <button type="button" title="Water the flowers" onClick={() => setWaterAt(p)}
              style={{ width: 46, height: 46, borderRadius: 999, border: 0, background: "var(--color-bg)", boxShadow: "0 6px 18px rgba(32,30,29,0.18)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
              <svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke="#8c491a" strokeWidth={2.75} strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3c3 4.2 5 7 5 9.4A5 5 0 0 1 7 12.4C7 10 9 7.2 12 3Z" />
              </svg>
            </button>
            <button type="button" title="Hold to blow"
              onPointerDown={() => { holdingRef.current = true; gust(); }}
              onPointerUp={() => { holdingRef.current = false; }}
              onPointerLeave={() => { holdingRef.current = false; }}
              style={{ width: 46, height: 46, borderRadius: 999, border: 0, background: "var(--color-bg)", boxShadow: "0 6px 18px rgba(32,30,29,0.18)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", touchAction: "none" }}>
              <svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke="#56633f" strokeWidth={2.75} strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 8h11a3 3 0 1 0-3-3" /><path d="M3 14h8a3 3 0 1 1-3 3" /><path d="M17 14h2.5a2.5 2.5 0 1 1-2.5 2.5" />
              </svg>
            </button>
            <button type="button" title="Ambience" onClick={toggleSound}
              style={{ width: 46, height: 46, borderRadius: 999, border: 0, background: sound ? "var(--color-accent-2-300)" : "var(--color-bg)", boxShadow: "0 6px 18px rgba(32,30,29,0.18)", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
              <svg width={22} height={22} viewBox="0 0 24 24" fill="none" stroke="#3d472b" strokeWidth={2.75} strokeLinecap="round" strokeLinejoin="round">
                <path d="M11 5 6 9H3v6h3l5 4V5Z" />
                {sound ? <path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" /> : <path d="M16 9.5l5 5m0-5l-5 5" />}
              </svg>
            </button>
          </div>

          <div style={{ position: "absolute", left: 20, right: 20, bottom: 152, background: "var(--color-bg)", borderRadius: 24, padding: "17px 19px 15px", boxShadow: "0 14px 34px rgba(32,30,29,0.2)", display: "flex", flexDirection: "column", gap: 8, pointerEvents: "auto" }}>
            <p style={{ margin: 0, fontSize: 17.5, lineHeight: 1.28 }}>{data.message}</p>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
              <span style={{ fontSize: 11.5, color: "var(--color-neutral-700)" }}>from {data.sender || "someone"}</span>
              <span style={{ fontSize: 11, color: "var(--color-accent-700)" }}>{phase}</span>
            </div>
          </div>

          {tip && (
            <div style={{
              position: "absolute", left: Math.max(14, Math.min(240, tip.x - 76)), top: Math.max(120, Math.min(620, tip.y + 42)),
              maxWidth: 200, display: "flex", flexDirection: "column", gap: 1, background: "var(--color-bg)", borderRadius: 16,
              padding: "9px 14px", boxShadow: "0 10px 26px rgba(32,30,29,0.22)", pointerEvents: "none",
            }}>
              <span style={{ fontSize: 13.5 }}>{tip.name}</span>
              <span style={{ fontSize: 11.5, color: "var(--color-neutral-700)" }}>{tip.meaning}</span>
              {tip.note && (
                <span style={{ marginTop: 5, paddingTop: 6, borderTop: "1px solid var(--color-divider)", fontSize: 12.5, lineHeight: 1.35, color: "var(--color-accent-700)" }}>
                  {tip.note}
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {showKeepsake && (
        <div style={{ position: "absolute", inset: 0, background: "var(--color-neutral-200)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 20, padding: "60px 26px 46px" }}>
          <div style={{ width: "100%", maxWidth: 340, background: "var(--color-neutral-100)", borderRadius: 24, padding: "26px 24px 22px", boxShadow: "0 18px 44px rgba(32,30,29,0.16)", display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
            <span style={{ fontSize: 10, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--color-neutral-600)" }}>pressed and kept</span>
            {pressedEl(uid, keepsakeSpecies)}
            <p style={{ margin: 0, fontSize: 17, lineHeight: 1.3, textAlign: "center" }}>{data.message}</p>
            <span style={{ fontSize: 11.5, color: "var(--color-neutral-600)", textAlign: "center" }}>
              {picks.length} stems · from {data.sender || "someone"}
              {!data.alive && ` · this bouquet closed on ${new Date(data.expires_at).toLocaleDateString(undefined, { day: "numeric", month: "long" })}`}
            </span>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            {data.alive && (
              <button type="button" className="btn btn-secondary" onClick={replay}>Watch again</button>
            )}
            <button type="button" className="btn btn-primary" onClick={() => navigate("/")}>Send one back</button>
          </div>
        </div>
      )}

      {dev && data.alive && (
        <div style={{ position: "absolute", left: 12, right: 12, bottom: 12, display: "flex", flexDirection: "column", gap: 8, background: "var(--color-neutral-100)", border: "1px solid var(--color-divider)", borderRadius: 20, padding: "12px 14px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
            <span style={{ fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--color-neutral-600)" }}>hand-tied · demo clock</span>
            <span style={{ fontSize: 11.5, color: "var(--color-neutral-700)" }}>a day in {PLAY_SECONDS}s</span>
          </div>
          <input type="range" min={0} max={1000} value={Math.round(p * 1000)} style={{ width: "100%", accentColor: "var(--color-accent)" }}
            onChange={(e) => {
              const v = Number(e.target.value) / 1000;
              tRef.current = v * PLAY_SECONDS;
              setP(v);
              setPlaying(false);
              if (screen !== "gift") setScreen("gift");
            }} />
          <div style={{ display: "flex", gap: 8 }}>
            <button type="button" className="btn btn-secondary btn-block" onClick={() => setPlaying((pl) => !pl)}>{playing ? "Pause" : "Play"}</button>
            <button type="button" className="btn btn-secondary btn-block" onClick={replay}>Restart day</button>
            <button type="button" className="btn btn-secondary btn-block" onClick={() => navigate("/")}>Compose</button>
          </div>
        </div>
      )}
    </div>
  );
}
