// Plan the day, and the evening's wrap-up. Picks are refs to work anywhere in the app (or a line of your own), in
// your order, each with your minutes; the total is measured against what's left of your working hours, less the day's
// meetings (from the briefing: Settings → Calendar). The wrap-up rolls the open ones to tomorrow, except those you let
// go, and keeps a line for tomorrow-you.
import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, ReactNode } from "react";
import { api } from "@core/api";
import type { SearchGroup } from "@core/api";
import { CloseIcon, PineIcon, SignpostIcon, icon } from "@core/components/icons";
import { Switch } from "@core/components/ui";
import { useShell } from "@core/shell";
import { ChevronDown, ChevronUp, Moon } from "lucide-react";
import { musterApi } from "./api";
import type { Day, Pick } from "./api";
import { Check, Part, clock, dayWords, hourMinutes, hourWords, minutesWords, readMinutes } from "./bits";
import { busy, freeBlocks } from "./time";

const UpIcon = icon(ChevronUp);
const DownIcon = icon(ChevronDown);
const EveningIcon = icon(Moon);

/** Picks still in today's plan (not carried on to another day, or let go). */
export const inPlan = (picks: Pick[]) => picks.filter((p) => !p.rolled_to && !p.let_go);

/** Runs a change, saying what went wrong if it did. */
function useAct() {
  const { toast } = useShell();
  return async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      return true;
    } catch (e) {
      toast((e as Error).message, "error");
      return false;
    }
  };
}

