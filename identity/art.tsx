// Traverse's artwork, the identity's half of the family contract (core/web/components/illustrations.tsx re-exports
// it): Logo (the brand mark), Scene (a trail across a mountainside), Ambient (the app's atmosphere, with map lines) and Badge (the empty-state mark). Every family app's identity/art.tsx exports these four.
// Colors here are artwork, so they stay out of the tokens (DESIGN.md §10).
import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";

const reducedMotion = () =>
  typeof window !== "undefined" && (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false);

/** Stones as [cx, cy, rx, ry] on a cairn that stands on (0, 0), about 21 high: the shape every cairn here shares. */
const STONES: [number, number, number, number][] = [
  [0, -4.1, 10, 4],
  [0.5, -9.3, 8, 3.4],
  [-0.2, -14.2, 5.8, 2.8],
  [0.3, -18.2, 3.4, 2.1],
];

/** Brand mark: the family's tile in sunrise gold and orange, a pale sun, and a cairn of five balanced stones. */
export function Logo({ size = 36 }: { size?: number }) {
  const id = useId();
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" className="shrink-0">
      <defs>
        <linearGradient id={`${id}-bg`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#FFD05A" />
          <stop offset="1" stopColor="#F0702A" />
        </linearGradient>
        <linearGradient id={`${id}-sun`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#FFF6CF" />
          <stop offset="1" stopColor="#FFE08A" />
        </linearGradient>
        <clipPath id={`${id}-clip`}>
          <rect width="64" height="64" rx="16" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id}-clip)`}>
        <rect width="64" height="64" fill={`url(#${id}-bg)`} />
        <circle cx="47" cy="18" r="7.5" fill={`url(#${id}-sun)`} />
        <path d="M0 49 C 16 45, 30 43, 44 45 C 52 46, 58 48, 64 51 V64 H0Z" fill="#B8420F" fillOpacity="0.26" />
        <ellipse cx="30" cy="54" rx="17" ry="2.6" fill="#7A2C07" fillOpacity="0.3" />
        <ellipse cx="30" cy="48.6" rx="15.5" ry="5.6" fill="#FFF3D9" />
        {[
          [30.6, 42.8, 12.4, 5],
          [29.6, 35.4, 9.2, 4.3],
          [30.8, 28.8, 6.4, 3.5],
          [30, 22.7, 3.8, 2.6],
        ].map(([cx, cy, rx, ry]) => (
          <g key={cy}>
            <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="#C4781E" fillOpacity="0.38" />
            <ellipse cx={cx + 0.2} cy={cy - 1.4} rx={rx} ry={ry} fill="#FFF3D9" />
          </g>
        ))}
      </g>
      <rect x="0.5" y="0.5" width="63" height="63" rx="15.5" fill="none" stroke="#fff" strokeOpacity="0.2" />
    </svg>
  );
}

// ── The traverse ──────────────────────────────────────────────────────

// Day shows golden hour and Dusk shows sunset (as Trailmix does). The far ridge has a saddle in the middle; the trail
// climbs across the mountainside toward it, with a cairn at each turn, the nearest one large.
const DAY = {
  skyTop: "#FFAE42", skyBottom: "#FFEBC2", sun: "#FFF8DE", sunGlow: "#FFE08A",
  far: "#EDB07A", snow: "#FFFAEE", mid: "#CF7C43", near: "#A95A31", front: "#7E3F24",
  trail: "#FFF1D2", stone: "#FFF3D9", stoneShade: "#C4781E",
};
const DUSK = {
  skyTop: "#33202F", skyBottom: "#F28A44", sun: "#FFB84D", sunGlow: "#F7A455",
  far: "#6A4047", snow: "#EBCBA9", mid: "#54343A", near: "#412A2E", front: "#301F20",
  trail: "#F2D2A8", stone: "#F0D9B0", stoneShade: "#A97B4A",
};

/** A cairn of balanced stones standing on (x, y), at the given size. */
function Cairn({ x, y, s, P }: { x: number; y: number; s: number; P: typeof DAY }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <ellipse cx="0" cy="1.2" rx="12" ry="2.2" fill="#000" fillOpacity="0.14" />
      {STONES.map(([cx, cy, rx, ry]) => (
        <g key={cy}>
          <ellipse cx={cx + 0.6} cy={cy + 1.3} rx={rx} ry={ry} fill={P.stoneShade} fillOpacity="0.5" />
          <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill={P.stone} />
        </g>
      ))}
    </g>
  );
}

