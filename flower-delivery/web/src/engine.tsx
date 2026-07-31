import React from "react";

// Ported from HANDOFF.md's `Bloom Gift Phone.dc.html` Component class —
// hand-tied layout only (the "open field" branch was the rejected 1a option).
// Kept as pure functions instead of a class so two different pages (compose
// backdrop, animated gift) can drive the same drawing code with their own
// state instead of sharing one mutable instance.

export type SpeciesKey =
  | "rose"
  | "ranunculus"
  | "tulip"
  | "cosmos"
  | "daffodil"
  | "chamomile"
  | "eucalyptus";

export interface Stem {
  species: SpeciesKey;
  note?: string;
}

interface SpeciesDef {
  name: string;
  meaning: string;
  dropN: number;
  kind: "rosette" | "cup" | "flat" | "trumpet" | "spray" | "green";
  rings?: [number, number, number][];
  n?: number;
  len?: number;
  wid?: number;
  o: string[];
  i?: string[];
  line: string;
  stem: string;
  disc?: string;
  corona?: string[];
}

export const SP: Record<SpeciesKey, SpeciesDef> = {
  rose: {
    name: "Garden rose", meaning: "I hold you dear", dropN: 8, kind: "rosette",
    rings: [[8, 35, 28], [7, 27, 23], [6, 20, 18], [5, 13, 12]],
    o: ["#c9603f", "#ef8f75", "#fbbda6"], i: ["#e08a6c", "#f7b49b", "#ffdccb"],
    line: "#b8563b", stem: "#7e9159",
  },
  ranunculus: {
    name: "Ranunculus", meaning: "you are radiant", dropN: 8, kind: "rosette",
    rings: [[9, 30, 21], [8, 23, 17], [7, 17, 14], [6, 11, 10]],
    o: ["#dda05f", "#f6c894", "#fdeacb"], i: ["#eab77c", "#fbdcb4", "#fff6e6"],
    line: "#c98f52", stem: "#8fa073",
  },
  tulip: {
    name: "Tulip", meaning: "a plain declaration", dropN: 6, kind: "cup",
    o: ["#cf6b34", "#f09a63", "#fbc79c"], i: ["#e2854a", "#f6b184", "#fedcbb"],
    line: "#bd6031", stem: "#8fa073",
  },
  cosmos: {
    name: "Cosmos", meaning: "a calm, ordered heart", dropN: 8, kind: "flat", n: 8, len: 38, wid: 18,
    o: ["#e8a79b", "#f9cfc6", "#fff6f3"], line: "#d69a8d", disc: "#f0b83f", stem: "#8fa073",
  },
  daffodil: {
    name: "Daffodil", meaning: "new beginnings", dropN: 6, kind: "trumpet", n: 6, len: 39, wid: 17,
    o: ["#eccb6a", "#fbeaa8", "#fffbe6"], line: "#dcb95c", corona: ["#e08f28", "#f9c25a"], stem: "#7e9159",
  },
  chamomile: {
    name: "Chamomile", meaning: "patience with me", dropN: 6, kind: "spray",
    o: ["#e6ddd0", "#f8f2e8", "#fffdf8"], line: "#cfc4b3", disc: "#f0b83f", stem: "#8fa073",
  },
  eucalyptus: {
    name: "Eucalyptus", meaning: "quiet company", dropN: 0, kind: "green",
    o: ["#728157", "#8fa073", "#aebf92"], line: "#5f6f49", stem: "#728157",
  },
};

export const ORDER: SpeciesKey[] = [
  "rose", "ranunculus", "tulip", "cosmos", "daffodil", "chamomile", "eucalyptus",
];

export const W = 402;
export const H = 874;

export function ss(x: number): number {
  const t = Math.max(0, Math.min(1, x));
  return t * t * (3 - 2 * t);
}
export function cl(x: number, a: number, b: number): number {
  return Math.max(a, Math.min(b, x));
}
export function rn(i: number): number {
  const x = Math.sin(i * 127.1 + 11.7) * 43758.5453;
  return x - Math.floor(x);
}
export function mix(a: string, b: string, t: number): string {
  const p = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
  const A = p(a), B = p(b);
  return "#" + A.map((v, i) => Math.round(v + (B[i] - v) * t).toString(16).padStart(2, "0")).join("");
}