function MinutesField({ pick, day }: { pick: Pick; day: string }) {
  const act = useAct();
  const [text, setText] = useState(pick.minutes ? String(pick.minutes) : "");
  useEffect(() => setText(pick.minutes ? String(pick.minutes) : ""), [pick.minutes]);
  const save = () => {
    const n = readMinutes(text);
    if (n === undefined) {
      setText(pick.minutes ? String(pick.minutes) : "");
      return;
    }
    if (n !== pick.minutes) void act(() => musterApi.patchPick(day, pick.id, { minutes: n }));
  };
  return (
    <div className="relative w-[76px] shrink-0">
      <input
        aria-label={`Minutes for ${pick.title}`}
        value={text}
        inputMode="numeric"
        disabled={pick.done}
        onChange={(e) => setText(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => e.key === "Enter" && (e.currentTarget as HTMLInputElement).blur()}
        placeholder="—"
        className="field h-8 w-full py-0 pr-9 text-right tabular-nums"
        data-tip="Minutes: 45, 1h30…"
      />
      <span aria-hidden="true" className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-meta text-ink-soft">min</span>
    </div>
  );
}

function PickRow({ pick, day, index, count, onMove }: { pick: Pick; day: string; index: number; count: number; onMove: (to: number) => void }) {
  const act = useAct();
  const from = pick.first_day < day ? `From ${dayWords(pick.first_day, day)}` : null;
  const notes = [from, pick.done_there ? "Done where it lives" : null, pick.gone ? "Not there any more" : null].filter(Boolean);
  const keys = (e: KeyboardEvent<HTMLDivElement>) => {
    if (!e.altKey || (e.key !== "ArrowUp" && e.key !== "ArrowDown")) return;
    e.preventDefault();
    onMove(e.key === "ArrowUp" ? index - 1 : index + 1);
  };
  return (
    <div role="listitem" data-pick={pick.id} tabIndex={-1} onKeyDown={keys} className="group flex flex-wrap items-start gap-x-3 gap-y-2 px-4 py-2.5 focus-within:bg-forest/[.03] sm:flex-nowrap sm:px-5">
      <div className="flex w-full min-w-0 items-start gap-3 sm:w-auto sm:flex-1">
        <Check done={pick.done} label={pick.done ? `Mark ${pick.title} as not done` : `Mark ${pick.title} as done`} onToggle={() => void act(() => musterApi.patchPick(day, pick.id, { done: !pick.done }))} />
        <div className="min-w-0 flex-1">
          {pick.href ? (
            <a href={pick.href} className={`text-label leading-snug transition-colors hover:text-forest-deep ${pick.done ? "text-ink-soft line-through decoration-ink-faint" : ""}`}>
              {pick.title}
            </a>
          ) : (
            <span className={`text-label leading-snug ${pick.done ? "text-ink-soft line-through decoration-ink-faint" : ""}`}>{pick.title}</span>
          )}
          {notes.length > 0 && <div className="mt-0.5 text-hint text-ink-soft">{notes.join(" · ")}</div>}
        </div>
      </div>
      <div className="ml-[30px] flex shrink-0 items-center gap-1 sm:ml-0">
        <MinutesField pick={pick} day={day} />
        <button type="button" className="icon-btn h-8 w-8" disabled={index === 0} aria-label={`Move ${pick.title} up`} data-tip="Up (Alt ↑)" onClick={() => onMove(index - 1)}>
          <UpIcon size={16} />
        </button>
        <button type="button" className="icon-btn h-8 w-8" disabled={index === count - 1} aria-label={`Move ${pick.title} down`} data-tip="Down (Alt ↓)" onClick={() => onMove(index + 1)}>
          <DownIcon size={16} />
        </button>
        <button type="button" className="icon-btn h-8 w-8" aria-label={`Take ${pick.title} out of the plan`} data-tip="Take out of the plan" onClick={() => void act(() => musterApi.removePick(day, pick.id))}>
          <CloseIcon size={16} />
        </button>
      </div>
    </div>
  );
}

/** Search anything in the app to pick it, or add the words as a line of your own. */
function AddPick({ day, picked }: { day: string; picked: (ref: string) => boolean }) {
  const act = useAct();
  const [q, setQ] = useState("");
  const [found, setFound] = useState<SearchGroup[] | null>(null);
  const [active, setActive] = useState(-1);
  const box = useRef<HTMLInputElement>(null);
  const hits = (found ?? []).flatMap((g) => g.hits.map((h) => ({ ...h, module_name: g.module_name }))).filter((h) => !picked(h.ref)).slice(0, 8);

  useEffect(() => {
    const words = q.trim();
    if (!words) return setFound(null);
    const t = setTimeout(() => api.search(words).then(setFound, () => setFound([])), 160);
    return () => clearTimeout(t);
  }, [q]);
  useEffect(() => setActive(-1), [found]);

  const add = async (body: { ref?: string; title?: string; href?: string }) => {
    const asked = q;
    if (!(await act(() => musterApi.addPick(day, body)))) return;
    setQ((now) => (now === asked ? "" : now));          // unless you've typed on meanwhile
    box.current?.focus();
  };
  const keys = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" && hits.length) {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, hits.length - 1));
    } else if (e.key === "ArrowUp" && hits.length) {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, -1));
    } else if (e.key === "Escape") {
      setQ("");
    } else if (e.key === "Enter" && q.trim()) {
      e.preventDefault();
      const hit = hits[active];
      void add(hit ? { ref: hit.ref } : { title: q.trim() });
    }
  };

  return (
    <div className="relative px-4 py-3 sm:px-5">
      <input
        ref={box}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={keys}
        placeholder="Add a pick: find work, or type a line"
        aria-label="Add a pick"
        role="combobox"
        aria-expanded={!!q.trim()}
        aria-controls="muster-pick-options"
        aria-activedescendant={active >= 0 ? `muster-pick-${active}` : undefined}
        className="field h-9 w-full"
      />
      {q.trim() && (
        <div id="muster-pick-options" role="listbox" className="absolute inset-x-4 top-full z-20 -mt-1 animate-pop overflow-hidden rounded-md border border-line bg-surface py-1 shadow-lg sm:inset-x-5">
          {hits.map((h, i) => (
            <button
              key={h.ref}
              id={`muster-pick-${i}`}
              type="button"
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => void add({ ref: h.ref })}
              className={`block w-full px-3 py-2 text-left transition-colors hover:bg-forest/[.05] ${i === active ? "bg-forest/[.06]" : ""}`}
            >
              <span className="block truncate text-ui font-medium">{h.title}</span>
              <span className="block truncate text-meta text-ink-soft">{[h.module_name, h.snippet].filter(Boolean).join(" · ")}</span>
            </button>
          ))}
          <button
            type="button"
            role="option"
            aria-selected={active === -1}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => void add({ title: q.trim() })}
            className={`block w-full px-3 py-2 text-left text-ui transition-colors hover:bg-forest/[.05] ${active === -1 ? "bg-forest/[.06]" : ""}`}
          >
            Add “{q.trim()}” as a line of your own
          </button>
        </div>
      )}
    </div>
  );
}

