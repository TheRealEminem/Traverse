// The inbox's Home card, its sidebar count, and its section on the Settings page.
import { useState } from "react";
import { Section } from "@core/components/blocks";
import { InboxIcon, RefreshIcon, WaveIcon } from "@core/components/icons";
import { ControlRow, SwitchRow } from "@core/components/ui";
import { useLive } from "@core/live";
import { NavCount } from "@core/Sidebar";
import { useSettings, useShell } from "@core/shell";
import { inboxApi } from "./api";
import { CaptureChip, when } from "./bits";

export function WaitingCount() {
  const { data } = useLive(inboxApi.count);
  return <NavCount n={data?.waiting} />;
}

export function InboxHome() {
  const { data: captures } = useLive(inboxApi.list);
  const waiting = captures?.filter((c) => c.status === "review") ?? [];
  const shown = (waiting.length ? waiting : captures ?? []).slice(0, 3);
  return (
    <>
      <div className="flex items-center gap-3">
        <span className="well well-forest">
          <InboxIcon size={16} />
        </span>
        <div className="min-w-0">
          <h2 className="text-heading font-semibold tracking-[-0.01em]">Inbox</h2>
          <p className="text-hint text-ink-soft">{captures ? (waiting.length ? `${waiting.length} waiting for you` : "Nothing waiting") : "…"}</p>
        </div>
      </div>
      <div className="mt-3 space-y-px">
        {shown.map((c) => (
          <a key={c.id} href={`#/inbox/${c.id}`} className="-mx-2 flex items-center justify-between gap-3 rounded-md px-2 py-2 text-ui transition-colors hover:bg-forest/[.05]">
            <span className="truncate font-medium">{c.title}</span>
            <span className="shrink-0">
              <CaptureChip capture={c} />
            </span>
          </a>
        ))}
        {captures?.length === 0 && <p className="py-2 text-ui text-ink-soft">Paste a thread or an email, and the work in it waits here for you.</p>}
      </div>
      <a href="#/inbox" className="btn btn-sm btn-ghost -ml-3 mt-2">
        {captures?.length ? "Open the inbox" : "Capture something"}
      </a>
    </>
  );
}

/** "just now", "4 min ago", then the time or day. */
function ago(iso: string): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  return minutes < 1 ? "just now" : minutes < 60 ? `${minutes} min ago` : when(iso);
}

function TrailmixState() {
  const { toast } = useShell();
  const { data } = useLive(inboxApi.trailmix);
  const [busy, setBusy] = useState(false);
  if (!data) return null;
  const last = data.last;
  const running = data.job && (data.job.status === "queued" || data.job.status === "running");
  const label = running ? "Checking Trailmix…" : !last ? "Not checked yet" : last.error ? "Trailmix wants a sign-in" : last.reachable ? "Trailmix is open" : "Trailmix isn’t running";
  const brought = `${data.brought_in} ${data.brought_in === 1 ? "meeting" : "meetings"} brought in so far`;
  const hint = !last
    ? `It looks every few minutes at ${data.url}.`
    : last.error ?? (last.reachable ? `Checked ${ago(last.at)} · ${brought}` : `Nothing comes in while it’s closed. Checked ${ago(last.at)}.`);
  const check = async () => {
    setBusy(true);
    try {
      await inboxApi.checkTrailmix();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  };
  return (
    <ControlRow
      wrap
      icon={<StatusDot tone={running ? "sky" : last?.reachable && !last.error ? "forest" : "neutral"} />}
      label={label}
      hint={hint}
    >
      <button className="btn btn-sm btn-soft" disabled={busy || !!running} onClick={() => void check()}>
        <RefreshIcon size={16} />
        Check now
      </button>
    </ControlRow>
  );
}

function StatusDot({ tone }: { tone: "forest" | "sky" | "neutral" }) {
  const bg = { forest: "bg-forest", sky: "bg-sky animate-soft-pulse", neutral: "bg-ink-faint" }[tone];
  return <span aria-hidden="true" className={`h-2 w-2 rounded-full ${bg}`} />;
}

export function InboxSettings() {
  const { get, save } = useSettings();
  const on = !!get<boolean>("inbox.trailmix");
  return (
    <Section icon={<InboxIcon size={16} />} title="Inbox" blurb="Where captures come from.">
      <SwitchRow
        icon={<WaveIcon size={16} />}
        label="Meetings from Trailmix"
        hint="Brings in the open action items of meetings Trailmix has summarized in the last two weeks, for your AI to read and you to review. Off: nothing is read from Trailmix."
        checked={on}
        onChange={(v) => void save({ "inbox.trailmix": v })}
      />
      {on && <TrailmixState />}
    </Section>
  );
}