export function petalD(len: number, wid: number, type: string): string {
  if (type === "notch") {
    return `M0 0 C${wid} ${-len * 0.2} ${wid * 0.82} ${-len * 0.78} ${wid * 0.32} ${-len} L${wid * 0.14} ${-len * 0.86} L0 ${-len} L${-wid * 0.14} ${-len * 0.86} L${-wid * 0.32} ${-len} C${-wid * 0.82} ${-len * 0.78} ${-wid} ${-len * 0.2} 0 0Z`;
  }
  if (type === "thin") {
    return `M0 0 C${wid} ${-len * 0.3} ${wid * 0.7} ${-len * 0.86} 0 ${-len} C${-wid * 0.7} ${-len * 0.86} ${-wid} ${-len * 0.3} 0 0Z`;
  }
  if (type === "leaf") {
    return `M0 0 C${wid} ${-len * 0.22} ${wid * 0.9} ${-len * 0.8} 0 ${-len} C${-wid * 0.9} ${-len * 0.8} ${-wid} ${-len * 0.22} 0 0Z`;
  }
  return `M0 0 C${wid} ${-len * 0.1} ${wid * 1.02} ${-len * 0.7} 0 ${-len} C${-wid * 1.02} ${-len * 0.7} ${-wid} ${-len * 0.1} 0 0Z`;
}

export interface GardenFlower {
  k: SpeciesKey;
  i: number;
  bx: number; by: number; hx: number; hy: number;
  sc: number;
  openAt: number; openDur: number;
  wiltAt: number; wiltDur: number;
  drops: number[];
  bend: number; ph: number; spd: number; rot: number;
}

export function buildGarden(picks: SpeciesKey[]): GardenFlower[] {
  const n = Math.max(1, picks.length);
  const g = picks.map((k, i) => {
    const r1 = rn(i * 3 + 1), r2 = rn(i * 7 + 2), r3 = rn(i * 11 + 3);
    const angD = -34 + (i + 0.5) * (68 / n);
    const ang = (angD * Math.PI) / 180;
    const rad = 428 - Math.abs(angD) * 1.25 + (r1 - 0.5) * 26;
    const bx = 201 + (r3 - 0.5) * 14;
    const by = 742;
    const hx = cl(201 + Math.sin(ang) * rad * 0.68, 52, 350);
    const hy = by - Math.cos(ang) * rad;
    const sc = (k === "chamomile" || k === "eucalyptus" ? 0.92 : 1) * (0.94 + r2 * 0.28);
    const openAt = 0.05 + i * 0.021 + r1 * 0.02;
    const wiltAt = 0.5 + i * 0.036 + r2 * 0.035;
    const wiltDur = 0.2 + r3 * 0.08;
    const dn = SP[k].dropN;
    const drops: number[] = [];
    for (let j = 0; j < dn; j++) {
      drops.push(
        Math.min(0.985, wiltAt + wiltDur * (0.3 + 0.72 * (j / Math.max(1, dn - 1))) + (rn(i * 31 + j) - 0.5) * 0.02)
      );
    }
    return {
      k, i, bx, by, hx, hy, sc, openAt, openDur: 0.1 + r2 * 0.05, wiltAt, wiltDur, drops,
      bend: (r1 - 0.5) * 90, ph: r2 * 6.3, spd: 0.42 + r3 * 0.3, rot: (r3 - 0.5) * 16,
    };
  });
  g.sort((a, b) => a.hy - b.hy);
  return g;
}

export interface FillerSpec {
  kind: "euc" | "spirea" | "wax";
  tx: number; ty: number;
  bx: number; by: number;
  bend: number; sc: number; ph: number; spd: number;
}

export function buildFillers(): FillerSpec[] {
  const cx0 = 201, cy0 = 436, baseY = 742;
  const kinds: FillerSpec["kind"][] = ["euc", "spirea", "euc", "wax", "euc", "spirea", "wax", "euc", "spirea", "euc"];
  const specs: [FillerSpec["kind"], number, number, number][] = [];
  for (let i = 0; i < 10; i++) {
    const r = rn(i * 19 + 4);
    const ang = ((-80 + (i + 0.5) * (160 / 10)) * Math.PI) / 180;
    const rad = 178 + (r - 0.5) * 70 - Math.abs(ang) * 24;
    specs.push([kinds[i], cx0 + Math.sin(ang) * rad * 1.08, cy0 - Math.cos(ang) * rad * 0.84, ang * 30]);
  }
  return specs.map((s, i) => {
    const r = rn(i * 23 + 5);
    return {
      kind: s[0], tx: s[1], ty: s[2],
      bx: cx0 + (r - 0.5) * 14, by: baseY,
      bend: s[3], sc: 0.88 + r * 0.3, ph: r * 6.3, spd: 0.36 + r * 0.26,
    };
  });
}

