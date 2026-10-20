// #/plane/outbox: your changes waiting to go to Plane, and what was sent. Nothing reaches Plane until you press Send,
// and Send reads the item from Plane again first: a field someone changed there meanwhile stops it, showing both
// values, until you choose Plane's or yours. Each field shows what Plane has and what it will have; notes start left
// out (a description is replaced whole). What was sent is listed with each field's before and after, and Undo, which
// is a new push of the values from before, with the same check. ?push=<id> points at one (where a task's link opens);
// ?view=sent shows what was sent.
import { useEffect, useState } from "react";
import { Empty } from "@core/components/blocks";
import { ExternalIcon, icon } from "@core/components/icons";
import { PageHeader, Segmented, Skeleton, Spinner, StatusChip, Switch, useConfirm } from "@core/components/ui";
import type { Tone } from "@core/components/ui";
import { formatDate, relativeTime } from "@core/format";
import { useLive } from "@core/live";
import { useQueryParams } from "@core/router";
import { useShell } from "@core/shell";
import { NavCount } from "@core/Sidebar";
import { Send, Undo2 } from "lucide-react";
import { planeApi } from "./api";
import type { Outbox as OutboxData, Push, PushField, PushFieldView } from "./api";
import { plural } from "./bits";

const SendIcon = icon(Send);
const UndoIcon = icon(Undo2);

const STATUS: Record<Push["status"], { tone: Tone; label: string; live?: boolean }> = {
  waiting: { tone: "sun", label: "Waiting for you" },
  sending: { tone: "sky", label: "Sending", live: true },
  stopped: { tone: "sun", label: "Changed in Plane" },
  failed: { tone: "trail", label: "Didn't go" },
  sent: { tone: "forest", label: "Sent" },
  discarded: { tone: "neutral", label: "Discarded" },
};
const KIND: Record<Push["kind"], string> = { update: "Changes", create: "New in Plane", undo: "Undo" };
const EMPTY: Partial<Record<PushField, string>> = { start_on: "None", due_on: "None", assignee: "No one", notes: "Empty", priority: "None" };

/** A value as the outbox shows it: days formatted, nothing said in words. */
function shown(field: PushField, value: string): string {
  if (!value) return EMPTY[field] ?? "None";
  if (field === "start_on" || field === "due_on") return formatDate(`${value}T12:00:00`, { weekday: "short", month: "short", day: "numeric" });
  return value;
}

export default function Outbox() {
  const { data, error, reload } = useLive(planeApi.outbox);
  const [params, setParams] = useQueryParams();
  const view = params.get("view") === "sent" ? "sent" : "waiting";
  const focus = params.get("push");

  useEffect(() => {
    if (!focus || !data) return;
    if (data.sent.some((p) => p.id === focus) && !data.waiting.some((p) => p.id === focus) && view !== "sent") setParams({ view: "sent" });
    document.getElementById(`push-${focus}`)?.scrollIntoView({ block: "center" });
  }, [focus, !!data, view]); // eslint-disable-line react-hooks/exhaustive-deps

  const header = (
    <PageHeader
      title="Outbox"
      subtitle="Your changes waiting to go to Plane, and what was sent. Nothing goes until you press Send, and Traverse checks Plane again first."
    />
  );
  if (error && !data) {
    return (
      <>
        {header}
        <div className="rounded-lg border border-trail/20 bg-trail-soft/70 p-4 text-label text-trail-deep">{error}</div>
      </>
    );
  }
  if (!data) {
    return (
      <>
        {header}
        <Skeleton className="mb-4 h-10 w-64 rounded-lg" />
        <Skeleton className="h-64 rounded-xl" />
      </>
    );
  }
  const list = view === "sent" ? data.sent : data.waiting;
  return (
    <>
      {header}
      <div className="mb-6 flex animate-enter flex-wrap items-center justify-between gap-3">
        <Segmented
          kind="tab"
          label="Show"
          value={view}
          onChange={(v) => setParams({ view: v === "sent" ? "sent" : null, push: null })}
          options={[
            { id: "waiting", label: data.waiting.length ? `Waiting · ${data.waiting.length}` : "Waiting" },
            { id: "sent", label: "Sent" },
          ]}
        />
      </div>
      {data.dry_run && view === "waiting" && <DryRun />}
      {!list.length ? (
        view === "sent" ? (
          <Empty icon={<SendIcon size={20} />} title="Nothing sent yet">
            Everything Traverse sends to Plane is listed here, with what each field was before and Undo.
          </Empty>
        ) : (
          <Empty icon={<SendIcon size={20} />} title="Nothing waiting to send">
            When you send a linked task's changes to Plane (from its page), they wait here for you to look over and send.
          </Empty>
        )
      ) : (
        <div className="flex flex-col gap-4">
          {list.map((p, n) =>
            view === "sent" ? (
              <Sent key={p.id} push={p} focused={focus === p.id} delay={n} onChanged={() => void reload()} />
            ) : (
              <Waiting key={p.id} push={p} data={data} focused={focus === p.id} delay={n} onChanged={() => void reload()} />
            ),
          )}
        </div>
      )}
    </>
  );
}

