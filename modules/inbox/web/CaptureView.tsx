// The review screen: one capture, the work items the AI proposed from it, and where accepted ones are filed.
import { useEffect, useState } from "react";
import type { KeyboardEvent } from "react";
import { Empty, JobStatus, LinkedList } from "@core/components/blocks";
import {
  BackIcon,
  CalendarIcon,
  CheckIcon,
  ExternalIcon,
  FlagIcon,
  PencilIcon,
  PersonIcon,
  RefreshIcon,
  SparkleIcon,
  TrashIcon,
} from "@core/components/icons";
import { Collapse, ControlRow, Select, Skeleton } from "@core/components/ui";
import { useLive } from "@core/live";
import type { RouteProps } from "@core/registry";
import { navigate } from "@core/router";
import { useShell } from "@core/shell";
import { inboxApi } from "./api";
import type { Capture, Proposal, ProposalChanges } from "./api";
import { PRIORITIES, ProjectIcon, SourceIcon, dueLabel, sourceLine, when } from "./bits";
import ProjectPicker from "./ProjectPicker";

function Facts({ p }: { p: Pick<Proposal, "assignee_name" | "due_on" | "priority"> }) {
  if (!p.assignee_name && !p.due_on && !p.priority) return <span className="text-meta text-ink-soft">No one or day named</span>;
  return (
    <>
      {p.assignee_name && (
        <span className="chip bg-surface-subtle text-ink-soft">
          <PersonIcon size={12} />
          {p.assignee_name}
        </span>
      )}
      {p.due_on && (
        <span className="chip bg-surface-subtle tabular-nums text-ink-soft">
          <CalendarIcon size={12} />
          {dueLabel(p.due_on)}
        </span>
      )}
      {p.priority > 0 && (
        <span className={`chip ${p.priority >= 3 ? "bg-sun-soft text-sun-deep" : "bg-surface-subtle text-ink-soft"}`}>
          <FlagIcon size={12} />
          {PRIORITIES[p.priority]}
        </span>
      )}
    </>
  );
}

function EditProposal({ p, onSave, onCancel }: { p: Proposal; onSave: (c: ProposalChanges) => Promise<boolean>; onCancel: () => void }) {
  const [text, setText] = useState(p.text);
  const [who, setWho] = useState(p.assignee_name ?? "");
  const [due, setDue] = useState(p.due_on ?? "");
  const [priority, setPriority] = useState(String(p.priority));
  const save = () => void onSave({ text, assignee_name: who, due_on: due || null, priority: Number(priority) });
  const keys = (e: KeyboardEvent) => {
    if (e.key === "Escape") onCancel();
    if (e.key === "Enter" && text.trim()) save();
  };
  return (
    <div className="animate-fade-in py-4">
      <input autoFocus aria-label="Work item" className="field w-full text-label" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={keys} />
      <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
        <label className="block">
          <span className="eyebrow mb-1 block">Who</span>
          <input className="field w-full" placeholder="Nobody yet" value={who} onChange={(e) => setWho(e.target.value)} onKeyDown={keys} />
        </label>
        <label className="block">
          <span className="eyebrow mb-1 block">Due</span>
          <input type="date" className="field w-full tabular-nums" value={due} onChange={(e) => setDue(e.target.value)} onKeyDown={keys} />
        </label>
        <div>
          <span className="eyebrow mb-1 block">Priority</span>
          <Select label="Priority" className="w-full" value={priority} onChange={setPriority} options={PRIORITIES.map((label, i) => ({ value: String(i), label }))} />
        </div>
      </div>
      <div className="mt-3 flex justify-end gap-2">
        <button className="btn btn-sm btn-ghost" onClick={onCancel}>
          Cancel
        </button>
        <button className="btn btn-sm btn-soft" disabled={!text.trim()} onClick={save}>
          Save
        </button>
      </div>
    </div>
  );
}

type Act = (fn: () => Promise<unknown>, done?: string) => Promise<boolean>;