export function relief(waterAt: number, p: number, cycleSeconds: number): number {
  if (waterAt < 0) return 0;
  const dt = (p - waterAt) * cycleSeconds;
  if (dt < 0) return 0;
  return 0.4 * (1 - Math.exp(-dt / 0.45)) * Math.exp(-dt / 8);
}

// Petals dropped so far are a pure function of `p` and each petal's scheduled
// `drops[j]` time, so scrubbing the timeline or reloading mid-animation is
// always visually correct — nothing here is a spawned/stateful particle.
type ExtraMap = Record<string, number>;

export function droppedAt(extra: ExtraMap, f: GardenFlower, j: number, p: number): number | null {
  const e = extra[f.i + "-" + j];
  const at = Math.min(f.drops[j] ?? 9, e ?? 9);
  return p > at ? at : null;
}

export function petalEl(uid: string, k: SpeciesKey, key: string, len: number, wid: number, type: string, transform: string, inner: boolean) {
  const sp = SP[k];
  const fill = `url(#${uid}${k}-${inner && sp.i ? "i" : "o"})`;
  return (
    <g key={key} transform={transform}>
      <path d={petalD(len, wid, type)} fill={fill} stroke={sp.line} strokeWidth={0.55} strokeOpacity={0.4} />
      {type !== "thin" && (
        <path d={`M0 ${-len * 0.12} Q${wid * 0.16} ${-len * 0.55} 0 ${-len * 0.9}`} fill="none" stroke={sp.line} strokeWidth={0.5} strokeOpacity={0.22} />
      )}
      {type === "round" && <path d={petalD(len * 0.5, wid * 0.88, "round")} fill={sp.line} opacity={0.15} />}
      {type === "round" && (
        <path d={`M${-wid * 0.16} ${-len * 0.94} Q${wid * 0.5} ${-len * 0.78} ${wid * 0.14} ${-len * 0.56}`} fill="none" stroke="#fffaf4" strokeWidth={1.1} strokeOpacity={0.32} strokeLinecap="round" />
      )}
    </g>
  );
}