function DryRun() {
  return (
    <div role="status" className="mb-6 flex animate-enter flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border border-sky/25 bg-sky-soft/60 px-4 py-3">
      <div className="min-w-0 flex-1 basis-64">
        <div className="text-label font-semibold text-sky-deep">Dry run is on</div>
        <p className="mt-0.5 text-ui text-ink-soft">
          Send checks each change against Plane and says what it would write, but writes nothing. Turn it off in Settings → Plane when you're ready.
        </p>
      </div>
      <a className="btn btn-sm btn-soft" href="#/settings">
        Open Settings
      </a>
    </div>
  );
}

/** The task it's from, and the Plane item it goes to (or the project a new one goes into). */
function Heading({ push: p }: { push: Push }) {
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-0.5">
      <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-meta text-ink-soft">{KIND[p.kind]}</span>
        {p.task ? (
          <a href={p.task.href} className="min-w-0 break-words text-label font-semibold hover:text-forest">
            {p.task.title}
          </a>
        ) : (
          <span className="text-label font-semibold text-ink-soft">A task that's gone from Traverse</span>
        )}
      </div>
      <div className="flex min-w-0 items-center gap-x-1.5 text-meta text-ink-soft">
        {p.item ? (
          <>
            <span className="shrink-0">to</span>
            {p.item.url ? (
              <a href={p.item.url} target="_blank" rel="noreferrer" className="inline-flex min-w-0 items-center gap-1 font-medium text-ink hover:text-forest">
                <span className="truncate">
                  {p.item.key} {p.item.name}
                </span>
                <ExternalIcon size={12} className="shrink-0 text-ink-faint" />
              </a>
            ) : (
              <span className="truncate font-medium text-ink">{p.item.name}</span>
            )}
            {p.item.removed && <span className="shrink-0">· not in what Traverse reads</span>}
          </>
        ) : (
          <span>
            to a new item in <span className="font-medium text-ink">{p.project?.name ?? "its Plane project"}</span>
          </span>
        )}
      </div>
    </div>
  );
}

function useAct(onChanged: () => void) {
  const { toast } = useShell();
  const [busy, setBusy] = useState<string | null>(null);
  const act = async (what: string, work: () => Promise<unknown>, done?: string) => {
    setBusy(what);
    try {
      await work();
      if (done) toast(done, "success");
      onChanged();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(null);
    }
  };
  return { act, busy };
}

function Waiting({ push: p, data, focused, delay, onChanged }: { push: Push; data: OutboxData; focused: boolean; delay: number; onChanged: () => void }) {
  const { act, busy } = useAct(onChanged);
  const [confirm, dialog] = useConfirm();
  const status = STATUS[p.status];
  const sending = p.status === "sending" && p.job?.status !== "error";
  const choosing = p.fields.some((f) => f.theirs !== null && f.include);
  const ready = p.fields.filter((f) => f.include && !f.skip);
  const failed = p.status === "failed" || (p.status === "sending" && p.job?.status === "error");
  const note = p.status === "sending" && p.job?.status === "error" ? p.job.error : p.note;
  const discard = async () => {
    const ok = await confirm({
      title: "Discard this?",
      body: "Nothing is sent, and nothing changes in Plane or in the task: your changes stay on the task, to send later.",
      confirmLabel: "Discard",
    });
    if (ok) void act("discard", () => planeApi.discard(p.id));
  };
  return (
    <section
      id={`push-${p.id}`}
      className={`panel animate-enter overflow-hidden ${focused ? "ring-2 ring-forest/30" : ""}`}
      style={{ animationDelay: `${delay * 60}ms` }}
      aria-label={`${KIND[p.kind]}: ${p.task?.title ?? "a task"}`}
    >
      <div className="flex flex-wrap items-start gap-3 px-5 pt-4">
        <Heading push={p} />
        <StatusChip tone={failed ? "trail" : status.tone} label={failed ? "Didn't go" : sending && p.job?.stage ? p.job.stage : status.label} live={sending} />
      </div>
      {note && <Note push={p} failed={failed} text={note} />}
      <FieldTable push={p} busy={busy} act={act} />
      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-line px-5 py-3">
        <span className="mr-auto text-meta text-ink-soft" data-tip={formatDate(p.created_at)}>
          Asked {relativeTime(p.created_at)}
          {p.checked_at ? ` · checked against Plane ${relativeTime(p.checked_at)}` : ""}
        </span>
        <button className="btn btn-sm btn-ghost" disabled={sending || !!busy} onClick={() => void discard()}>
          Discard
        </button>
        <button
          className="btn btn-sm btn-sun"
          disabled={sending || choosing || !ready.length || !!busy}
          data-tip={choosing ? "Choose Plane's or yours first" : !ready.length ? "Include something to send" : undefined}
          onClick={() => void act("send", () => planeApi.send(p.id))}
        >
          {sending || busy === "send" ? <Spinner /> : <SendIcon size={16} />}
          {data.dry_run ? "Check (dry run)" : failed ? "Try again" : p.kind === "create" ? "Add to Plane" : `Send ${ready.length === 1 ? "it" : plural(ready.length, "change")}`}
        </button>
      </div>
      {dialog}
    </section>
  );
}

