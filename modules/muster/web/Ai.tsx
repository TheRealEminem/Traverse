// The AI's part of Muster (chunk 15b): the morning summary of what moved, and a suggested plan for the day, fitted into
// the free time between your meetings. Each says which AI wrote it. The plan never applies itself: you accept, move or
// drop each pick, and an accepted one joins today's picks.
import { useState } from "react";
import type { CSSProperties } from "react";
import { JobStatus } from "@core/components/blocks";
import { CheckIcon, RefreshIcon, SparkleIcon, icon } from "@core/components/icons";
import { Spinner } from "@core/components/ui";
import { useShell } from "@core/shell";
import { ChevronDown, ChevronUp } from "lucide-react";
import { musterApi } from "./api";
import type { Day, Proposal } from "./api";
import { clock, minutesWords } from "./bits";
import type { Slot } from "./time";
import { busy, fit, freeBlocks, timeRange } from "./time";
import { inPlan } from "./Plan";

const UpIcon = icon(ChevronUp);
const DownIcon = icon(ChevronDown);

/** Runs a change, saying what went wrong if it did; `busy` says which is running. */
function useAct() {
  const { toast } = useShell();
  const [busyWith, setBusy] = useState<string | null>(null);
  const act = async (what: string, work: () => Promise<unknown>, done?: string) => {
    setBusy(what);
    try {
      await work();
      if (done) toast(done, "success");
      return true;
    } catch (e) {
      toast((e as Error).message, "error");
      return false;
    } finally {
      setBusy(null);
    }
  };
  return { act, busy: busyWith };
}

const working = (status?: string) => status === "queued" || status === "running";

// ── The morning summary ───────────────────────────────────────────────