export function headEls(uid: string, f: GardenFlower, bloom: number, wilt: number, p: number, extra: ExtraMap): React.ReactNode[] {
  const sp = SP[f.k];
  const out: React.ReactNode[] = [];
  const b = bloom, w = wilt;
  const droop = 1 - 0.16 * w;

  if (sp.kind === "rosette" && sp.rings) {
    sp.rings.forEach((r, ri) => {
      const [n, len, wid] = r;
      const inner = ri >= 2;
      for (let j = 0; j < n; j++) {
        if (ri === 0 && droppedAt(extra, f, j, p) !== null) continue;
        const a = (j / n) * 360 + ri * 24 + f.rot * 0.4;
        const open = 0.28 + 0.72 * b;
        const s = open * (1 - 0.06 * ri) * droop;
        const lift = (2 + ri * 1.4) * b;
        out.push(
          petalEl(uid, f.k, ri + "-" + j, len, wid, "round",
            `rotate(${a}) translate(0,${-lift}) scale(${s},${s * (1 - 0.1 * w)}) rotate(${(rn(j * 5 + ri) - 0.5) * 10})`, inner)
        );
      }
    });
    out.push(<circle key="c" r={3.4 * b} fill={sp.i ? sp.i[2] : "#fff"} opacity={0.9} />);
  } else if (sp.kind === "cup") {
    const back = [-34, 0, 34], front = [-17, 17];
    back.forEach((a, j) => {
      if (droppedAt(extra, f, j, p) !== null) return;
      out.push(petalEl(uid, f.k, "b" + j, 54, 25, "round", `rotate(${a * b + f.rot * 0.2}) scale(${(0.3 + 0.7 * b) * droop})`, false));
    });
    front.forEach((a, j) => {
      if (droppedAt(extra, f, j + 3, p) !== null) return;
      out.push(petalEl(uid, f.k, "f" + j, 46, 22, "round", `rotate(${a * b}) translate(0,3) scale(${(0.3 + 0.7 * b) * droop})`, true));
    });
    if (droppedAt(extra, f, 5, p) === null) {
      out.push(petalEl(uid, f.k, "f2", 40, 19, "round", `rotate(${f.rot * 0.2}) translate(0,5) scale(${(0.3 + 0.7 * b) * droop})`, true));
    }
  } else if (sp.kind === "flat" || sp.kind === "trumpet") {
    const n = sp.n!;
    for (let j = 0; j < n; j++) {
      if (droppedAt(extra, f, j, p) !== null) continue;
      const a = (j / n) * 360 + f.rot * 0.5;
      out.push(
        petalEl(uid, f.k, "p" + j, sp.len!, sp.wid!, sp.kind === "flat" ? "notch" : "thin",
          `rotate(${a}) translate(0,${-3 * b}) scale(${(0.24 + 0.76 * b) * droop},${(0.24 + 0.76 * b) * (1 - 0.14 * w)}) rotate(${(rn(j * 9) - 0.5) * 8 + w * 6})`, false)
      );
    }
    if (sp.kind === "trumpet" && sp.corona) {
      const cr = 11 * b;
      out.push(
        <g key="cor" opacity={b}>
          <ellipse rx={cr} ry={cr * 0.86} fill={sp.corona[1]} stroke={sp.corona[0]} strokeWidth={1} />
          <ellipse rx={cr * 0.62} ry={cr * 0.52} fill={sp.corona[0]} opacity={0.75} />
          <circle r={cr * 0.18} fill="#fff6d8" opacity={0.8} />
        </g>
      );
    } else if (sp.disc) {
      out.push(
        <g key="d" opacity={b}>
          <circle r={7.4} fill={sp.disc} />
          <circle r={7.4} fill="none" stroke="#c9922c" strokeWidth={1} strokeOpacity={0.5} />
          <circle r={3} fill="#d99a2a" opacity={0.55} />
        </g>
      );
    }
  } else if (sp.kind === "spray") {
    const pos: [number, number, number][] = [[2, -18, 1], [-26, 4, 0.92], [24, 8, 0.88], [-11, 28, 0.8], [15, -40, 0.72], [-2, 8, 1.04]];
    pos.forEach((pt, di) => {
      if (di < sp.dropN && droppedAt(extra, f, Math.min(di, sp.dropN - 1), p) !== null) return;
      const kids: React.ReactNode[] = [];
      for (let j = 0; j < 13; j++) {
        kids.push(petalEl(uid, f.k, "d" + di + "-" + j, 15, 4.4, "thin", `rotate(${(j / 13) * 360 + di * 11}) scale(${(0.2 + 0.8 * b) * droop})`, false));
      }
      kids.push(<circle key="c" r={4.6 * b} fill={sp.disc} />);
      kids.push(<circle key="c2" r={2.2 * b} fill="#d99a2a" opacity={0.5} />);
      out.push(<g key={"f" + di} transform={`translate(${pt[0]},${pt[1]}) scale(${pt[2] * (0.8 + 0.2 * b)})`}>{kids}</g>);
    });
  } else if (sp.kind === "green") {
    out.push(<path key="ax" d="M0 40 Q5 -30 -3 -100" stroke={sp.line} strokeWidth={2.1} fill="none" opacity={0.75} />);
    for (let j = 0; j < 11; j++) {
      const up = 32 - j * 13;
      const taper = 1 - (j / 11) * 0.42;
      const side = j % 2 ? 1 : -1;
      out.push(
        <path key={"l" + j} d={petalD(27 * taper, 8 * taper, "leaf")}
          fill={`url(#${uid}eucalyptus-o)`} stroke={sp.line} strokeWidth={0.55} strokeOpacity={0.3}
          transform={`translate(0,${up}) rotate(${side * (56 + w * 22)})`} opacity={0.62 + 0.38 * b} />
      );
    }
  }

  if (b < 0.94 && sp.kind !== "green") {
    const bs = 1 - ss(b / 0.9);
    out.push(
      <g key="bud" opacity={bs} transform="translate(0,10)">
        <path d={petalD(32, 14, "leaf")} fill="#93a377" stroke="#728157" strokeWidth={0.9} transform={`scale(${0.72 + 0.28 * bs})`} />
        <path d={petalD(22, 9, "leaf")} fill={sp.o[1]} opacity={0.6} transform="translate(0,-6)" />
      </g>
    );
  }
  return out;
}