function Note({ push: p, failed, text }: { push: Push; failed: boolean; text: string }) {
  const tone = failed
    ? "border-trail/20 bg-trail-soft/70 text-trail-deep"
    : p.status === "stopped"
      ? "border-sun/30 bg-sun-soft/60 text-sun-deep"
      : "border-line bg-surface-subtle text-ink";
  return (
    <p role="status" className={`mx-5 mt-3 rounded-lg border px-3.5 py-2.5 text-ui ${tone}`}>
      {failed && <span className="font-semibold">It didn't reach Plane. </span>}
      {text}
    </p>
  );
}

function FieldTable({ push: p, busy, act }: { push: Push; busy: string | null; act: (what: string, work: () => Promise<unknown>, done?: string) => Promise<void> }) {
  const open = p.status !== "sending";
  const made = p.kind === "create"; // nothing in Plane yet: only what it will have
  const cols = made ? "sm:grid-cols-[2.75rem_6.5rem_minmax(0,1fr)]" : "sm:grid-cols-[2.75rem_6.5rem_minmax(0,1fr)_minmax(0,1fr)]";
  return (
    <div className="mt-3 px-2 pb-1">
      <div className={`hidden gap-x-3 px-3 pb-1.5 text-meta text-ink-soft sm:grid ${cols}`}>
        <span />
        <span />
        {!made && <span>In Plane now</span>}
        <span>{made ? "It will have" : "Will be"}</span>
      </div>
      <ul className="divide-y divide-line">
        {p.fields.map((f) => (
          <li key={f.field} className="px-3 py-2.5">
            {f.theirs !== null ? (
              <Conflict push={p} field={f} busy={busy} act={act} />
            ) : (
              <div className={`grid grid-cols-[2.75rem_minmax(0,1fr)] items-start gap-x-3 gap-y-1 ${cols} ${f.include ? "" : "opacity-70"}`}>
                <span className="pt-0.5">
                  <Switch
                    label={`Send ${f.label.toLowerCase()}`}
                    checked={f.include}
                    disabled={!open || !!f.skip || !!busy}
                    onChange={(on) => void act("include", () => planeApi.include(p.id, { [f.field]: on }))}
                  />
                </span>
                <span className="pt-0.5 text-label font-medium">{f.label}</span>
                {!made && <Value field={f.field} value={f.before} label="In Plane now" muted className="col-start-2 sm:col-start-auto" />}
                <Value field={f.field} value={f.after} label={made ? "It will have" : "Will be"} className="col-start-2 sm:col-start-auto" />
                {(f.skip || f.changed || f.already || (!f.include && f.field === "notes")) && (
                  <p className={`col-start-2 text-meta sm:[grid-column:2/-1] ${f.changed ? "text-sun-deep" : "text-ink-soft"}`}>
                    {f.skip
                      ? `Can't be sent: ${f.skip}.`
                      : f.changed
                        ? "Plane has changed this since you asked to send it. Send will stop and ask which to keep."
                        : f.already
                          ? "Plane has this already, so there's nothing to write for it."
                          : "Left out: a description is replaced whole in Plane. Include it to send yours."}
                  </p>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Value({ field, value, label, muted, className = "" }: { field: PushField; value: string; label: string; muted?: boolean; className?: string }) {
  return (
    <span className={`min-w-0 text-ui ${className}`}>
      <span className="block text-meta text-ink-soft sm:hidden">{label}</span>
      <span className={`block whitespace-pre-line break-words ${field === "notes" ? "line-clamp-4" : ""} ${muted ? "text-ink-soft" : ""}`}>
        {shown(field, value)}
      </span>
    </span>
  );
}

/** A field someone changed in Plane since you last saw it: both values, and your choice. */
function Conflict({ push: p, field: f, busy, act }: { push: Push; field: PushFieldView; busy: string | null; act: (what: string, work: () => Promise<unknown>, done?: string) => Promise<void> }) {
  return (
    <div className="-mx-1 rounded-lg bg-sun-soft/50 px-1 py-1">
      <div className="grid gap-x-4 gap-y-2 sm:grid-cols-[6.5rem_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)] sm:items-start">
        <span className="text-label font-medium text-sun-deep">{f.label}</span>
        <span className="min-w-0 text-ui">
          <span className="block text-meta text-ink-soft">When you last saw it</span>
          <span className="block whitespace-pre-line break-words text-ink-soft">{shown(f.field, f.before)}</span>
        </span>
        <span className="min-w-0 text-ui">
          <span className="block text-meta text-ink-soft">Plane now</span>
          <span className="block whitespace-pre-line break-words">{shown(f.field, f.theirs ?? "")}</span>
        </span>
        <span className="min-w-0 text-ui">
          <span className="block text-meta text-ink-soft">Yours</span>
          <span className="block whitespace-pre-line break-words">{shown(f.field, f.yours ?? "")}</span>
        </span>
      </div>
      <div className="mt-2 flex flex-wrap gap-2 sm:pl-[7.5rem]">
        <button className="btn btn-sm btn-soft" disabled={!!busy} onClick={() => void act("choose", () => planeApi.choose(p.id, f.field, "plane"), `Kept Plane's ${f.label.toLowerCase()}`)}>
          Keep Plane's
        </button>
        <button className="btn btn-sm btn-ghost" disabled={!!busy} onClick={() => void act("choose", () => planeApi.choose(p.id, f.field, "mine"))}>
          Send mine instead
        </button>
        {p.task && (
          <a className="btn btn-sm btn-ghost" href={p.task.href}>
            Edit the task
          </a>
        )}
      </div>
    </div>
  );
}

function Sent({ push: p, focused, delay, onChanged }: { push: Push; focused: boolean; delay: number; onChanged: () => void }) {
  const { act, busy } = useAct(onChanged);
  const sent = p.fields.filter((f) => f.include && !f.skip);
  const undone = p.undone && p.undone.status !== "discarded" ? p.undone : null;
  return (
    <section
      id={`push-${p.id}`}
      className={`panel animate-enter px-5 py-4 ${focused ? "ring-2 ring-forest/30" : ""}`}
      style={{ animationDelay: `${Math.min(delay, 8) * 60}ms` }}
      aria-label={`Sent: ${p.task?.title ?? "a task"}`}
    >
      <div className="flex flex-wrap items-start gap-3">
        <Heading push={p} />
        {undone ? (
          <a href={`#/plane/outbox?push=${undone.id}`} className="shrink-0">
            <StatusChip tone="neutral" label={undone.status === "sent" ? "Undone" : "Being undone"} />
          </a>
        ) : p.kind === "create" ? null : (
          <button className="btn btn-sm btn-ghost -my-1 shrink-0" disabled={!!busy} onClick={() => void act("undo", () => planeApi.undo(p.id), "Undo is waiting for you to send it")}>
            {busy === "undo" ? <Spinner /> : <UndoIcon size={16} />} Undo
          </button>
        )}
      </div>
      <ul className="mt-3 flex flex-col gap-1.5">
        {sent.map((f) => (
          <li key={f.field} className="grid grid-cols-[6.5rem_minmax(0,1fr)] gap-x-3 text-ui">
            <span className="text-label font-medium">{f.label}</span>
            <span className="min-w-0 break-words">
              {p.kind !== "create" && (
                <>
                  <span className="text-ink-soft line-through decoration-ink-faint">{shown(f.field, f.before)}</span>
                  <span className="px-1.5 text-ink-faint" aria-label="became">
                    →
                  </span>
                </>
              )}
              <span className={f.field === "notes" ? "line-clamp-3 whitespace-pre-line" : ""}>{shown(f.field, f.after)}</span>
              {f.over && <span className="ml-2 text-meta text-ink-soft">(sent over a change in Plane, as you chose)</span>}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-meta text-ink-soft">
        <span data-tip={p.sent_at ? formatDate(p.sent_at) : undefined}>Sent {p.sent_at ? relativeTime(p.sent_at) : ""}</span>
        {p.approved_at && <> · approved by you {relativeTime(p.approved_at)}</>}
        {p.note && <> · {p.note}</>}
        {p.kind === "create" && <> · Traverse never deletes in Plane, so a new item can't be undone from here</>}
      </p>
    </section>
  );
}

/** The sidebar's count: pushes waiting for you. */
export function OutboxCount() {
  const { data } = useLive(planeApi.outboxCount);
  return <NavCount n={data?.waiting} />;
}
