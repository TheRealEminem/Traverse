import { json, request } from "@core/api";
import type { Job } from "@core/api";
import type { Tone } from "@core/components/ui";

export type SectionName = "today" | "waiting" | "moved" | "ahead";

/** One line of the day's briefing, as its module wrote it (core/server/briefing.py). */
export interface Entry {
  ref: string;
  module: string;
  module_name: string;
  title: string;
  href: string | null;
  /** What happened, or why it's here: "Due today", "To do → In progress · by Sam". */
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

/** The morning summary (summary.py): written by an AI, which `by` names. */
export interface Summary {
  text: string | null;
  by: string | null;
  at: string | null;
  /** How many lines of "what moved" it covered. */
  moved: number | null;
  job: Job | null;
}

/** One pick the AI suggests (suggest.py). */
export interface Proposal {
  id: string;
  ref: string;
  title: string;
  href: string | null;
  module: string;
  minutes: number | null;
  reason: string;
  state: "proposed" | "accepted" | "dropped";
  /** The day's pick it became. */
  pick_id: string | null;
}

export interface SuggestedPlan {
  status: "suggesting" | "ready";
  asked_at: string;
  written_by: string | null;
  made_at: string | null;
  note: string | null;
  meetings: number;
  free_minutes: number | null;
  proposals: Proposal[];
  job: Job | null;
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
  /** AI in Muster (Settings → Muster). */
  ai: boolean;
  summary: Summary;
  plan: SuggestedPlan | null;
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
  writeSummary: (d: string) => request<Summary>(`${day(d)}/summary`, json("POST")),
  suggestPlan: (d: string) => request<SuggestedPlan>(`${day(d)}/plan`, json("POST")),
  discardPlan: (d: string) => request<void>(`${day(d)}/plan`, { method: "DELETE" }),
  acceptAll: (d: string) => request<{ accepted: number }>(`${day(d)}/plan/accept`, json("POST")),
  acceptProposal: (d: string, id: string) => request<Proposal>(`${day(d)}/plan/${id}/accept`, json("POST")),
  patchProposal: (d: string, id: string, changes: { state?: "proposed" | "dropped"; minutes?: number | null }) =>
    request<Proposal>(`${day(d)}/plan/${id}`, json("PATCH", changes)),
  moveProposal: (d: string, id: string, after: string | null) => request<Proposal[]>(`${day(d)}/plan/${id}/move`, json("POST", { after })),
};