export function stemEl(f: GardenFlower, w: number) {
  const sp = SP[f.k];
  const droopY = 64 * w;
  const hx = f.hx, hy = f.hy + droopY;
  const cx = (f.bx + hx) / 2 + f.bend * (1 + w * 1.5);
  const cy = f.by - (f.by - hy) * 0.55;
  return (
    <g key={"st" + f.i}>
      <path d={`M${f.bx} ${f.by} Q${cx} ${cy} ${hx} ${hy}`} fill="none" stroke={mix(sp.stem, "#a89a72", w * 0.55)} strokeWidth={4.1 * f.sc} strokeLinecap="round" />
      {[0.2, 0.42, 0.66].map((t, li) => {
        const mx = (1 - t) * (1 - t) * f.bx + 2 * (1 - t) * t * cx + t * t * hx;
        const my = (1 - t) * (1 - t) * f.by + 2 * (1 - t) * t * cy + t * t * hy;
        const dir = li % 2 ? 1 : -1;
        return (
          <path key={"l" + li} d={petalD(44 - li * 9, 11, "leaf")} fill={mix("#8fa073", "#b3a479", w * 0.6)} stroke="#728157" strokeWidth={0.6} strokeOpacity={0.5}
            transform={`translate(${mx},${my}) rotate(${dir * (62 + w * 18)}) scale(${f.sc})`} />
        );
      })}
    </g>
  );
}

export function fillerEl(uid: string, f: FillerSpec, w: number, i: number) {
  const bendW = f.bend * (1 + w * 1.1);
  const ty = f.ty + w * 34;
  const cx = (f.bx + f.tx) / 2 + bendW;
  const cy = f.by - (f.by - ty) * 0.55;
  const pt = (t: number): [number, number] => [
    (1 - t) * (1 - t) * f.bx + 2 * (1 - t) * t * cx + t * t * f.tx,
    (1 - t) * (1 - t) * f.by + 2 * (1 - t) * t * cy + t * t * ty,
  ];
  const els: React.ReactNode[] = [
    <path key="s" d={`M${f.bx} ${f.by} Q${cx} ${cy} ${f.tx} ${ty}`} fill="none" stroke={mix("#7f9060", "#ab9b74", w * 0.6)} strokeWidth={2.3 * f.sc} strokeLinecap="round" />,
  ];
  const n = f.kind === "euc" ? 13 : f.kind === "spirea" ? 9 : 7;
  const t0 = f.kind === "euc" ? 0.18 : 0.42;
  for (let j = 0; j < n; j++) {
    const t = t0 + (j / (n - 1)) * (1 - t0);
    const q = pt(t);
    const taper = 1 - (j / n) * 0.52;
    if (f.kind === "euc") {
      const side = j % 2 ? 1 : -1;
      els.push(
        <path key={"l" + j} d={petalD(26 * taper * f.sc, 7.6 * taper * f.sc, "leaf")} fill={`url(#${uid}eucalyptus-o)`} stroke="#5f6f49" strokeWidth={0.55} strokeOpacity={0.3}
          transform={`translate(${q[0]},${q[1]}) rotate(${side * (58 + w * 20)})`} />
      );
    } else if (f.kind === "spirea") {
      const cl_: React.ReactNode[] = [];
      for (let m = 0; m < 7; m++) {
        const a = (m / 7) * 6.283 + j;
        cl_.push(
          <circle key={m} cx={q[0] + Math.cos(a) * 7.4 * taper * f.sc} cy={q[1] + Math.sin(a) * 6.2 * taper * f.sc}
            r={4.2 * taper * f.sc} fill={mix("#fffaf1", "#c2a882", w)} stroke="#e6d8c2" strokeWidth={0.5} opacity={0.97} />
        );
      }
      cl_.push(<circle key="c" cx={q[0]} cy={q[1]} r={2 * taper * f.sc} fill="#f0c04a" opacity={0.65} />);
      els.push(<g key={"sp" + j}>{cl_}</g>);
    } else {
      for (let m = 0; m < 4; m++) {
        const a = (m / 4) * 6.283 + j * 1.7;
        els.push(
          <circle key={"w" + j + "-" + m} cx={q[0] + Math.cos(a) * 6.4 * taper * f.sc} cy={q[1] + Math.sin(a) * 5.4 * taper * f.sc}
            r={4 * taper * f.sc} fill={mix("#e3948d", "#bb9f80", w)} opacity={0.92} />
        );
      }
    }
  }
  return <g key={"fi" + i} opacity={0.9}>{els}</g>;
}