export function MorningSummary({ day }: { day: Day }) {
  const { act, busy: writing } = useAct();
  const s = day.summary;
  const moved = day.briefing.sections.moved.length;
  if (!day.ai) return null;
  const job = s.job;
  const write = () => void act("write", () => musterApi.writeSummary(day.day));
  const style = { animationDelay: "80ms" } as CSSProperties;

  if (working(job?.status)) {
    return (
      <div className="inset-surface -mt-2 mb-8 animate-enter px-4 py-3.5" style={style} aria-label="Writing the morning summary">
        <JobStatus job={job} />
      </div>
    );
  }
  const failed = job?.status === "error" ? (
    <div className="-mt-2 mb-3">
      <JobStatus job={job} />
    </div>
  ) : null;
  if (!s.text) {
    if (!moved) return failed && <div className="mb-5">{failed}</div>;
    return (
      <div className="-mt-2 mb-8 animate-enter" style={style}>
        {failed}
        {!failed && (
          <button className="btn btn-sm btn-soft" disabled={!!writing} onClick={write}>
            {writing ? <Spinner /> : <SparkleIcon size={16} />}
            Sum up what moved
          </button>
        )}
      </div>
    );
  }
  const since = moved - (s.moved ?? 0);
  return (
    <div className="-mt-2 mb-8 animate-enter" style={style}>
      {failed}
      <section aria-label="Morning summary" className="flex items-start gap-3 rounded-lg border border-line bg-surface px-4 py-3.5 shadow-sm sm:px-5">
        <span className="well well-forest">
          <SparkleIcon size={16} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-body leading-relaxed">{s.text}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-meta text-ink-soft">
              Written by {s.by ?? "AI"}
              {s.at ? ` at ${clock(s.at)}` : ""}
              {since > 0 ? ` · ${since} more moved since` : ""}
            </span>
            <button className="btn btn-sm btn-ghost -my-1" disabled={!!writing} onClick={write} data-tip="The AI writes it again from what moved now">
              {writing ? <Spinner /> : <RefreshIcon size={14} />}
              Write again
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

// ── The suggested plan ────────────────────────────────────────────────

/** "Suggest a plan", for the top of Plan the day. */
export function SuggestButton({ day }: { day: Day }) {
  const { act, busy: asking } = useAct();
  if (!day.ai || day.day !== day.today) return null;
  const suggesting = day.plan?.status === "suggesting" && day.plan.job?.status !== "error";
  return (
    <button
      className="btn btn-sm btn-soft"
      disabled={suggesting || !!asking}
      onClick={() => void act("suggest", () => musterApi.suggestPlan(day.day))}
      data-tip="The AI picks from what's on, in order, around today's meetings"
    >
      {suggesting || asking ? <Spinner /> : <SparkleIcon size={16} />}
      {day.plan ? "Suggest again" : "Suggest a plan"}
    </button>
  );
}

function slotWords(day: string, slot: Slot): { text: string; full?: boolean } {
  if (slot === null) return { text: "—" };
  if (slot === "full") return { text: "Doesn’t fit today", full: true };
  return { text: timeRange(day, slot.start, slot.end) + (slot.across ? ", around a meeting" : "") };
}

function ProposalRow({
  p,
  day,
  slot,
  index,
  count,
  onMove,
}: {
  p: Proposal;
  day: string;
  slot: Slot;
  index: number;
  count: number;
  onMove: (to: number) => void;
}) {
  const { act, busy: acting } = useAct();
  const when = slotWords(day, slot);
  return (
    <li className="px-4 py-2.5 sm:px-5">
      <div className="flex min-w-0 items-start gap-3">
        <span className={`w-[92px] shrink-0 pt-0.5 text-hint tabular-nums ${when.full ? "font-medium text-sun-deep" : "text-ink-soft"}`}>{when.text}</span>
        <div className="min-w-0 flex-1">
          {p.href ? (
            <a href={p.href} className="text-label leading-snug transition-colors hover:text-forest-deep">
              {p.title}
            </a>
          ) : (
            <span className="text-label leading-snug">{p.title}</span>
          )}
          <div className="mt-0.5 text-hint leading-snug text-ink-soft">
            {[p.minutes ? minutesWords(p.minutes) : null, p.reason].filter(Boolean).join(" · ")}
          </div>
        </div>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-1 sm:pl-[104px]">
        <button className="btn btn-sm btn-soft" disabled={!!acting} onClick={() => void act("accept", () => musterApi.acceptProposal(day, p.id))}>
          {acting === "accept" ? <Spinner /> : <CheckIcon size={16} />}
          Accept
        </button>
        <button type="button" className="icon-btn h-8 w-8" disabled={index === 0} aria-label={`Move ${p.title} up`} data-tip="Earlier" onClick={() => onMove(index - 1)}>
          <UpIcon size={16} />
        </button>
        <button type="button" className="icon-btn h-8 w-8" disabled={index === count - 1} aria-label={`Move ${p.title} down`} data-tip="Later" onClick={() => onMove(index + 1)}>
          <DownIcon size={16} />
        </button>
        <button className="btn btn-sm btn-ghost" disabled={!!acting} onClick={() => void act("drop", () => musterApi.patchProposal(day, p.id, { state: "dropped" }))}>
          Drop
        </button>
      </div>
    </li>
  );
}

export function SuggestedPlan({ day, now }: { day: Day; now: Date }) {
  const { act, busy: acting } = useAct();
  const plan = day.plan;
  if (!plan || !day.ai) return null;
  if (plan.status === "suggesting") {
    return (
      <div className="inset-surface mb-3 animate-enter px-4 py-3.5" aria-label="Suggesting a plan">
        {plan.job ? (
          <JobStatus job={plan.job} />
        ) : (
          <span className="flex items-center gap-2 text-ui text-ink-soft">
            <Spinner className="text-sky" /> Planning the day…
          </span>
        )}
      </div>
    );
  }

  const proposed = plan.proposals.filter((p) => p.state === "proposed");
  const dropped = plan.proposals.filter((p) => p.state === "dropped");
  const accepted = plan.proposals.filter((p) => p.state === "accepted");
  const today = day.briefing.sections.today;
  const blocks = freeBlocks(today, day.day, day.hours, day.day === day.today ? now : undefined);
  const planned = inPlan(day.picks).filter((p) => !p.done);
  const slots = fit([...planned.map((p) => p.minutes), ...proposed.map((p) => p.minutes)], blocks).slice(planned.length);
  const meetings = busy(today, day.day).length || plan.meetings;
  const shape = meetings ? `Around ${meetings} ${meetings === 1 ? "meeting" : "meetings"}` : "No meetings to plan around";
  const move = (p: Proposal, to: number) => {
    if (to < 0 || to >= proposed.length) return;
    const rest = proposed.filter((x) => x.id !== p.id);
    void act("move", () => musterApi.moveProposal(day.day, p.id, to === 0 ? null : rest[to - 1].id));
  };

  return (
    <section className="panel mb-3 animate-enter overflow-hidden" aria-label="Suggested plan">
      <div className="px-4 pt-3.5 sm:px-5">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <SparkleIcon size={16} className="text-ink-faint" />
          <span className="text-label font-semibold">Suggested plan</span>
          <span className="text-meta text-ink-soft">
            by {plan.written_by ?? "AI"}
            {plan.made_at ? ` at ${clock(plan.made_at)}` : ""}
          </span>
        </div>
        <p className="mt-1 text-hint leading-snug text-ink-soft">{[shape, plan.note].filter(Boolean).join(". ")}</p>
      </div>
      {proposed.length > 0 ? (
        <ol aria-label="Suggested picks" className="mt-2 divide-y divide-line border-t border-line">
          {proposed.map((p, i) => (
            <ProposalRow key={p.id} p={p} day={day.day} slot={slots[i]} index={i} count={proposed.length} onMove={(to) => move(p, to)} />
          ))}
        </ol>
      ) : (
        <p className="mt-2 border-t border-line px-4 py-3 text-ui text-ink-soft sm:px-5">
          {accepted.length ? "All in your plan." : plan.proposals.length ? "Nothing left to accept." : "Nothing to suggest just now."}
        </p>
      )}
      {dropped.length > 0 && (
        <ul className="border-t border-line px-4 py-2 sm:px-5" aria-label="Dropped">
          {dropped.map((p) => (
            <li key={p.id} className="flex items-center gap-3 py-1">
              <span className="min-w-0 flex-1 truncate text-hint text-ink-soft line-through decoration-ink-faint">{p.title}</span>
              <button className="btn btn-sm btn-ghost shrink-0" disabled={!!acting} onClick={() => void act("back", () => musterApi.patchProposal(day.day, p.id, { state: "proposed" }))}>
                <RefreshIcon size={14} /> Bring back
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap items-center gap-2 border-t border-line px-4 py-3 sm:px-5">
        <span className="mr-auto text-hint text-ink-soft">
          {accepted.length ? `${accepted.length} accepted into today’s plan` : "Nothing changes until you accept."}
        </span>
        <div className="ml-auto flex items-center gap-2">
          <button className="btn btn-sm btn-ghost" disabled={!!acting} onClick={() => void act("discard", () => musterApi.discardPlan(day.day))}>
            {proposed.length ? "Discard" : "Done"}
          </button>
          {proposed.length > 1 && (
            <button
              className="btn btn-sm btn-soft"
              disabled={!!acting}
              onClick={() => void act("all", () => musterApi.acceptAll(day.day), `${proposed.length} picks added to today’s plan.`)}
            >
              {acting === "all" ? <Spinner /> : <CheckIcon size={16} />}
              Accept all
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
