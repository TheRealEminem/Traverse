// Small pieces Muster's page shares: how it says days, times and minutes, a section's heading, the round check, and
// one line of the briefing.
import { useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { CheckIcon, ExternalIcon, PlusIcon } from "@core/components/icons";
import type { Entry } from "./api";

const noon = (iso: string) => new Date(`${iso}T12:00:00`);
const DAY = 86_400_000;

export const isoDay = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/** "Thu 22 Oct". */
export function dayName(iso: string): string {
  return noon(iso.slice(0, 10)).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
}

/** A day near `today` in words: "today", "tomorrow", "yesterday", "Thu 22 Oct". */
export function dayWords(iso: string, today: string): string {
  const n = Math.round((noon(iso.slice(0, 10)).getTime() - noon(today).getTime()) / DAY);
  return n === 0 ? "today" : n === 1 ? "tomorrow" : n === -1 ? "yesterday" : dayName(iso);
}

/** "9:04 am". */
export function clock(moment: string): string {
  return new Date(moment).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

/** A moment near today: "9:04 am", "yesterday 5:12 pm", "Mon 19 Oct 5:12 pm". */
export function momentWords(moment: string, today: string): string {
  const day = isoDay(new Date(moment));
  return day === today ? clock(moment) : `${dayWords(day, today)} ${clock(moment)}`;
}

/** An entry's "when": a day in words, or a moment. */
export function whenWords(when: string | null, today: string): string | null {
  if (!when) return null;
  return when.length === 10 ? dayWords(when, today) : momentWords(when, today);
}

/** "45 min", "1 h 30 min", "2 h". */
export function minutesWords(n: number): string {
  const h = Math.floor(n / 60);
  const m = n % 60;
  return h ? `${h} h${m ? ` ${m} min` : ""}` : `${m} min`;
}

/** "45", "45m", "2h", "1h30", "1:30" → minutes; "" → null; anything else → undefined. */
export function readMinutes(text: string): number | null | undefined {
  const t = text.trim().toLowerCase().replace(/\s+/g, "");
  if (!t) return null;
  let m = t.match(/^(\d+)(m|min|mins)?$/);
  if (m) return Number(m[1]);
  m = t.match(/^(\d+)(?:h|hr|hrs|:)(\d{1,2})?(?:m|min)?$/);
  if (m) return Number(m[1]) * 60 + Number(m[2] ?? 0);
  return undefined;
}

/** "09:00" → minutes since midnight. */
export const hourMinutes = (hhmm: string) => {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + (m || 0);
};

/** "09:00" as the clock shows it: "9:00 am". */
export const hourWords = (hhmm: string) => clock(`2026-01-01T${hhmm}:00`);

/** A part of the page: a forest well, a heading with a line under it, something on the right, then its content. */
export function Part({
  icon,
  title,
  blurb,
  aside,
  delay = 0,
  className = "",
  children,
}: {
  icon: ReactNode;
  title: string;
  blurb?: ReactNode;
  aside?: ReactNode;
  delay?: number;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={`min-w-0 animate-enter ${className}`} style={{ animationDelay: `${delay}ms` } as CSSProperties}>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-x-4 gap-y-2 px-1">
        <div className="flex min-w-0 items-start gap-3">
          <span className="well well-forest">{icon}</span>
          <div className="min-w-0">
            <h2 className="text-heading font-semibold tracking-[-0.01em]">{title}</h2>
            {blurb && <p className="mt-0.5 text-ui leading-snug text-ink-soft">{blurb}</p>}
          </div>
        </div>
        {aside}
      </div>
      {children}
    </section>
  );
}

/** A small heading inside a part. */
export function Sub({ children, count }: { children: ReactNode; count?: number }) {
  return (
    <h3 className="eyebrow mb-1.5 mt-5 flex items-center gap-2 px-1 first:mt-0">
      {children}
      {count ? <span className="tabular-nums text-ink-soft">{count}</span> : null}
    </h3>
  );
}

export function Check({ done, onToggle, label }: { done: boolean; onToggle: () => void; label: string }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={done}
      aria-label={label}
      onClick={onToggle}
      className={`mt-px flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border transition-colors duration-150 ${
        done ? "border-forest bg-forest text-on-accent" : "border-line-strong bg-surface hover:border-forest/60"
      }`}
    >
      {done && <CheckIcon size={12} strokeWidth={3} className="animate-check-pop" />}
    </button>
  );
}

const DOT: Record<string, string> = {
  trail: "bg-trail",
  sun: "bg-sun",
  sky: "bg-sky",
  forest: "bg-forest",
  berry: "bg-berry",
  neutral: "bg-ink-faint",
};

/** A tone as a dot, for lines where a chip would be too loud. Its meaning is always in the words beside it. */
export function Dot({ tone }: { tone: string }) {
  return <span aria-hidden="true" className={`mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full ${DOT[tone] ?? DOT.neutral}`} />;
}

/**
 * One line of the briefing: its tone, its title (opening it), what happened with who and when, and a way to put it in
 * today's plan. `hide` leaves out what the part already says (its project, when grouped by project).
 */
export function EntryRow({
  entry,
  today,
  picked,
  onPick,
  hide = [],
}: {
  entry: Entry;
  today: string;
  picked: boolean;
  onPick?: (e: Entry) => void;
  hide?: ("project" | "who")[];
}) {
  const when = whenWords(entry.when, today);
  const meta = [
    entry.what,
    !hide.includes("who") && entry.who && entry.who !== "You" ? entry.who : null,
    !hide.includes("project") && entry.project !== entry.title ? entry.project : null,
    when,
  ].filter(Boolean);
  return (
    <div className="group flex items-start gap-3 px-4 py-2.5 sm:px-5">
      <Dot tone={entry.tone} />
      <div className="min-w-0 flex-1">
        <div className="flex items-start gap-1.5">
          {entry.href ? (
            <a href={entry.href} className="min-w-0 text-label leading-snug transition-colors hover:text-forest-deep">
              {entry.title}
            </a>
          ) : (
            <span className="min-w-0 text-label leading-snug">{entry.title}</span>
          )}
          {entry.url && (
            <a
              href={entry.url}
              target="_blank"
              rel="noreferrer"
              className="icon-btn -my-1.5 h-7 w-7 shrink-0 text-ink-faint hover:text-ink"
              aria-label={`Open ${entry.title} in ${entry.module_name}`}
              data-tip={`Open in ${entry.module_name}`}
            >
              <ExternalIcon size={14} />
            </a>
          )}
        </div>
        <div className="mt-0.5 text-hint leading-snug text-ink-soft">{meta.join(" · ")}</div>
      </div>
      {onPick &&
        (picked ? (
          <span className="flex h-8 w-8 shrink-0 items-center justify-center text-forest" data-tip="In today’s plan" aria-label="In today’s plan">
            <CheckIcon size={16} />
          </span>
        ) : (
          <button
            type="button"
            className="icon-btn h-8 w-8 shrink-0"
            aria-label={`Add ${entry.title} to today’s plan`}
            data-tip="Add to today’s plan"
            onClick={() => onPick(entry)}
          >
            <PlusIcon size={16} />
          </button>
        ))}
    </div>
  );
}

/** A panel of briefing lines (the first `limit`, then "Show N more"), or a sentence when there are none. */
export function Entries({
  entries,
  empty,
  limit = 8,
  ...row
}: {
  entries: Entry[];
  empty: ReactNode;
  limit?: number;
  today: string;
  isPicked: (ref: string) => boolean;
  onPick?: (e: Entry) => void;
  hide?: ("project" | "who")[];
}) {
  const [all, setAll] = useState(false);
  if (!entries.length) return <p className="px-1 py-1 text-ui text-ink-soft">{empty}</p>;
  const cut = !all && entries.length > limit + 2;
  const shown = cut ? entries.slice(0, limit) : entries;
  return (
    <div className="panel divide-y divide-line py-1">
      {shown.map((e) => (
        <EntryRow key={`${e.ref}-${e.kind}-${e.what}`} entry={e} today={row.today} picked={row.isPicked(e.ref)} onPick={row.onPick} hide={row.hide} />
      ))}
      {cut && (
        <div className="px-2 pt-1">
          <button type="button" className="btn btn-sm btn-ghost" onClick={() => setAll(true)}>
            Show {entries.length - limit} more
          </button>
        </div>
      )}
    </div>
  );
}
