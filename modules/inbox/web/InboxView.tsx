import { useRef, useState } from "react";
import type { DragEvent } from "react";
import { Empty } from "@core/components/blocks";
import { DocIcon, InboxIcon, SparkleIcon } from "@core/components/icons";
import { Collapse, PageHeader, Skeleton } from "@core/components/ui";
import { useLive } from "@core/live";
import { navigate } from "@core/router";
import { useShell } from "@core/shell";
import { FILE_KINDS, inboxApi } from "./api";
import type { CaptureListItem } from "./api";
import { CaptureChip, SourceIcon, sourceLine } from "./bits";

const MAX_FILE_BYTES = 2_000_000;

/** Reads a dropped or chosen file and brings it in, or says why it can't. */
async function bringInFile(file: File): Promise<string> {
  const kind = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!FILE_KINDS.includes(kind)) throw new Error("The inbox reads .txt, .md and .eml files.");
  if (file.size > MAX_FILE_BYTES) throw new Error("That file is too big for the inbox. Bring in the part with the work in it.");
  return (await inboxApi.file(file.name, await file.text())).id;
}

function CaptureBox() {
  const { toast } = useShell();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [over, setOver] = useState(false);
  const picker = useRef<HTMLInputElement>(null);

  const go = async (make: () => Promise<string>) => {
    setBusy(true);
    try {
      navigate(`inbox/${await make()}`);
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    const file = e.dataTransfer.files[0];
    if (file) void go(() => bringInFile(file));
    else setText((t) => t + e.dataTransfer.getData("text/plain"));
  };

  return (
    <section
      className={`panel animate-enter p-4 transition-shadow sm:p-5 ${over ? "ring-2 ring-forest/40" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
    >
      <textarea
        aria-label="Paste something to capture"
        className="field min-h-[132px] w-full resize-y px-4 py-3 text-body leading-relaxed"
        placeholder="Paste a Slack thread, an email or your notes…"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && text.trim()) void go(async () => (await inboxApi.paste(text)).id);
        }}
      />
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <button type="button" className="btn btn-sm btn-soft" disabled={busy} onClick={() => picker.current?.click()}>
            <DocIcon size={16} />
            Choose a file
          </button>
          <span className="hidden text-hint text-ink-soft sm:inline">or drop a .txt, .md or .eml here</span>
          <input
            ref={picker}
            type="file"
            accept={FILE_KINDS.join(",")}
            className="hidden"
            aria-hidden="true"
            tabIndex={-1}
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) void go(() => bringInFile(file));
            }}
          />
        </div>
        <button className="btn btn-md btn-primary" disabled={busy || !text.trim()} onClick={() => void go(async () => (await inboxApi.paste(text)).id)}>
          <SparkleIcon size={18} />
          Find the work in it
        </button>
      </div>
      <p className="mt-3 text-hint text-ink-soft">Your AI (Settings → AI) proposes work items. Nothing becomes a task until you accept it.</p>
    </section>
  );
}

function CaptureRow({ c }: { c: CaptureListItem }) {
  return (
    <a href={`#/inbox/${c.id}`} className="flex items-center gap-3 rounded-md px-3 py-3 transition-colors hover:bg-forest/[.04]">
      <span className="well">
        <SourceIcon capture={c} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-label font-medium">{c.title}</div>
        <div className="mt-0.5 truncate text-meta tabular-nums text-ink-soft">{sourceLine(c)}</div>
      </div>
      <span className="shrink-0">
        <CaptureChip capture={c} />
      </span>
    </a>
  );
}

function Group({ title, items, delay }: { title: string; items: CaptureListItem[]; delay: number }) {
  if (!items.length) return null;
  return (
    <section className="mt-10 animate-enter" style={{ animationDelay: `${delay}ms` }}>
      <h2 className="eyebrow mb-2 px-1">{title}</h2>
      <div className="panel divide-y divide-line px-2">
        {items.map((c) => (
          <CaptureRow key={c.id} c={c} />
        ))}
      </div>
    </section>
  );
}

export default function InboxView() {
  const { data: captures } = useLive(inboxApi.list);
  const [showDone, setShowDone] = useState(false);
  const waiting = captures?.filter((c) => c.status === "review") ?? [];
  const reading = captures?.filter((c) => c.status === "new") ?? [];
  const done = captures?.filter((c) => c.status === "done") ?? [];

  return (
    <>
      <PageHeader
        title="Inbox"
        subtitle={captures ? (waiting.length ? `${waiting.length} waiting for you` : "Capture anything; the work in it waits here for you.") : undefined}
      />
      <CaptureBox />
      {!captures && <Skeleton className="mt-10 h-32 w-full rounded-xl" />}
      {captures?.length === 0 && (
        <div className="mt-10 animate-enter">
          <Empty icon={<InboxIcon size={20} />} title="Nothing in the inbox yet">
            Paste a thread or bring in a file, and the work items in it will wait here for you to accept, edit or drop.
          </Empty>
        </div>
      )}
      <Group title="Waiting for you" items={waiting} delay={60} />
      <Group title="Being read" items={reading} delay={120} />
      {done.length > 0 && (
        <section className="mt-10 animate-enter" style={{ animationDelay: "180ms" }}>
          <button className="btn btn-sm btn-ghost -ml-3" onClick={() => setShowDone(!showDone)} aria-expanded={showDone}>
            {showDone ? "Hide" : "Show"} {done.length} done
          </button>
          <Collapse open={showDone}>
            <div className="panel mt-2 divide-y divide-line px-2">
              {done.map((c) => (
                <CaptureRow key={c.id} c={c} />
              ))}
            </div>
          </Collapse>
        </section>
      )}
    </>
  );
}
