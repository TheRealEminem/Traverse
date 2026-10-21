import { json, request } from "@core/api";
import type { Tone } from "@core/components/ui";

export type SectionName = "today" | "waiting" | "moved" | "ahead";

/** One line of the day's briefing, as its module wrote it (core/server/briefing.py). */
export interface Entry {
  ref: string;
  module: string;
  module_name: string;
  title: string;
  href: string | null;
  /** What happened, or why it's here: "Due today", "To do → In progress · by Mickey". */
  what: string;
  /** Who it's about, or who has it now. */
  who: string | null;
  /** A day (YYYY-MM-DD) or a moment. */
  when: string | null;
  project: string | null;
  kind: string | null;
  tone: Tone;
  minutes: number | null;
  /** Where it opens outside Traverse (Plane). */
  url: string | null;
}

export interface Briefing {
  today: string;
  since: string;
  sections: Record<SectionName, Entry[]>;
  /** Modules whose part didn't come through. */
  failed: string[];
}

export interface Pick {
  id: string;
  ref: string | null;
  title: string;
  href: string | null;
  minutes: number | null;
  /** Ticked here, or done where it lives. */
  done: boolean;
  /** Done where it lives, not ticked here. */
  done_there: boolean;
  /** Its module doesn't know it any more. */
  gone: boolean;
  module: string | null;
  first_day: string;
  rolled_to: string | null;
  let_go: boolean;
}

export interface Day {
  day: string;
  today: string;
  since: string;
  /** The very first Muster: nothing before it. */
  first: boolean;
  opened_at: string | null;
  kicked_off_at: string | null;
  wrapped_up_at: string | null;
  intention: string;
  tomorrow_note: string;
  /** The line your last wrap-up left for this day. */
  note: { day: string; text: string } | null;
  picks: Pick[];
  hours: { start: string; end: string };
  briefing: Briefing;
}

export interface WrappedUp {
  to: string;
  done: number;
  rolled: number;
  let_go: number;
}

const day = (d: string) => `/muster/days/${d}`;

export const musterApi = {
  start: () => request<{ path: string | null }>("/muster/start").then((r) => r.path),
  today: () => request<Day>("/muster/today"),
  openToday: () => request<Day>("/muster/today/open", json("POST")),
  patchDay: (d: string, changes: { intention?: string; tomorrow_note?: string }) => request<{ ok: true }>(day(d), json("PATCH", changes)),
  kickOff: (d: string) => request<{ ok: true }>(`${day(d)}/kickoff`, json("POST")),
  wrapUp: (d: string, body: { let_go: string[]; note: string }) => request<WrappedUp>(`${day(d)}/wrapup`, json("POST", body)),
  addPick: (d: string, body: { ref?: string; title?: string; href?: string | null; minutes?: number | null }) =>
    request<Pick>(`${day(d)}/picks`, json("POST", body)),
  patchPick: (d: string, id: string, changes: { minutes?: number | null; done?: boolean; title?: string }) =>
    request<Pick>(`${day(d)}/picks/${id}`, json("PATCH", changes)),
  movePick: (d: string, id: string, after: string | null) => request<Pick[]>(`${day(d)}/picks/${id}/move`, json("POST", { after })),
  removePick: (d: string, id: string) => request<void>(`${day(d)}/picks/${id}`, { method: "DELETE" }),
};
