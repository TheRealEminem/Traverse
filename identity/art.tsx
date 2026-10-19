// Traverse's artwork, the identity's half of the family contract (core/web/components/illustrations.tsx re-exports
// it): Logo (the brand mark), Scene (a trail across a mountainside), Ambient (the app's atmosphere, with a route
// drawn on a map) and Badge (the empty-state mark). Every family app's identity/art.tsx exports these four.
// Colors here are artwork, so they stay out of the tokens (DESIGN.md §10).
import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";

const reducedMotion = () =>
  typeof window !== "undefined" && (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false);

/** Brand mark: the family's tile in sky, a low sun, and a trail crossing a slope to a small cairn. */
export function Logo({ size = 36 }: { size?: number }) {
  const id = useId();
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" className="shrink-0">
      <defs>
        <linearGradient id={`${id}-bg`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#4F86A8" />
          <stop offset="1" stopColor="#285B7A" />
        </linearGradient>
        <linearGradient id={`${id}-sun`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#F8CB5A" />
          <stop offset="1" stopColor="#EE8540" />
        </linearGradient>
        <clipPath id={`${id}-clip`}>
          <rect width="64" height="64" rx="16" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id}-clip)`}>
        <rect width="64" height="64" fill={`url(#${id}-bg)`} />
        <path d="M0 52 C 18 46, 36 36, 64 22 V64 H0Z" fill="#fff" fillOpacity="0.08" />
        <g fill="none" stroke="#F4EEDC" strokeLinecap="round" strokeWidth="1.3">
          <path d="M-2 59 C 18 53, 38 43, 66 30" opacity="0.2" />
          <path d="M-2 66 C 20 60, 40 51, 66 39" opacity="0.13" />
        </g>
        <circle cx="19" cy="19" r="6.5" fill={`url(#${id}-sun)`} />
        <path d="M7 59 C 17 54, 26 49.5, 36 44.8" fill="none" stroke="#F6EBCF" strokeWidth="3.4" strokeLinecap="round" />
        <g fill="#F6EBCF">
          <ellipse cx="42.2" cy="42" rx="5" ry="2.5" />
          <ellipse cx="41.9" cy="37.9" rx="3.6" ry="1.9" />
          <ellipse cx="42.3" cy="34.6" rx="2.3" ry="1.5" />
        </g>
      </g>
      <rect x="0.5" y="0.5" width="63" height="63" rx="15.5" fill="none" stroke="#fff" strokeOpacity="0.16" />
    </svg>
  );
}

// ── The traverse ──────────────────────────────────────────────────────

// Day shows day and Dusk shows dusk (as Trailmix does). The far ridge has a saddle in the middle; the trail climbs
// across the mountainside toward it, with a cairn at each turn, the nearest one large.
const DAY = {
  skyTop: "#9CC3DA", skyBottom: "#EAF0EA", sun: "#F8CB5A", sunGlow: "#FBE7B0",
  far: "#A9BCC6", snow: "#F7F4EC", mid: "#7F9C90", near: "#5F8171", front: "#4B6C5C",
  trail: "#F4EEDC", stone: "#E9E0C9", stoneShade: "#C9BC9D",
};
const DUSK = {
  skyTop: "#1C2B40", skyBottom: "#C98E72", sun: "#F2A65A", sunGlow: "#F0B07A",
  far: "#43506A", snow: "#C9BFB4", mid: "#344A58", near: "#2A3E48", front: "#21323A",
  trail: "#E2D2B2", stone: "#CDBD9C", stoneShade: "#9F9177",
};

/** A cairn of three stones standing on (x, y), at the given size. */
function Cairn({ x, y, s, P }: { x: number; y: number; s: number; P: typeof DAY }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <ellipse cx="0" cy="1.2" rx="11" ry="2.2" fill="#000" fillOpacity="0.12" />
      <ellipse cx="0" cy="-3" rx="10" ry="4.4" fill={P.stone} />
      <ellipse cx="1.2" cy="-1.6" rx="8" ry="2.6" fill={P.stoneShade} fillOpacity="0.55" />
      <ellipse cx="-0.6" cy="-10.6" rx="7.4" ry="3.6" fill={P.stone} />
      <ellipse cx="0.6" cy="-9.4" rx="5.6" ry="2" fill={P.stoneShade} fillOpacity="0.5" />
      <ellipse cx="0.4" cy="-16.8" rx="4.6" ry="2.8" fill={P.stone} />
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

// ── The route ─────────────────────────────────────────────────────────

const ROUTE = "M960 70 C 1040 130, 1120 30, 1210 96 S 1360 196, 1450 128 S 1560 50, 1660 96";
const ROUTE_LOW = "M-40 900 C 60 860, 140 940, 240 888 S 380 820, 470 870";
const WAYPOINTS: [number, number][] = [[960, 70], [1210, 96], [1450, 128], [240, 888]];

/** The app's atmosphere: a soft gradient, warm light high on the right, and a faint route on a map. */
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
        <g fill="none" stroke="var(--grain)" strokeWidth="1.6" strokeDasharray="7 9" strokeLinecap="round">
          <path d={ROUTE} vectorEffect="non-scaling-stroke" />
          <path d={ROUTE_LOW} vectorEffect="non-scaling-stroke" />
        </g>
        <g fill="var(--grain)">
          {WAYPOINTS.map(([x, y]) => (
            <circle key={`${x}-${y}`} cx={x} cy={y} r="5" />
          ))}
        </g>
      </svg>
    </div>
  );
}

/** Empty-state mark: an icon in a forest well, ringed by a short dashed route with three waypoints. */
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