export function useNow(everyMs = 60_000) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), everyMs);
    return () => clearInterval(t);
  }, [everyMs]);
  return now;
}

function Total({ day }: { day: Day }) {
  const now = useNow();
  const open = inPlan(day.picks).filter((p) => !p.done);
  const planned = open.reduce((n, p) => n + (p.minutes ?? 0), 0);
  const guessless = open.filter((p) => !p.minutes).length;
  const isToday = day.day === day.today;
  const today = day.briefing.sections.today;
  const blocks = freeBlocks(today, day.day, day.hours, isToday ? now : undefined);
  const left = blocks.reduce((n, [a, b]) => n + b - a, 0);
  const from = Math.max(hourMinutes(day.hours.start), isToday ? now.getHours() * 60 + now.getMinutes() : 0);
  const meetings = busy(today, day.day).filter(([a, b]) => b > from && a < hourMinutes(day.hours.end)).length;
  const known = busy(today, day.day).length > 0;
  const over = planned - left;
  const hours = `Working hours: ${hourWords(day.hours.start)} to ${hourWords(day.hours.end)} (Settings → Muster)`;
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3 text-hint text-ink-soft sm:px-5">
      <span>
        <span className="font-medium tabular-nums text-ink">{minutesWords(planned)}</span> planned
        {guessless ? ` · ${guessless} without minutes` : ""}
      </span>
      <span className={over > 0 ? "font-medium text-sun-deep" : ""} data-tip={known ? `${hours}, less today’s meetings` : hours}>
        {over > 0 ? `${minutesWords(over)} more than ` : ""}
        <span className="tabular-nums">{minutesWords(left)}</span> {known ? "free" : "left"} {isToday ? "today" : "in the day"}
        {meetings ? `, around ${meetings} ${meetings === 1 ? "meeting" : "meetings"}` : ""}
      </span>
    </div>
  );
}

/** suggestion: the AI's suggested plan, shown above the picks; aside: what goes at the top right ("Suggest a plan"). */
export function PlanTheDay({
  day,
  className,
  delay,
  aside,
  suggestion,
}: {
  day: Day;
  className?: string;
  delay?: number;
  aside?: ReactNode;
  suggestion?: ReactNode;
}) {
  const act = useAct();
  const picks = inPlan(day.picks);
  const elsewhere = day.picks.filter((p) => p.rolled_to || p.let_go);
  const picked = (ref: string) => picks.some((p) => p.ref === ref);
  const move = (pick: Pick, to: number) => {
    if (to < 0 || to >= picks.length) return;
    const rest = picks.filter((p) => p.id !== pick.id);
    const after = to === 0 ? null : rest[to - 1].id;
    void act(() => musterApi.movePick(day.day, pick.id, after)).then(() =>
      requestAnimationFrame(() => document.querySelector<HTMLElement>(`[data-pick="${pick.id}"]`)?.focus()),
    );
  };
  const carried = picks.filter((p) => p.first_day < day.day).length;
  return (
    <Part
      icon={<SignpostIcon size={16} />}
      title="Plan the day"
      blurb={carried ? `What you'll do today, in order. ${carried} carried over from before.` : "What you'll do today, in order."}
      className={className}
      delay={delay}
      aside={aside}
    >
      {suggestion}
      <div className="panel divide-y divide-line">
        {picks.length > 0 && (
          <div role="list" aria-label="Today's picks" className="divide-y divide-line">
            {picks.map((p, i) => (
              <PickRow key={p.id} pick={p} day={day.day} index={i} count={picks.length} onMove={(to) => move(p, to)} />
            ))}
          </div>
        )}
        {picks.length === 0 && (
          <p className="px-4 py-3 text-ui text-ink-soft sm:px-5">Nothing picked yet. Add from the lists here with +, or find anything below.</p>
        )}
        <AddPick day={day.day} picked={picked} />
        <Total day={day} />
      </div>
      {elsewhere.length > 0 && (
        <p className="mt-2 px-1 text-hint text-ink-soft">
          {elsewhere.filter((p) => p.rolled_to).length ? `Rolled to ${dayWords(elsewhere.find((p) => p.rolled_to)!.rolled_to!, day.day)}: ${elsewhere.filter((p) => p.rolled_to).map((p) => p.title).join(", ")}. ` : ""}
          {elsewhere.filter((p) => p.let_go).length ? `Let go: ${elsewhere.filter((p) => p.let_go).map((p) => p.title).join(", ")}.` : ""}
        </p>
      )}
    </Part>
  );
}