export function fallenEls(uid: string, garden: GardenFlower[], extra: ExtraMap, p: number, wind: number, cycleSeconds: number): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  garden.forEach((f) => {
    const sp = SP[f.k];
    if (!sp.dropN) return;
    for (let j = 0; j < sp.dropN; j++) {
      const at = droppedAt(extra, f, j, p);
      if (at === null) continue;
      const age = (p - at) * cycleSeconds;
      const k = cl(age / 2.8, 0, 1);
      const r = rn(f.i * 41 + j * 7);
      const fallY = k * k * 0.72 + k * 0.28;
      const restX = cl(f.hx * 0.55 + 201 * 0.45 + (r - 0.5) * 190, 16, W - 16);
      const restY = 796 + rn(f.i * 13 + j) * 40;
      const x = f.hx + (restX - f.hx) * fallY + Math.sin(k * 5 + r * 6) * 16 * (1 - k) + wind * 26 * (1 - k);
      const y = f.hy + (restY - f.hy) * fallY;
      const rot = r * 360 + k * (140 + r * 200) + (1 - k) * wind * 40;
      const len = sp.kind === "rosette" ? sp.rings![0][1] : sp.kind === "cup" ? 40 : sp.len || 14;
      const wid = sp.kind === "rosette" ? sp.rings![0][2] : sp.kind === "cup" ? 18 : sp.wid || 5;
      const type = sp.kind === "flat" ? "notch" : sp.kind === "spray" ? "thin" : "round";
      out.push(
        <g key={"fp" + f.i + "-" + j} transform={`translate(${x},${y}) rotate(${rot}) scale(${f.sc * (1 - 0.12 * k)},${f.sc * (1 - 0.52 * k)})`} opacity={0.92}>
          <path d={petalD(sp.kind === "spray" ? 13 : len, sp.kind === "spray" ? 5 : wid, type)} fill={`url(#${uid}${f.k}-o)`} stroke={sp.line} strokeWidth={0.5} strokeOpacity={0.35} />
        </g>
      );
    }
  });
  return out;
}

const SKY_KEYFRAMES: [number, [string, string]][] = [
  [0, ["#f7dfc6", "#f1c6a4"]], [0.13, ["#fdf2e0", "#f6ead9"]], [0.36, ["#fdf9ef", "#f5ead8"]],
  [0.6, ["#fdf0d9", "#f3e0c4"]], [0.78, ["#f8d8b2", "#e7b493"]], [0.9, ["#cd9a80", "#a4746b"]], [1, ["#3b2f36", "#251d24"]],
];

export function skyPair(p: number): [string, string] {
  let a = SKY_KEYFRAMES[0], b = SKY_KEYFRAMES[SKY_KEYFRAMES.length - 1];
  for (let i = 0; i < SKY_KEYFRAMES.length - 1; i++) {
    if (p >= SKY_KEYFRAMES[i][0] && p <= SKY_KEYFRAMES[i + 1][0]) { a = SKY_KEYFRAMES[i]; b = SKY_KEYFRAMES[i + 1]; }
  }
  const t = ss((p - a[0]) / Math.max(0.001, b[0] - a[0]));
  return [mix(a[1][0], b[1][0], t), mix(a[1][1], b[1][1], t)];
}

export function defsEl(uid: string, p: number) {
  const sky = skyPair(p);
  return (
    <defs>
      {ORDER.map((k) => {
        const sp = SP[k];
        return (["o", "i"] as const).map((v) => {
          const cols = v === "o" ? sp.o : sp.i;
          if (!cols) return null;
          return (
            <linearGradient key={k + v} id={uid + k + "-" + v} x1="0.1" y1="1" x2="0" y2="0">
              {cols.map((c, i) => <stop key={i} offset={(i / (cols.length - 1)) * 100 + "%"} stopColor={c} />)}
            </linearGradient>
          );
        });
      })}
      <linearGradient id={uid + "sky"} x1="0" y1="0" x2="0.2" y2="1">
        <stop offset="0%" stopColor={sky[0]} />
        <stop offset="100%" stopColor={sky[1]} />
      </linearGradient>
      <radialGradient id={uid + "sun"}>
        <stop offset="0%" stopColor="#fff6dc" stopOpacity={0.95} />
        <stop offset="100%" stopColor="#fbd9a0" stopOpacity={0} />
      </radialGradient>
    </defs>
  );
}

