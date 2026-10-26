// #/muster: the day's kick-off. What's on today and what waits on you, what moved since your last Muster (in
// Traverse and in Plane), the plan for the day, what's ahead, and the evening's wrap-up. Everything but the plan is
// the host's briefing (every module's part of it); the first look each day lands here (index.tsx's start). With AI
// on, a summary of what moved and a suggested plan (Ai.tsx); the day's meetings come through the briefing too
// (Meetings.tsx; calendars are added in Settings → Calendar).
import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { CompassIcon, FlagIcon, SunIcon, icon } from "@core/components/icons";
import { PageHeader, Segmented, Skeleton } from "@core/components/ui";
import { useLive } from "@core/live";
import { useShell } from "@core/shell";
import { History } from "lucide-react";
import { musterApi } from "./api";
import type { Day, Entry } from "./api";
import { MorningSummary, SuggestButton, SuggestedPlan } from "./Ai";
import { Entries, Part, Sub, clock, dayName, hourMinutes, momentWords } from "./bits";
import { TodayMeetings, WeekMeetings } from "./Meetings";
import { isScheduled } from "./time";
import { PlanTheDay, WrapUp, inPlan, useNow } from "./Plan";

const MovedIcon = icon(History);

const greeting = (h: number) => (h < 5 ? "Good evening" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening");
const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** What every list on the page needs to offer "Add to today's plan". */
function usePicking(day: Day) {
  const { toast } = useShell();
  const refs = new Set(inPlan(day.picks).map((p) => p.ref));
  return {
    today: day.day,
    isPicked: (ref: string) => refs.has(ref),
    onPick: (e: Entry) =>
      void musterApi.addPick(day.day, { ref: e.ref, title: e.title, href: e.href, minutes: e.minutes }).then(
        () => toast(`Added to today’s plan: ${e.title}`, "success"),
        (err: Error) => toast(err.message, "error"),
      ),
  };
}

export default function MusterView() {
  const { data: day, error } = useLive(musterApi.today);
  const now = useNow();
  const opened = useRef(false);
  useEffect(() => {
    if (opened.current) return;
    opened.current = true;
    void musterApi.openToday().catch(() => undefined);
  }, []);

  if (error && !day) {
    return (
      <div className="accent-mustard">
        <PageHeader title="Muster" />
        <div className="rounded-lg border border-trail/20 bg-trail-soft/70 p-4 text-label text-trail-deep">
          <div className="font-semibold">Muster didn't load</div>
          <div className="mt-0.5 opacity-90">{error}</div>
        </div>
      </div>
    );
  }
  if (!day) return <Loading />;

  const evening = new Date().getHours() * 60 + new Date().getMinutes() >= hourMinutes(day.hours.end) - 60;
  return (
    <div className="accent-mustard">
      <Header day={day} />
      <MorningSummary day={day} />
      {day.briefing.failed.length > 0 && (
        <p className="-mt-4 mb-6 px-1 text-hint text-ink-soft">
          {day.briefing.failed.join(" and ")} couldn't say {day.briefing.failed.length === 1 ? "its" : "their"} part just now; the rest is here.
        </p>
      )}
      <div className="flex flex-col gap-10 xl:grid xl:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] xl:items-start xl:gap-x-8">
        <div className="contents xl:flex xl:flex-col xl:gap-10">
          <KickOff day={day} now={now} className="order-1" />
          <Moved day={day} className="order-3" />
        </div>
        <div className="contents xl:flex xl:flex-col xl:gap-10">
          <PlanTheDay
            day={day}
            className="relative z-20 order-2"
            delay={120}
            aside={<SuggestButton day={day} />}
            suggestion={<SuggestedPlan day={day} now={now} />}
          />
          <Ahead day={day} className="order-4" />
          <WrapUp day={day} className="order-5" primary={!!day.kicked_off_at || evening} />
        </div>
      </div>
    </div>
  );
}

function Loading() {
  return (
    <div aria-busy="true" aria-label="Loading Muster">
      <Skeleton className="mb-3 h-4 w-40" />
      <Skeleton className="mb-10 h-9 w-72" />
      <div className="grid gap-8 xl:grid-cols-[7fr_5fr]">
        <Skeleton className="h-64 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    </div>
  );
}

// ── The top: the day, your intention, yesterday-you's note, kicking off ──

function Header({ day }: { day: Day }) {
  const { toast } = useShell();
  const s = day.briefing.sections;
  const counts = [
    s.today.length ? plural(s.today.length, "thing") + " on today" : null,
    s.waiting.length ? `${s.waiting.length} waiting on you` : null,
    s.moved.length ? `${s.moved.length} moved` : null,
  ].filter(Boolean);
  const kickOff = () => void musterApi.kickOff(day.day).then(() => toast("Kicked off. Have a good day.", "success"), (e: Error) => toast(e.message, "error"));
  return (
    <>
      <p className="eyebrow mb-2 animate-enter">
        {new Date(`${day.day}T12:00:00`).toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
      </p>
      <PageHeader
        title={greeting(new Date().getHours())}
        subtitle={counts.length ? counts.join(" · ") : "A quiet one so far."}
        actions={
          day.kicked_off_at ? (
            <span className="inline-flex items-center gap-2 text-ui text-ink-soft">
              <SunIcon size={16} className="text-forest" />
              Kicked off at {clock(day.kicked_off_at)}
            </span>
          ) : (
            <button className="btn btn-md btn-primary" onClick={kickOff}>
              <SunIcon size={18} />
              Kick off the day
            </button>
          )
        }
      />
      <Intention day={day} />
      {day.note && (
        <div className="-mt-2 mb-8 flex animate-enter items-start gap-3 rounded-lg border border-line bg-surface-subtle/70 px-4 py-3" style={{ animationDelay: "60ms" } as CSSProperties}>
          <span className="well">
            <FlagIcon size={16} />
          </span>
          <div className="min-w-0">
            <div className="text-meta font-medium text-ink-soft">From {dayName(day.note.day)}’s wrap-up</div>
            <div className="text-body leading-snug">{day.note.text}</div>
          </div>
        </div>
      )}
    </>
  );
}

function Intention({ day }: { day: Day }) {
  const { toast } = useShell();
  const [text, setText] = useState(day.intention);
  useEffect(() => setText(day.intention), [day.intention]);
  const save = () => {
    if (text.trim() === day.intention) return;
    void musterApi.patchDay(day.day, { intention: text }).catch((e: Error) => toast(e.message, "error"));
  };
  return (
    <div className="-mt-4 mb-8 animate-enter" style={{ animationDelay: "40ms" } as CSSProperties}>
      <label htmlFor="muster-intention" className="sr-only">
        A line for today
      </label>
      <input
        id="muster-intention"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => e.key === "Enter" && (e.currentTarget as HTMLInputElement).blur()}
        placeholder="One line for today: what would make it a good day?"
        className="field h-10 w-full max-w-[640px] text-label"
      />
    </div>
  );
}

// ── Kick-off: today, and what waits on you ─────────────────────────────

function KickOff({ day, now, className }: { day: Day; now: Date; className?: string }) {
  const pick = usePicking(day);
  const today = day.briefing.sections.today;
  const booked = today.filter(isScheduled);
  const recorded = today.filter((e) => e.kind === "meeting" && !isScheduled(e));    // Trailmix's, after the fact
  const team = today.filter((e) => e.kind === "past_due");
  const yours = today.filter((e) => e.kind !== "meeting" && e.kind !== "event" && e.kind !== "past_due");
  const waiting = day.briefing.sections.waiting;
  return (
    <Part icon={<SunIcon size={16} />} title="Today" blurb="Your meetings, what's due and in progress, and what waits on you." className={className} delay={60}>
      <Sub count={booked.length + recorded.length}>Meetings</Sub>
      <TodayMeetings entries={booked} now={now} />
      {recorded.length > 0 && (
        <div className="mt-2">
          <Entries entries={recorded} empty="" {...pick} onPick={undefined} />
        </div>
      )}
      <Sub count={yours.length}>Due and in progress</Sub>
      <Entries entries={yours} empty="Nothing due today, late or in progress." {...pick} />
      <Sub count={waiting.length}>Waiting on you</Sub>
      <Entries entries={waiting} empty="Nothing waits on you: no proposals to review, nothing to send." {...pick} />
      {team.length > 0 && (
        <>
          <Sub count={team.length}>Past due on the team</Sub>
          <Entries entries={team} empty="" {...pick} />
        </>
      )}
    </Part>
  );
}

// ── Since your last Muster ─────────────────────────────────────────────

type By = "project" | "person";

function group(entries: Entry[], by: By): [string, Entry[]][] {
  const groups = new Map<string, Entry[]>();
  for (const e of entries) {
    const key = by === "project" ? e.project || "No project" : e.who || "No one";
    groups.set(key, [...(groups.get(key) ?? []), e]);
  }
  const last = by === "person" ? "No one" : "No project";
  return [...groups.entries()].sort(([a, x], [b, y]) => (a === last ? 1 : b === last ? -1 : y.length - x.length || a.localeCompare(b)));
}

function Moved({ day, className }: { day: Day; className?: string }) {
  const pick = usePicking(day);
  const [by, setBy] = useState<By>("project");
  const moved = day.briefing.sections.moved;
  const since = day.first ? "in the last day" : `since your last Muster, ${momentWords(day.since, day.day)}`;
  return (
    <Part
      icon={<MovedIcon size={16} />}
      title="What moved"
      blurb={`In Traverse and in Plane, ${since}.`}
      className={className}
      delay={180}
      aside={
        moved.length > 0 ? (
          <Segmented<By>
            size="sm"
            label="Group what moved"
            value={by}
            onChange={setBy}
            options={[
              { id: "project", label: "By project" },
              { id: "person", label: "By person" },
            ]}
          />
        ) : undefined
      }
    >
      {moved.length === 0 ? (
        <p className="px-1 py-1 text-ui text-ink-soft">Nothing has moved {day.first ? "in the last day" : "since then"}. Plane’s changes show here from the first pull that records them.</p>
      ) : (
        group(moved, by).map(([name, entries]) => (
          <div key={name}>
            <Sub count={entries.length}>{name}</Sub>
            <Entries entries={entries} empty="" {...pick} hide={[by === "project" ? "project" : "who"]} />
          </div>
        ))
      )}
    </Part>
  );
}

// ── Look ahead ─────────────────────────────────────────────────────────

function Ahead({ day, className }: { day: Day; className?: string }) {
  const pick = usePicking(day);
  const ahead = [...day.briefing.sections.ahead].sort((a, b) => (a.kind === "at_risk" ? 1 : 0) - (b.kind === "at_risk" ? 1 : 0) || (a.when ?? "9999").localeCompare(b.when ?? "9999"));
  const risky = ahead.filter((e) => e.kind === "at_risk");
  const week = ahead.filter(isScheduled);
  const dated = ahead.filter((e) => e.kind !== "at_risk" && !isScheduled(e));
  return (
    <Part icon={<CompassIcon size={16} />} title="Look ahead" blurb="This week's due dates, milestones and cycles ending, meetings, and projects at risk." className={className} delay={240}>
      <Entries entries={dated} empty="Nothing due in the next seven days." {...pick} />
      {week.length > 0 && (
        <>
          <Sub count={week.length}>Meetings this week</Sub>
          <WeekMeetings entries={week} />
        </>
      )}
      {risky.length > 0 && (
        <>
          <Sub count={risky.length}>Projects at risk</Sub>
          <Entries entries={risky} empty="" {...pick} onPick={undefined} />
        </>
      )}
    </Part>
  );
}
