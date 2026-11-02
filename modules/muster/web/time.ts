// The day's meetings as Muster's page plans around them: briefing lines that say when they start ("when", this
// computer's time) and how long they take ("minutes"); Traverse's calendar module gives them (server/meetings.py reads
// them the same way). Also the free time they leave in your working hours, and where things of so many minutes fit
// into it, in order.
import type { Entry } from "./api";
import { hourMinutes, isoDay } from "./bits";

const SHORTEST_GAP = 5;
const midnight = (day: string) => new Date(`${day}T00:00:00`);

/** A meeting or event from a calendar (all day, or with a length); not one Trailmix recorded after the fact. */
export const isScheduled = (e: Entry) => (e.kind === "meeting" || e.kind === "event") && (e.minutes != null || e.when?.length === 10);
export const isAllDay = (e: Entry) => e.kind === "event" && e.when?.length === 10;

/** Where a meeting starts and ends, in minutes since midnight on `day`, cut to the day. */
function span(e: Entry, day: string): [number, number] {
  const start = Math.round((new Date(e.when!).getTime() - midnight(day).getTime()) / 60_000);
  return [Math.max(0, start), Math.min(24 * 60, start + (e.minutes ?? 0))];
}

/** The meetings that take time on `day`, in order. */
export function busy(entries: Entry[], day: string): [number, number, Entry][] {
  return entries
    .filter((e) => e.kind === "meeting" && e.minutes && (e.when?.length ?? 0) > 10)
    .map((e) => [...span(e, day), e] as [number, number, Entry])
    .filter(([a, b]) => b > a)
    .sort((x, y) => x[0] - y[0] || x[1] - y[1]);
}

/** The free stretches of the working day, in minutes since midnight: working hours less the meetings that take time,
 *  and on the day itself less what's gone by. */
export function freeBlocks(entries: Entry[], day: string, hours: { start: string; end: string }, now?: Date): [number, number][] {
  let at = hourMinutes(hours.start);
  const finish = hourMinutes(hours.end);
  if (now && isoDay(now) === day) at = Math.max(at, now.getHours() * 60 + now.getMinutes());
  const blocks: [number, number][] = [];
  for (const [start, end] of busy(entries, day)) {
    if (start > at) blocks.push([at, Math.min(start, finish)]);
    at = Math.max(at, end);
    if (at >= finish) break;
  }
  if (at < finish) blocks.push([at, finish]);
  return blocks.filter(([a, b]) => b - a >= SHORTEST_GAP);
}

/** Where something lands in the day: start and end in minutes since midnight (across: it runs over a meeting, since no
 *  free stretch is long enough), "full" when what's left of the day can't hold it, or null with no estimate. */
export type Slot = { start: number; end: number; across: boolean } | "full" | null;

/** Lays things of so many minutes, in order, into the free stretches: each in the first one from where the last ended
 *  that holds it whole, or else across the stretches from there. */
export function fit(lengths: (number | null)[], blocks: [number, number][]): Slot[] {
  let b = 0;
  let at = blocks[0]?.[0] ?? 0;
  return lengths.map((m) => {
    if (!m) return null;
    for (let i = b; i < blocks.length; i++) {
      const from = Math.max(at, blocks[i][0]);
      if (blocks[i][1] - from >= m) {
        b = i;
        at = from + m;
        return { start: from, end: at, across: false };
      }
    }
    let need = m;
    for (let i = b, from = Math.max(at, blocks[b]?.[0] ?? 0), start = from; i < blocks.length; i++, from = blocks[i]?.[0] ?? 0) {
      const room = blocks[i][1] - from;
      if (room >= need) {
        b = i;
        at = from + need;
        return { start, end: at, across: true };
      }
      need -= Math.max(0, room);
    }
    return "full";
  });
}

const times = () => new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" });

/** "9:00 – 9:45 AM", in this computer's way of saying times. */
export function timeRange(day: string, start: number, end: number): string {
  const at = (m: number) => new Date(midnight(day).getTime() + m * 60_000);
  return times().formatRange(at(start), at(end));
}

/** A meeting's times, "10:00 – 10:30 AM". */
export function entryTimes(e: Entry): string {
  const start = new Date(e.when!);
  return times().formatRange(start, new Date(start.getTime() + (e.minutes ?? 0) * 60_000));
}