/** Follows the pointer a few pixels (nearer layers more), unless motion is reduced. */
function useDrift(on: boolean) {
  const [drift, setDrift] = useState({ x: 0, y: 0 });
  const frame = useRef(0);
  useEffect(() => {
    if (!on || reducedMotion()) return;
    const move = (e: PointerEvent) => {
      cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(() =>
        setDrift({ x: (e.clientX / window.innerWidth - 0.5) * 2, y: (e.clientY / window.innerHeight - 0.5) * 2 }),
      );
    };
    window.addEventListener("pointermove", move);
    return () => {
      window.removeEventListener("pointermove", move);
      cancelAnimationFrame(frame.current);
    };
  }, [on]);
  return (depth: number) => `translate(${(-drift.x * depth).toFixed(2)} ${(-drift.y * depth * 0.4).toFixed(2)})`;
}

/**
 * A trail traversing a mountainside toward a saddle, cairns along it. With `parallax`, the layers drift a few
 * pixels with the pointer. `dusk` draws the evening.
 */
export function Scene({ dusk = false, parallax = false, className = "" }: { dusk?: boolean; parallax?: boolean; className?: string }) {
  const id = useId();
  const P = dusk ? DUSK : DAY;
  const at = useDrift(parallax);
  const sun = dusk ? { x: 476, y: 150, r: 30 } : { x: 618, y: 66, r: 24 };
  return (
    <svg viewBox="0 0 800 260" preserveAspectRatio="xMidYMax slice" className={className} role="img"
      aria-label={dusk ? "A trail crossing a mountainside toward a saddle at sunset, with cairns along it" : "A trail crossing a mountainside toward a saddle, with cairns along it"}>
      <defs>
        <linearGradient id={`${id}-sky`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={P.skyTop} />
          <stop offset="1" stopColor={P.skyBottom} />
        </linearGradient>
        <radialGradient id={`${id}-glow`}>
          <stop offset="0" stopColor={P.sunGlow} stopOpacity="0.7" />
          <stop offset="1" stopColor={P.sunGlow} stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect width="800" height="260" fill={`url(#${id}-sky)`} />
      <g transform={at(1.5)}>
        <circle cx={sun.x} cy={sun.y} r={sun.r * 3.2} fill={`url(#${id}-glow)`} />
        <circle cx={sun.x} cy={sun.y} r={sun.r} fill={P.sun} />
      </g>
      <g transform={at(2.5)}>
        <path d="M-20 150 L90 116 L170 130 L262 92 L350 118 L420 138 L476 148 L530 134 L604 102 L692 76 L760 96 L820 88 V260 H-20Z" fill={P.far} />
        <path d="M232 104 L262 92 L290 104 L276 102 L262 108 L248 102Z" fill={P.snow} fillOpacity="0.9" />
        <path d="M660 88 L692 76 L724 88 L708 86 L692 92 L676 86Z" fill={P.snow} fillOpacity="0.9" />
      </g>
      <g transform={at(4)}>
        <path d="M-20 196 C 120 180, 260 158, 400 146 C 450 142, 476 141, 520 136 C 620 120, 720 108, 820 104 V260 H-20Z" fill={P.mid} />
        <path d="M-20 222 C 140 210, 300 190, 470 170 C 600 156, 720 150, 820 148 V260 H-20Z" fill={P.near} fillOpacity="0.55" />
        <g fill="none" strokeLinecap="round">
          <path d="M40 238 C 160 221, 256 198, 332 182 C 390 170, 432 156, 468 143" stroke="#000" strokeOpacity="0.1" strokeWidth="6.5" />
          <path d="M40 238 C 160 221, 256 198, 332 182 C 390 170, 432 156, 468 143" stroke={P.trail} strokeWidth="4" />
          <path d="M332 182 C 356 183, 368 179, 380 173" stroke={P.trail} strokeWidth="2" strokeOpacity="0.55" />
        </g>
        <Cairn x={452} y={150} s={0.45} P={P} />
        <Cairn x={336} y={183} s={0.78} P={P} />
      </g>
      <g transform={at(6)}>
        <path d="M-20 268 L-20 248 C 70 244, 150 238, 232 242 C 312 246, 372 254, 430 268Z" fill={P.front} />
        <Cairn x={128} y={226} s={1.75} P={P} />
      </g>
    </svg>
  );
}

// ── The map ───────────────────────────────────────────────────────────

// A survey grid on the 1600×1000 backdrop: two families of lines, turned a little and warped by a slow swell, so they
// cross at slightly different angles like the graticule on a map. Every fourth line is an index line, drawn heavier.
const warp = (x: number, y: number): [number, number] => [x + 44 * Math.sin(y / 240 + 0.7) + 14 * Math.sin(y / 90), y + 36 * Math.sin(x / 330 - 0.5)];
const turn = (x: number, y: number, a: number): [number, number] => [
  800 + (x - 800) * Math.cos(a) - (y - 500) * Math.sin(a),
  500 + (x - 800) * Math.sin(a) + (y - 500) * Math.cos(a),
];

function gridLines() {
  const out: { index: boolean; d: string }[] = [];
  const line = (all: [number, number][], index: boolean) => {
    const pts = all.filter(([x, y]) => x > -100 && x < 1700 && y > -100 && y < 1100);
    if (pts.length > 1) out.push({ index, d: pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(0)} ${y.toFixed(0)}`).join("") });
  };
  for (let i = -9; i <= 9; i++) {
    const pts: [number, number][] = [];
    for (let t = -500; t <= 1500; t += 50) pts.push(warp(...turn(800 + i * 210, t, -0.2)));
    line(pts, i % 4 === 0);
  }
  for (let j = -8; j <= 8; j++) {
    const pts: [number, number][] = [];
    for (let t = -900; t <= 2500; t += 50) pts.push(warp(...turn(t, 500 + j * 175, -0.13)));
    line(pts, j % 4 === 0);
  }
  return out;
}
const GRID = gridLines();

/** The app's atmosphere: a soft gradient, golden light high on the right, and faint map lines crossing the page. */
export function Ambient() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, var(--bg-top) 0%, var(--bg) 42%)" }} />
      <div className="absolute inset-0" style={{ background: "radial-gradient(55% 50% at 60% 62%, var(--glow-green), transparent 70%)" }} />
      <div className="absolute inset-0" style={{ background: "radial-gradient(34% 28% at 84% 2%, var(--glow-warm), transparent 72%)" }} />
      <svg
        viewBox="0 0 1600 1000"
        preserveAspectRatio="xMidYMid slice"
        className="absolute inset-0 h-full w-full"
        style={{
          WebkitMaskImage: "radial-gradient(95% 95% at 78% 18%, #000 30%, transparent 88%)",
          maskImage: "radial-gradient(95% 95% at 78% 18%, #000 30%, transparent 88%)",
        }}
      >
        <g fill="none" stroke="var(--grain)" strokeLinejoin="round">
          {GRID.map((l, i) => (
            <path key={i} d={l.d} strokeWidth={l.index ? 1.6 : 1} vectorEffect="non-scaling-stroke" />
          ))}
        </g>
      </svg>
    </div>
  );
}

/** Empty-state mark: an icon in a brand-colored well, ringed by a short dashed route with three waypoints. */
export function Badge({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`relative mx-auto flex h-20 w-20 items-center justify-center ${className}`}>
      <svg viewBox="0 0 64 64" className="absolute inset-0 h-full w-full text-forest" aria-hidden="true">
        <circle cx="32" cy="32" r="27" fill="none" stroke="currentColor" strokeOpacity="0.22" strokeWidth="1" strokeDasharray="2.6 3.4" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
        <g fill="currentColor" fillOpacity="0.3">
          <circle cx="13" cy="13" r="1.8" />
          <circle cx="58.5" cy="34" r="1.8" />
          <circle cx="22" cy="57.4" r="1.8" />
        </g>
      </svg>
      <span className="well well-forest relative h-10 w-10 rounded-md">{children}</span>
    </div>
  );
}
