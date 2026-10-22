// The day's meetings on Muster's page, from the briefing (Traverse's calendar module gives them; calendars are added in
// Settings → Calendar): today's in Today, and the next week's in Look ahead.
import type { Entry } from "./api";
import { Dot, dayName, minutesWords } from "./bits";
import { busy, entryTimes, isAllDay } from "./time";

function MeetingRow({ entry, now }: { entry: Entry; now: Date }) {
  const allDay = isAllDay(entry);
  const start = new Date(entry.when!);
  const end = new Date(start.getTime() + (entry.minutes ?? 0) * 60_000);
  const past = !allDay && end <= now;
  const on = !allDay && start <= now && !past;
  const meta = [allDay ? "All day" : entryTimes(entry), on ? "Now" : null, entry.what === "Shown as free" ? entry.what : null, entry.project].filter(Boolean);
  return (
    <div className={`flex items-start gap-3 px-4 py-2.5 sm:px-5 ${past ? "opacity-60" : ""}`}>
      <Dot tone={on ? "sky" : "neutral"} />
      <div className="min-w-0 flex-1">
        <div className={`text-label leading-snug ${past ? "text-ink-soft" : ""}`}>{entry.title}</div>
        <div className="mt-0.5 text-hint leading-snug text-ink-soft">{meta.join(" · ")}</div>
      </div>
    </div>
  );
}

/** Today's meetings, all-day ones first, then in order. */
export function TodayMeetings({ entries, now }: { entries: Entry[]; now: Date }) {
  if (!entries.length) {
    return <p className="px-1 py-1 text-ui text-ink-soft">No meetings today. Calendars you add in Settings → Calendar show here.</p>;
  }
  const shown = [...entries].sort((a, b) => Number(isAllDay(b)) - Number(isAllDay(a)) || (a.when ?? "").localeCompare(b.when ?? ""));
  return (
    <div className="panel divide-y divide-line py-1" aria-label="Today’s meetings">
      {shown.map((e) => (
        <MeetingRow key={e.ref} entry={e} now={now} />
      ))}
    </div>
  );
}

/** How many meetings each of the next seven days has, how long they take, and what they are. */
export function WeekMeetings({ entries }: { entries: Entry[] }) {
  const days = new Map<string, Entry[]>();
  for (const e of entries) {
    const day = (e.when ?? "").slice(0, 10);
    days.set(day, [...(days.get(day) ?? []), e]);
  }
  return (
    <div className="panel divide-y divide-line py-1" aria-label="Meetings this week">
      {[...days.entries()]
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([day, list]) => {
          const timed = busy(list, day);
          const minutes = timed.reduce((n, [a, b]) => n + b - a, 0);
          const allDay = list.filter(isAllDay);
          const count = [
            timed.length ? `${timed.length} ${timed.length === 1 ? "meeting" : "meetings"}, ${minutesWords(minutes)}` : null,
            allDay.length ? `${allDay.length} all day` : null,
          ].filter(Boolean);
          const titles = list.map((e) => e.title);
          return (
            <div key={day} className="flex items-start gap-3 px-4 py-2.5 sm:px-5">
              <Dot tone="neutral" />
              <div className="min-w-0 flex-1">
                <div className="text-label leading-snug">
                  {dayName(day)} <span className="text-ink-soft">· {count.join(" · ") || "Free time only"}</span>
                </div>
                <div className="mt-0.5 truncate text-hint leading-snug text-ink-soft">
                  {titles.slice(0, 4).join(", ")}
                  {titles.length > 4 ? `, and ${titles.length - 4} more` : ""}
                </div>
              </div>
            </div>
          );
        })}
    </div>
  );
}