export interface SceneProps {
  uid: string;
  garden: GardenFlower[];
  fillers: FillerSpec[];
  p: number;
  wind: number;
  waterAt: number;
  clock: number;
  extra: ExtraMap;
  cycleSeconds: number;
  liftForCompose?: boolean;
  onTapStem?: (f: GardenFlower) => void;
}

export function BouquetScene({ uid, garden, fillers, p, wind, waterAt, clock, extra, cycleSeconds, liftForCompose, onTapStem }: SceneProps) {
  const night = ss((p - 0.84) / 0.14);
  const rel = relief(waterAt, p, cycleSeconds);

  const green = fillers.map((f, i) => {
    const gw = cl(ss((p - 0.58) / 0.34) - rel, 0, 1);
    const grow = ss(p / 0.1);
    const sway = (0.9 + wind * 6) * Math.sin(clock * f.spd + f.ph);
    return (
      <g key={"gr" + i} transform={`rotate(${sway} ${f.bx} ${f.by})`} style={{ filter: `saturate(${1 - 0.4 * gw}) brightness(${1 - 0.05 * gw})`, opacity: 0.35 + 0.65 * grow }}>
        {fillerEl(uid, f, gw, i)}
      </g>
    );
  });

  const bodies = garden.map((f) => {
    const bloom = ss((p - f.openAt) / f.openDur);
    const w = cl(ss((p - f.wiltAt) / f.wiltDur) - rel, 0, 1);
    const sway = (1.1 + wind * 5.5) * Math.sin(clock * f.spd + f.ph) + Math.sin(clock * 0.21 + f.ph) * 0.7;
    const droopY = 64 * w - 16 * rel;
    return (
      <g key={"fl" + f.i} transform={`rotate(${sway} ${f.bx} ${f.by})`} style={{ filter: `saturate(${1 - 0.42 * w + 0.3 * rel}) brightness(${1 - 0.07 * w + 0.05 * rel})` }}>
        {stemEl(f, w)}
        <g transform={`translate(${f.hx},${f.hy + droopY}) rotate(${w * 62 + f.rot * 0.3}) scale(${f.sc})`}
          onClick={() => onTapStem?.(f)} style={{ cursor: onTapStem ? "pointer" : "default" }}>
          <circle r={30} fill="transparent" />
          {headEls(uid, f, bloom, w, p, extra)}
        </g>
      </g>
    );
  });

  const tie = (
    <g key="tie">
      {[0, 1, 2, 3, 4].map((i) => (
        <path key={i} d={`M${201 + (i - 2) * 4} 690 Q${201 + (i - 2) * 11} 800 ${184 + i * 8} 884`}
          stroke={mix("#7e9159", "#a89a72", ss((p - 0.6) / 0.34) * 0.5)} strokeWidth={3.6} fill="none" strokeLinecap="round" opacity={0.92} />
      ))}
    </g>
  );

  const sunT = cl(p / 0.86, 0, 1);
  const sunX = -30 + 462 * sunT, sunY = 226 - 168 * Math.sin(Math.PI * sunT);
  const stars = night > 0.05
    ? [...Array(16)].map((_, i) => (
        <circle key={"s" + i} cx={rn(i * 3) * W} cy={40 + rn(i * 5) * 300} r={0.7 + rn(i * 7) * 1.1} fill="#fff" opacity={night * (0.35 + rn(i) * 0.5)} />
      ))
    : null;

  const wdt = waterAt >= 0 ? (p - waterAt) * cycleSeconds : -1;
  const drops = wdt >= 0 && wdt < 3.1
    ? [...Array(24)].map((_, i) => {
        const r = rn(i * 17 + 3), r2 = rn(i * 29 + 7), r3 = rn(i * 41 + 11);
        const k = (wdt - r * 0.95) / (0.95 + r2 * 0.35);
        if (k < 0) return null;
        const x = 34 + r * 334 + wind * 18;
        const land = 430 + r2 * 340;
        if (k <= 1) {
          const y = -24 + (land + 24) * (k * k * 0.84 + k * 0.16);
          const st = 1 + k * 1.1;
          return (
            <g key={"wd" + i} transform={`translate(${x},${y})`} opacity={0.8}>
              <ellipse rx={2.1} ry={5.4 * st} fill="#9dc3d4" opacity={0.7} />
              <ellipse cx={-0.7} cy={-1.4 * st} rx={0.7} ry={1.9 * st} fill="#f4fbff" opacity={0.75} />
            </g>
          );
        }
        const s = Math.min(1, (k - 1) / 0.6);
        if (s >= 1) return null;
        return (
          <g key={"ws" + i} transform={`translate(${x},${land})`}>
            <ellipse rx={3 + s * 15} ry={(3 + s * 15) * 0.34} fill="none" stroke="#9dc3d4" strokeWidth={1.5 * (1 - s)} opacity={0.55 * (1 - s)} />
            <circle cx={-3 - s * 5} cy={-6 * (1 - s) - s * 3} r={1.5 * (1 - s)} fill="#9dc3d4" opacity={0.6 * (1 - s)} />
            <circle cx={3.5 + s * 6} cy={-7 * (1 - s) - s * 2} r={1.7 * (1 - s)} fill="#9dc3d4" opacity={0.55 * (1 - s)} />
          </g>
        );
      })
    : null;
  const sheen = rel > 0.02 ? <rect width={W} height={H} fill="#cfe6ee" opacity={rel * 0.1} pointerEvents="none" /> : null;

  return (
    <svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid slice" style={{ position: "absolute", inset: 0, display: "block" }}>
      {defsEl(uid, p)}
      <rect width={W} height={H} fill={`url(#${uid}sky)`} />
      {stars}
      <circle cx={sunX} cy={sunY} r={54} fill={`url(#${uid}sun)`} opacity={0.85 * (1 - night)} />
      <circle cx={sunX} cy={sunY} r={15} fill="#fdf2cf" opacity={0.9 * (1 - night)} />
      {night > 0.05 && <circle cx={78} cy={152} r={13} fill="#f3ecd8" opacity={night * 0.9} />}
      <ellipse cx={201} cy={862} rx={210} ry={46} fill="#c9b394" opacity={0.28} />
      <g transform={`translate(0,${liftForCompose ? -128 : 0})`}>
        {green}
        {tie}
        {bodies}
        {fallenEls(uid, garden, extra, p, wind, cycleSeconds)}
      </g>
      {sheen}
      {drops}
      {night > 0.02 && <rect width={W} height={H} fill="#2b2839" opacity={night * 0.32} pointerEvents="none" />}
    </svg>
  );
}

