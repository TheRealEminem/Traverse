// Traverse's artwork, the identity's half of the family contract (core/web/components/illustrations.tsx re-exports
// it): Logo (the brand mark), Scene (a trail across a mountainside), Ambient (the app's atmosphere, a faint map) and
// Badge (the empty-state mark). Every family app's identity/art.tsx exports these four.
// Colors here are artwork, so they stay out of the tokens (DESIGN.md §10).
import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";

const reducedMotion = () =>
  typeof window !== "undefined" && (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false);

// A cairn as a trail has them: six stones, flat where they rest, uneven in width (a narrow one can hold a wider one),
// each tilted a little and set a little off the one below. Each is [shadow, stone]: the shadow is the same stone
// nudged down and right, so every stone sits on the one below it. Drawn by pebble() in a 64-unit tile (the mark), and
// the same stones scaled to stand about 21 high on (0, 0) (the scene's cairns).
const MARK_STONES: [string, string][] = [
  ["M18.0 50.4C18.5 45.7 34.1 44.1 41.9 46.8C43.8 49.1 41.9 52.3 31.9 53.0C21.3 53.2 17.5 52.1 18.0 50.4Z", "M17.5 49.1C18.0 44.4 33.6 42.8 41.4 45.5C43.3 47.8 41.4 51.0 31.4 51.7C20.8 51.9 17.0 50.8 17.5 49.1Z"],
  ["M20.5 42.5C21.2 39.3 32.6 39.1 41.3 41.7C42.7 43.4 40.9 45.6 32.2 45.4C23.1 44.8 19.9 43.7 20.5 42.5Z", "M20.0 41.2C20.7 38.0 32.1 37.8 40.8 40.4C42.2 42.1 40.4 44.3 31.7 44.1C22.6 43.5 19.4 42.4 20.0 41.2Z"],
  ["M22.6 37.8C22.6 33.8 32.7 31.9 36.9 34.0C38.1 35.8 37.2 38.6 31.2 39.6C24.8 40.1 22.4 39.3 22.6 37.8Z", "M22.1 36.5C22.1 32.5 32.2 30.6 36.4 32.7C37.6 34.5 36.7 37.3 30.7 38.3C24.3 38.8 21.9 38.0 22.1 36.5Z"],
  ["M22.3 29.6C23.0 26.6 32.9 26.8 40.4 29.4C41.6 31.0 39.9 33.0 32.4 32.6C24.5 31.8 21.7 30.7 22.3 29.6Z", "M21.8 28.3C22.5 25.3 32.4 25.5 39.9 28.1C41.1 29.7 39.4 31.7 31.9 31.3C24.0 30.5 21.2 29.4 21.8 28.3Z"],
  ["M25.9 24.8C26.0 21.5 32.0 20.4 35.4 22.3C36.2 23.9 35.5 26.2 31.5 26.7C27.3 26.8 25.8 26.0 25.9 24.8Z", "M25.4 23.5C25.5 20.2 31.5 19.1 34.9 21.0C35.7 22.6 35.0 24.9 31.0 25.4C26.8 25.5 25.3 24.7 25.4 23.5Z"],
  ["M28.6 18.9C29.0 16.8 32.3 16.8 34.1 18.4C34.3 19.5 33.7 20.8 31.4 20.7C29.1 20.3 28.3 19.6 28.6 18.9Z", "M28.1 17.6C28.5 15.5 31.8 15.5 33.6 17.1C33.8 18.2 33.2 19.5 30.9 19.4C28.6 19.0 27.8 18.3 28.1 17.6Z"],
];
const STONES: [string, string][] = [
  ["M-6.9 -0.9C-6.6 -3.6 2.4 -4.5 6.9 -3.0C7.9 -1.7 6.8 0.2 1.1 0.6C-5.0 0.7 -7.2 0.0 -6.9 -0.9Z", "M-7.2 -1.7C-6.9 -4.4 2.1 -5.3 6.6 -3.7C7.6 -2.4 6.5 -0.6 0.8 -0.1C-5.3 -0.1 -7.5 -0.7 -7.2 -1.7Z"],
  ["M-5.5 -5.4C-5.0 -7.3 1.5 -7.4 6.5 -5.9C7.3 -4.9 6.3 -3.7 1.3 -3.8C-4.0 -4.1 -5.8 -4.8 -5.5 -5.4Z", "M-5.8 -6.2C-5.3 -8.1 1.2 -8.2 6.2 -6.7C7.0 -5.7 6.0 -4.4 1.0 -4.5C-4.3 -4.9 -6.1 -5.5 -5.8 -6.2Z"],
  ["M-4.2 -8.2C-4.3 -10.4 1.6 -11.6 4.0 -10.4C4.7 -9.3 4.2 -7.7 0.7 -7.1C-3.0 -6.8 -4.4 -7.3 -4.2 -8.2Z", "M-4.5 -8.9C-4.6 -11.2 1.3 -12.3 3.7 -11.1C4.4 -10.1 3.9 -8.4 0.4 -7.9C-3.3 -7.6 -4.7 -8.1 -4.5 -8.9Z"],
  ["M-4.4 -12.9C-4.0 -14.6 1.7 -14.5 6.0 -13.0C6.7 -12.0 5.7 -10.9 1.4 -11.1C-3.2 -11.6 -4.8 -12.2 -4.4 -12.9Z", "M-4.7 -13.6C-4.3 -15.4 1.4 -15.3 5.7 -13.7C6.4 -12.8 5.4 -11.7 1.1 -11.9C-3.5 -12.4 -5.1 -13.0 -4.7 -13.6Z"],
  ["M-2.3 -15.7C-2.3 -17.6 1.1 -18.2 3.1 -17.1C3.6 -16.2 3.2 -14.8 0.9 -14.5C-1.5 -14.5 -2.4 -15.0 -2.3 -15.7Z", "M-2.6 -16.4C-2.6 -18.3 0.8 -18.9 2.8 -17.8C3.3 -16.9 2.9 -15.6 0.6 -15.3C-1.8 -15.3 -2.7 -15.7 -2.6 -16.4Z"],
  ["M-0.8 -19.0C-0.6 -20.2 1.3 -20.2 2.4 -19.3C2.5 -18.7 2.1 -17.9 0.8 -18.0C-0.5 -18.2 -0.9 -18.6 -0.8 -19.0Z", "M-1.1 -19.8C-0.9 -21.0 1.0 -21.0 2.1 -20.1C2.2 -19.4 1.8 -18.7 0.5 -18.7C-0.8 -19.0 -1.2 -19.4 -1.1 -19.8Z"],
];