export function WrapUp({ day, className, delay, primary }: { day: Day; className?: string; delay?: number; primary: boolean }) {
  const { toast } = useShell();
  const open = inPlan(day.picks).filter((p) => !p.done);
  const done = day.picks.filter((p) => p.done);
  const rolled = day.picks.filter((p) => p.rolled_to);
  const goneBy = day.picks.filter((p) => p.let_go);
  const [letGo, setLetGo] = useState<Set<string>>(new Set());
  const [note, setNote] = useState(day.tomorrow_note);
  const [busy, setBusy] = useState(false);
  useEffect(() => setNote(day.tomorrow_note), [day.tomorrow_note]);

  const wrap = async () => {
    setBusy(true);
    try {
      const r = await musterApi.wrapUp(day.day, { let_go: [...letGo], note });
      const rolled = r.rolled ? `${r.rolled} ${r.rolled === 1 ? "pick rolls" : "picks roll"} to ${dayWords(r.to, day.day)}` : "Nothing rolls over";
      toast(`Wrapped up. ${rolled}.`, "success");
      setLetGo(new Set());
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  };

  const blurb = day.wrapped_up_at
    ? `Wrapped up at ${clock(day.wrapped_up_at)}. You can wrap up again if the day goes on.`
    : "When the day's done: what got done, what rolls to tomorrow, and a line for tomorrow-you.";
  return (
    <Part icon={<EveningIcon size={16} />} title="Wrap up" blurb={blurb} className={className} delay={delay}>
      <div className="panel divide-y divide-line">
        <div className="px-4 py-3 text-ui sm:px-5">
          <span className="font-medium">
            {done.length} of {day.picks.length} {day.picks.length === 1 ? "pick" : "picks"} done
          </span>
          <span className="text-ink-soft">
            {done.length > 0 && ` · ${done.map((p) => p.title).join(", ")}`}
            {rolled.length > 0 && ` · ${rolled.length} rolled to ${dayWords(rolled[0].rolled_to!, day.day)}`}
            {goneBy.length > 0 && ` · ${goneBy.length} let go`}
          </span>
        </div>
        {open.map((p) => {
          const rolls = !letGo.has(p.id);
          return (
            <div key={p.id} className="flex items-center justify-between gap-4 px-4 py-2.5 sm:px-5">
              <div className="min-w-0">
                <div className="truncate text-label">{p.title}</div>
                <div className="text-hint text-ink-soft">{rolls ? "Rolls to tomorrow" : "Let go: stays with today"}</div>
              </div>
              <Switch
                checked={rolls}
                label={`Roll ${p.title} to tomorrow`}
                onChange={(on) => setLetGo((s) => {
                  const next = new Set(s);
                  if (on) next.delete(p.id);
                  else next.add(p.id);
                  return next;
                })}
              />
            </div>
          );
        })}
        <div className="px-4 py-3 sm:px-5">
          <label htmlFor="muster-tomorrow" className="mb-1.5 flex items-center gap-2 text-label font-medium">
            <PineIcon size={16} className="text-ink-soft" />
            A line for tomorrow-you
          </label>
          <textarea
            id="muster-tomorrow"
            rows={2}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Where to start, what to remember…"
            className="field w-full resize-y leading-snug"
          />
          <div className="mt-3 flex justify-end">
            <button className={`btn btn-md ${primary ? "btn-primary" : "btn-soft"}`} disabled={busy} onClick={() => void wrap()}>
              {day.wrapped_up_at ? "Wrap up again" : "Wrap up the day"}
            </button>
          </div>
        </div>
      </div>
    </Part>
  );
}