export function fakeFlower(k: SpeciesKey): GardenFlower {
  return { k, i: 3, sc: 1, rot: 0, drops: [], hx: 0, hy: 0, bx: 0, by: 0, bend: 0, ph: 0, spd: 0, openAt: 0, openDur: 1, wiltAt: 0, wiltDur: 1 };
}

export function speciesIcon(uid: string, k: SpeciesKey, size = 30) {
  return (
    <svg width={size} height={size} viewBox="-30 -30 60 60">
      {defsEl(uid, 0.4)}
      <g transform="translate(0,4) scale(0.78)">{headEls(uid, fakeFlower(k), 1, 0, 0, {})}</g>
    </svg>
  );
}

export function pressedEl(uid: string, species: SpeciesKey) {
  const f = fakeFlower(species);
  return (
    <svg width={232} height={232} viewBox="-116 -116 232 232" style={{ filter: "saturate(0.52) brightness(1.05)", display: "block" }}>
      {defsEl(uid, 0.4)}
      <ellipse cx={0} cy={8} rx={92} ry={86} fill="#efe6d6" opacity={0.7} />
      <path d="M-84 54 Q-30 30 34 62" fill="none" stroke="#9aa87f" strokeWidth={2.4} opacity={0.7} />
      <path d={petalD(46, 13, "leaf")} fill="#9aa87f" opacity={0.6} transform="translate(-52,52) rotate(-52)" />
      <path d={petalD(38, 11, "leaf")} fill="#9aa87f" opacity={0.5} transform="translate(38,58) rotate(46)" />
      <g transform="translate(0,-10) rotate(-7) scale(1.95,1.62)">{headEls(uid, f, 1, 0.1, 0, {})}</g>
    </svg>
  );
}
