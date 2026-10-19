// Small pieces the Team view is made of: the state split bar and its legend, people's initials, dates.
import type { CSSProperties } from "react";
import { Avatar } from "@core/components/blocks";
import { initials, formatDate, relativeTime } from "@core/format";
import type { Group, Split } from "./api";

/** The open state groups in the order work moves through them, each with its word and its mark's color. Status is
 *  never color alone: every bar has a legend with the words and counts, and a tooltip on each segment. */
export const GROUPS: { id: Group; label: string; swatch: string }[] = [
  { id: "triage", label: "Triage", swatch: "bg-sun" }, // new and not looked at: needs someone
  { id: "backlog", label: "Backlog", swatch: "bg-ink-faint/45" }, // set aside: the quietest step
  { id: "unstarted", label: "To do", swatch: "bg-ink-soft/80" }, // planned: a firmer neutral
  { id: "started", label: "In progress", swatch: "bg-sky" }, // working on it
];

const shown = (split: Split) => GROUPS.filter((g) => g.id !== "triage" || split.triage > 0);

/** A stacked bar of open items by state. `scale` is the count that fills the track, so bars compare across cards. */
export function StateBar({ split, scale, label, height = 8 }: { split: Split; scale: number; label: string; height?: number }) {
  const total = GROUPS.reduce((n, g) => n + split[g.id], 0);
  const parts = shown(split).filter((g) => split[g.id] > 0);
  return (
    <div
      role="img"
      aria-label={`${label}: ${parts.map((g) => `${split[g.id]} ${g.label.toLowerCase()}`).join(", ") || "nothing open"}`}
      className="flex w-full rounded-full bg-surface-subtle"
      style={{ height }}
    >
      <div className="flex gap-[2px]" style={{ width: `${scale ? Math.max((total / scale) * 100, total ? 2 : 0) : 0}%` }}>
        {parts.map((g, i) => (
          <span
            key={g.id}
            data-tip={`${split[g.id]} ${g.label.toLowerCase()}`}
            className={`${g.swatch} min-w-[4px] ${i === 0 ? "rounded-l-full" : ""} ${i === parts.length - 1 ? "rounded-r-full" : ""}`}
            style={{ flexGrow: split[g.id], flexBasis: 0 } as CSSProperties}
          />
        ))}
      </div>
    </div>
  );
}

/** "5 backlog · 6 to do · 12 in progress", each with its swatch. */
export function StateLegend({ split, zeros = false }: { split: Split; zeros?: boolean }) {
  const parts = shown(split).filter((g) => zeros || split[g.id] > 0);
  if (!parts.length) return <span className="text-meta text-ink-soft">Nothing open</span>;
  return (
    <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-meta text-ink-soft">
      {parts.map((g) => (
        <span key={g.id} className="inline-flex items-center gap-1.5 whitespace-nowrap">
          <span aria-hidden="true" className={`h-2 w-2 rounded-full ${g.swatch}`} />
          <span>
            <span className="tabular-nums">{split[g.id]}</span> {g.label.toLowerCase()}
          </span>
        </span>
      ))}
    </span>
  );
}

/** The bars' key: each state's swatch and word, without counts. */
export function StateKey({ triage = false }: { triage?: boolean }) {
  return (
    <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-meta text-ink-soft">
      {GROUPS.filter((g) => triage || g.id !== "triage").map((g) => (
        <span key={g.id} className="inline-flex items-center gap-1.5 whitespace-nowrap">
          <span aria-hidden="true" className={`h-2 w-2 rounded-full ${g.swatch}`} />
          {g.label}
        </span>
      ))}
    </span>
  );
}

/** A teammate's initials; yours on sky (You = sky); a dashed ring for "No one". */
export function PersonAvatar({ name, me, none, size = 32 }: { name: string; me?: boolean; none?: boolean; size?: number }) {
  if (none) {
    return (
      <span
        aria-hidden="true"
        className="grid shrink-0 place-items-center rounded-full border border-dashed border-line-strong text-ink-soft"
        style={{ width: size, height: size, fontSize: Math.round(size * 0.36) }}
      >
        –
      </span>
    );
  }
  if (me) {
    return (
      <span
        aria-hidden="true"
        className="grid shrink-0 place-items-center rounded-full bg-sky-soft font-semibold text-sky-deep"
        style={{ width: size, height: size, fontSize: Math.round(size * 0.36) }}
      >
        {initials(name)}
      </span>
    );
  }
  return <Avatar name={name} size={size} />;
}

/** "just now", "4 minutes ago", "2 hours ago", then the family's relative dates. */
export function since(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return "never";
  const minutes = Math.round((now - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} ${minutes === 1 ? "minute" : "minutes"} ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} ${hours === 1 ? "hour" : "hours"} ago`;
  return relativeTime(iso, now);
}

/** A due date as a person reads it in a list: late in trail, soon in sun, later plain, with the date in a tooltip. */
export function Due({ date, late, soon }: { date: string | null; late: boolean; soon: boolean }) {
  if (!date) return <span className="text-meta text-ink-soft">No date</span>;
  const words = relativeTime(date);
  const tip = formatDate(date);
  if (late) {
    const days = Math.max(1, Math.round((Date.now() - new Date(`${date}T12:00:00`).getTime()) / 86_400_000));
    return (
      <span className="chip bg-trail-soft text-trail-deep" data-tip={`Was due ${tip}`}>
        {plural(days, "day")} late
      </span>
    );
  }
  if (soon)
    return (
      <span className="chip bg-sun-soft text-sun-deep" data-tip={`Due ${tip}`}>
        Due {words}
      </span>
    );
  return (
    <span className="text-meta tabular-nums text-ink-soft" data-tip={`Due ${tip}`}>
      {formatDate(date, { year: undefined })}
    </span>
  );
}

export const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