/** Brand mark: the family's tile in sunrise gold and orange, a pale sun, and a cairn of six balanced stones. */
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
        <ellipse cx="30" cy="53" rx="16" ry="2.4" fill="#7A2C07" fillOpacity="0.3" />
        {MARK_STONES.map(([shadow, stone]) => (
          <g key={stone}>
            <path d={shadow} fill="#C4781E" fillOpacity="0.4" />
            <path d={stone} fill="#FFF3D9" />
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
      <ellipse cx="0" cy="0.6" rx="10" ry="1.6" fill="#000" fillOpacity="0.14" />
      {STONES.map(([shadow, stone]) => (
        <g key={stone}>
          <path d={shadow} fill={P.stoneShade} fillOpacity="0.5" />
          <path d={stone} fill={P.stone} />
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
        <Cairn x={452} y={150} s={0.52} P={P} />
        <Cairn x={336} y={183} s={0.9} P={P} />
      </g>
      <g transform={at(6)}>
        <path d="M-20 268 L-20 248 C 70 244, 150 238, 232 242 C 312 246, 372 254, 430 268Z" fill={P.front} />
        <Cairn x={128} y={226} s={2} P={P} />
      </g>
    </svg>
  );
}

// ── The map ───────────────────────────────────────────────────────────

// The backdrop is a faint, abstract map on a 1600×1000 sheet (Trailmix has contours, The Lodge has rings): two main
// roads and two lanes crossing, towns as clusters of blocks where they meet, a river with a bridge, a lake, spot
// heights, a camp and a viewpoint, and a dashed trail switchbacking up the slope: a traverse. docs/index.html has a
// copy of the same map as plain SVG: change both together.
const MAP: {
  trail: string;
  river: string;
  roads: [string, number][]; // [path, width]: main roads 4, lanes 2
  houses: [number, number, number][];
  lake: string;
  peaks: [number, number, string][];
  camp: [number, number];
  view: [number, number];
  bridge: [number, number];
} = {
  trail: "M-40 900 C 120 870, 260 800, 380 812 C 470 820, 520 780, 470 742 C 430 712, 520 668, 640 668 C 770 668, 860 620, 812 578 C 772 544, 860 500, 980 506 C 1100 512, 1180 470, 1130 424 C 1090 388, 1170 344, 1280 344 C 1390 344, 1450 300, 1404 258 C 1370 228, 1440 186, 1530 170 C 1580 162, 1620 140, 1660 120",
  river: "M1660 600 C 1560 590, 1520 520, 1430 548 C 1340 576, 1330 650, 1230 660 C 1130 670, 1080 610, 990 640 C 900 670, 900 760, 820 800 C 740 840, 660 820, 600 880 C 560 920, 560 980, 520 1060",
  roads: [
    ["M-40 500 C 240 470, 420 520, 600 500 C 780 480, 900 440, 1100 420 C 1300 400, 1460 430, 1660 380", 4],
    ["M990 -40 C 1030 120, 1080 280, 1100 420 C 1118 548, 1150 640, 1156 760 C 1162 880, 1140 960, 1150 1040", 4],
    ["M1100 420 C 1190 360, 1300 300, 1410 262 C 1460 245, 1510 230, 1560 196 C 1600 170, 1630 130, 1660 110", 2],
    ["M600 500 C 640 420, 700 360, 760 300 C 800 260, 820 200, 860 140 C 880 110, 900 60, 910 -40", 2],
  ],
  // [x, y, size]: houses, in clusters where roads meet
  houses: [
    [1062, 392, 16], [1084, 374, 12], [1128, 390, 14], [1152, 374, 11], [1066, 448, 14], [1090, 468, 11], [1130, 446, 16],
    [1156, 462, 12], [1044, 418, 10], [1174, 410, 10],
    [572, 474, 13], [594, 464, 10], [626, 480, 12], [578, 528, 12], [608, 526, 14], [636, 516, 9],
    [1540, 178, 11], [1568, 224, 10], [1590, 168, 9], [1528, 214, 8],
  ],
  lake: "M1268 96 C 1280 66, 1344 54, 1388 72 C 1432 90, 1428 128, 1388 140 C 1344 152, 1258 128, 1268 96Z",
  peaks: [[1206, 236, "2412"], [1478, 382, "2187"], [972, 300, "1964"]],
  camp: [1020, 548],
  view: [1430, 226],
  bridge: [1150, 656],
};

const VIEW_RAYS = Array.from({ length: 8 }, (_, i) => {
  const a = (i * Math.PI) / 4;
  const [x, y] = MAP.view;
  return `M${(x + 7 * Math.cos(a)).toFixed(1)} ${(y + 7 * Math.sin(a)).toFixed(1)}L${(x + 11 * Math.cos(a)).toFixed(1)} ${(y + 11 * Math.sin(a)).toFixed(1)}`;
}).join("");

/** The app's atmosphere: a soft gradient, golden light high on the right, and a faint map. */
export function Ambient() {
  const [bx, by] = MAP.bridge;
  const [cx, cy] = MAP.camp;
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
        <g fill="none" stroke="var(--grain)" strokeLinejoin="round" strokeLinecap="round">
          <path d={MAP.lake} fill="var(--grain)" fillOpacity="0.5" strokeWidth="1.4" />
          <path d={MAP.river} strokeWidth="2.2" />
          {MAP.roads.map(([d, w]) => (
            <path key={d} d={d} strokeWidth={w} />
          ))}
          <path d={MAP.trail} strokeWidth="2.4" strokeDasharray="9 8" />
          <g strokeWidth="1.8">
            <path d={`M${bx - 11} ${by - 12}Q${bx - 15} ${by} ${bx - 11} ${by + 12}M${bx + 11} ${by - 12}Q${bx + 15} ${by} ${bx + 11} ${by + 12}`} />
            <path d={`M${cx - 8} ${cy + 6}L${cx} ${cy - 8}L${cx + 8} ${cy + 6}ZM${cx} ${cy - 8}L${cx} ${cy + 6}`} />
            <circle cx={MAP.view[0]} cy={MAP.view[1]} r="4" />
            <path d={VIEW_RAYS} />
          </g>
        </g>
        <g fill="var(--grain)" style={{ font: "500 13px ui-monospace, Menlo, monospace", letterSpacing: "0.06em" }}>
          {MAP.houses.map(([x, y, s]) => (
            <rect key={`${x}-${y}`} x={x - s / 2} y={y - s / 2} width={s} height={s} transform={`rotate(-8 ${x} ${y})`} />
          ))}
          {MAP.peaks.map(([x, y, h]) => (
            <g key={h}>
              <path d={`M${x - 6} ${y + 5}L${x} ${y - 6}L${x + 6} ${y + 5}Z`} />
              <text x={x + 10} y={y + 5}>{h}</text>
            </g>
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