function ProposalRow({ p, from, act }: { p: Proposal; from: string | null; act: Act }) {
  const [editing, setEditing] = useState(false);
  if (editing) {
    return (
      <EditProposal
        p={p}
        onCancel={() => setEditing(false)}
        onSave={(changes) => act(() => inboxApi.edit(p.id, changes)).then((ok) => {
          if (ok) setEditing(false);
          return ok;
        })}
      />
    );
  }
  return (
    <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start">
      <div className="min-w-0 flex-1">
        <p className="text-label font-medium leading-snug">{p.text}</p>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          <Facts p={p} />
        </div>
        {p.quote && (
          <p className="mt-2.5 border-l-2 border-line-strong pl-3 text-hint leading-relaxed text-ink-soft">
            “{p.quote}”{from && <span className="whitespace-nowrap"> · {from}</span>}
          </p>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-1 sm:pt-0.5">
        <button className="btn btn-sm btn-soft" onClick={() => void act(() => inboxApi.accept(p.id), "Accepted.")}>
          <CheckIcon size={16} />
          Accept
        </button>
        <button className="icon-btn" aria-label="Edit" data-tip="Edit" onClick={() => setEditing(true)}>
          <PencilIcon size={16} />
        </button>
        <button className="btn btn-sm btn-danger-ghost" onClick={() => void act(() => inboxApi.drop(p.id))}>
          Drop
        </button>
      </div>
    </div>
  );
}

function DecidedRow({ p, act }: { p: Proposal; act: Act }) {
  const accepted = p.status === "accepted";
  return (
    <div className="flex items-center gap-3 py-3">
      <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full ${accepted ? "bg-forest-soft text-forest-deep" : "bg-surface-subtle text-ink-faint"}`}>
        {accepted ? <CheckIcon size={12} strokeWidth={2.6} /> : <span className="h-px w-2 bg-current" />}
      </span>
      <div className="min-w-0 flex-1">
        <div className={`truncate text-label ${accepted ? "" : "text-ink-soft line-through decoration-ink-faint"}`}>{p.text}</div>
        {accepted && (p.assignee_name || p.due_on) && (
          <div className="mt-0.5 truncate text-meta tabular-nums text-ink-soft">
            {[p.assignee_name, p.due_on && dueLabel(p.due_on)].filter(Boolean).join(" · ")}
          </div>
        )}
      </div>
      {accepted ? (
        <span className="shrink-0 text-meta text-ink-soft">Filed</span>
      ) : (
        <button className="btn btn-sm btn-ghost shrink-0" onClick={() => void act(() => inboxApi.restore(p.id))}>
          Bring back
        </button>
      )}
    </div>
  );
}

function TitleField({ capture }: { capture: Capture }) {
  const { toast } = useShell();
  const [value, setValue] = useState(capture.title);
  useEffect(() => setValue(capture.title), [capture.title]);
  const save = () => {
    const next = value.trim();
    if (!next || next === capture.title) return setValue(capture.title);
    inboxApi.rename(capture.id, next).catch((e: Error) => toast(e.message, "error"));
  };
  return (
    <input
      aria-label="Title"
      className="page-title w-full bg-transparent outline-none"
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={save}
      onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
    />
  );
}

export default function CaptureView({ params }: RouteProps) {
  const { confirm, toast } = useShell();
  const { data: c, error, reload } = useLive(() => inboxApi.get(params.id), [params.id]);
  const [showText, setShowText] = useState(false);

  if (error) {
    return (
      <p className="text-label text-ink-soft">
        {error} <a className="text-forest underline decoration-forest/30 underline-offset-2" href="#/inbox">Back to the inbox</a>
      </p>
    );
  }
  if (!c) {
    return (
      <div className="space-y-4 pt-2">
        <Skeleton className="h-3.5 w-40" />
        <Skeleton className="h-9 w-2/3" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    );
  }

  const act: Act = async (fn, done) => {
    try {
      await fn();
      if (done) toast(done);
      await reload();
      return true;
    } catch (e) {
      toast((e as Error).message, "error");
      return false;
    }
  };
  const waiting = c.proposals.filter((p) => p.status === "proposed");
  const decided = c.proposals.filter((p) => p.status !== "proposed");
  const reading = c.job && c.job.status !== "done";
  const from = c.source === "trailmix" ? `${c.origin_title ?? c.title}, ${when(c.origin_at ?? c.created_at)}` : null;
  const where = c.project ? `into ${c.project.title}` : "into Tasks, in no project";

  const remove = async () => {
    if (!(await confirm({ title: "Delete this capture?", body: "Its proposals go with it. Tasks you accepted from it stay.", confirmLabel: "Delete", tone: "danger" }))) return;
    await inboxApi.remove(c.id);
    toast("Capture deleted.");
    navigate("inbox");
  };

  return (
    <article className="animate-enter">
      <div className="mb-3 flex items-center justify-between gap-3">
        <a href="#/inbox" className="btn btn-sm btn-ghost -ml-3">
          <BackIcon size={16} />
          Inbox
        </a>
        <button className="icon-btn hover:!bg-trail-soft hover:!text-trail-deep" aria-label="Delete capture" data-tip="Delete" onClick={() => void remove()}>
          <TrashIcon size={18} />
        </button>
      </div>

      <TitleField capture={c} />
      <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-ui text-ink-soft">
        <span className="text-ink-faint">
          <SourceIcon capture={c} />
        </span>
        <span className="tabular-nums">{sourceLine(c)}</span>
        {c.origin_url && (
          <a href={c.origin_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-forest hover:underline">
            Open in Trailmix
            <ExternalIcon size={14} />
          </a>
        )}
      </p>

      <section className="panel mt-6 px-5 sm:px-6">
        <ControlRow
          wrap
          icon={<ProjectIcon size={16} />}
          label="Files into"
          hint={c.project ? "What you accept goes into this project." : "What you accept waits in Tasks, in no project, until you choose one."}
        >
          <ProjectPicker value={c.project} onChange={(p) => void act(() => inboxApi.setProject(c.id, p?.ref ?? null), p ? `Filing into ${p.title}.` : undefined)} />
        </ControlRow>
      </section>

      {reading && (
        <div className="mt-6">
          <JobStatus job={c.job} />
        </div>
      )}

      {!reading && c.status !== "new" && (
        <section className="mt-10 animate-enter">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-3 px-1">
            <div className="min-w-0">
              <h2 className="text-heading font-semibold tracking-[-0.01em]">
                {waiting.length ? `${waiting.length} proposed` : decided.length ? "All decided" : "Nothing proposed"}
              </h2>
              {c.read_by && (
                <p className="mt-0.5 flex items-center gap-1.5 text-hint text-ink-soft">
                  <SparkleIcon size={14} className="text-ink-faint" />
                  Proposed by {c.read_by}
                  {c.read_at && <span className="tabular-nums">· {when(c.read_at)}</span>}
                </p>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <button className="btn btn-sm btn-ghost" onClick={() => void act(() => inboxApi.readAgain(c.id))} data-tip="Proposals still waiting are replaced; what you decided stays">
                <RefreshIcon size={16} />
                Read again
              </button>
              {waiting.length > 1 && (
                <button className="btn btn-sm btn-primary" onClick={() => void act(() => inboxApi.acceptAll(c.id), `${waiting.length} filed ${where}.`)}>
                  <CheckIcon size={16} />
                  Accept all
                </button>
              )}
            </div>
          </div>
          {waiting.length > 0 && (
            <div className="panel divide-y divide-line px-5 sm:px-6">
              {waiting.map((p) => (
                <ProposalRow key={p.id} p={p} from={from} act={act} />
              ))}
            </div>
          )}
          {!c.proposals.length && (
            <Empty icon={<SparkleIcon size={20} />} title="No work items in this one">
              Nothing in it reads as something someone has to do. Read it again, or delete it.
            </Empty>
          )}
          {decided.length > 0 && (
            <>
              <h3 className="eyebrow mb-2 mt-8 px-1">Decided</h3>
              <div className="panel divide-y divide-line px-5 sm:px-6">
                {decided.map((p) => (
                  <DecidedRow key={p.id} p={p} act={act} />
                ))}
              </div>
            </>
          )}
        </section>
      )}

      <section className="mt-10">
        <button className="btn btn-sm btn-ghost -ml-3" onClick={() => setShowText(!showText)} aria-expanded={showText}>
          {showText ? "Hide" : "Show"} what was captured
        </button>
        <Collapse open={showText}>
          <div className="inset-surface mt-2 max-h-[420px] overflow-y-auto whitespace-pre-wrap break-words px-4 py-3 text-ui leading-relaxed text-ink-soft">{c.raw_text}</div>
        </Collapse>
      </section>

      <LinkedList of={`inbox:${c.id}`} />
    </article>
  );
}
