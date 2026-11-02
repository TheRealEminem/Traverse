// Settings → Calendar: the calendars Traverse reads for Muster's day and plan. A calendar's private iCal address (read
// by Traverse every few minutes, from any computer), and in the Mac app, this Mac's Calendar (every account the
// Calendar app has; macOS asks once). Traverse never changes a calendar, and never shows an address again once saved.
import { useEffect, useState } from "react";
import type { KeyboardEvent } from "react";
import { macCalendar } from "@core/api";
import type { CalendarAccess } from "@core/api";
import { Section } from "@core/components/blocks";
import { CalendarIcon, CloseIcon, LaptopIcon, PlusIcon, RefreshIcon } from "@core/components/icons";
import { ControlRow, Spinner, Switch, useConfirm } from "@core/components/ui";
import { relativeTime } from "@core/format";
import { useLive } from "@core/live";
import { useShell } from "@core/shell";
import { calendarApi } from "./api";
import type { Source } from "./api";

function useAct() {
  const { toast } = useShell();
  const [busy, setBusy] = useState<string | null>(null);
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
  return { act, busy };
}

const events = (n: number) => `${n} ${n === 1 ? "event" : "events"} this week`;

/** "at 9:04 AM" today, else "2 days ago". */
const moment = (iso: string) =>
  new Date(iso).toDateString() === new Date().toDateString()
    ? `at ${new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`
    : relativeTime(iso);

function SourceRow({ source, access }: { source: Source; access: CalendarAccess | null }) {
  const { app } = useShell();
  const { act, busy } = useAct();
  const [confirm, dialog] = useConfirm();
  const reading = source.job && ["queued", "running"].includes(source.job.status);
  const mac = source.kind === "mac";
  const blocked = mac && macCalendar && access && access !== "full";
  const status = reading
    ? "Reading…"
    : source.error
      ? `Couldn’t read it: ${source.error}`
      : [
          mac ? "Every account in the Calendar app" : source.host,
          source.read_at ? events(source.events) : null,
          source.read_at ? `${mac ? "sent" : "read"} ${moment(source.read_at)}` : mac ? "Sent from the app’s window while it’s open" : null,
        ]
          .filter(Boolean)
          .join(" · ");
  const remove = async () => {
    const ok = await confirm({
      title: `Stop reading ${source.name}?`,
      body: mac ? "Its events leave Traverse. Your calendar itself isn’t changed." : "Its address and events leave Traverse. Your calendar itself isn’t changed.",
      confirmLabel: "Remove",
    });
    if (ok) void act("remove", () => calendarApi.remove(source.id));
  };
  return (
    <ControlRow
      icon={mac ? <LaptopIcon size={16} /> : <CalendarIcon size={16} />}
      label={source.name}
      hint={
        <>
          <span className={source.error ? "text-trail-deep" : ""}>{status}</span>
          {blocked && (
            <span className="mt-1 block text-sun-deep">
              {app.name} can’t read your calendar on this Mac. Allow it in System Settings → Privacy & Security → Calendars.
            </span>
          )}
        </>
      }
      wrap
    >
      <div className="flex items-center gap-1">
        {blocked && (
          <button className="btn btn-sm btn-soft" onClick={() => void macCalendar?.openSettings()}>
            Open System Settings
          </button>
        )}
        {!mac && (
          <button className="btn btn-sm btn-ghost" disabled={!!busy || !!reading || !source.enabled} onClick={() => void act("read", () => calendarApi.readNow(source.id))}>
            {reading ? <Spinner /> : <RefreshIcon size={14} />}
            Read now
          </button>
        )}
        <Switch checked={source.enabled} label={`Read ${source.name}`} onChange={(on) => void act("switch", () => calendarApi.change(source.id, { enabled: on }))} />
        <button type="button" className="icon-btn h-8 w-8" aria-label={`Remove ${source.name}`} data-tip="Remove" disabled={!!busy} onClick={() => void remove()}>
          <CloseIcon size={16} />
        </button>
      </div>
      {dialog}
    </ControlRow>
  );
}

/** A calendar's private iCal address, with a name for it. */
function AddFeed() {
  const { act, busy } = useAct();
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const add = async () => {
    if (await act("add", () => calendarApi.add({ kind: "ical", name: name.trim() || undefined, url: url.trim() }), "Added. Reading it now.")) {
      setName("");
      setUrl("");
    }
  };
  const keys = (e: KeyboardEvent) => e.key === "Enter" && url.trim() && void add();
  return (
    <ControlRow
      icon={<PlusIcon size={16} />}
      label="Add a calendar by its private address"
      hint="Google Calendar: Settings → your calendar → Integrate calendar → Secret address in iCal format. Outlook: Settings → Calendar → Shared calendars → Publish a calendar (ICS). Anyone with the address can read the calendar, so it’s never shown again."
      wrap
    >
      <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:flex-nowrap">
        <input aria-label="Calendar name" className="field h-9 w-full sm:w-36" placeholder="Name (Work)" value={name} onChange={(e) => setName(e.target.value)} onKeyDown={keys} />
        <input
          type="password"
          aria-label="Private iCal address"
          autoComplete="off"
          className="field h-9 min-w-0 flex-1 font-mono text-hint sm:w-60 sm:flex-none"
          placeholder="https://… or webcal://…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={keys}
        />
        <button className="btn btn-sm btn-soft" disabled={!url.trim() || !!busy} onClick={() => void add()}>
          {busy ? <Spinner /> : null}
          Add
        </button>
      </div>
    </ControlRow>
  );
}

/** In the Mac app: this Mac's Calendar, which macOS asks about the first time. */
function AddMac({ access, onAccess }: { access: CalendarAccess | null; onAccess: (a: CalendarAccess) => void }) {
  const { app } = useShell();
  const { act, busy } = useAct();
  const add = () =>
    void act("mac", async () => {
      const now = await macCalendar!.request();
      onAccess(now);
      if (now !== "full") throw new Error(`${app.name} can’t read your calendar. Allow it in System Settings → Privacy & Security → Calendars, then add it again.`);
      await calendarApi.add({ kind: "mac" });
    }, "Added. Your Mac’s Calendar shows in Muster now.");
  return (
    <ControlRow
      icon={<LaptopIcon size={16} />}
      label="This Mac’s Calendar"
      hint={
        access === "unavailable"
          ? `This copy of ${app.name} doesn’t read the calendar.`
          : "Every account the Calendar app has: iCloud, Google, Exchange. macOS asks you once; the app’s window sends the events while it’s open."
      }
      wrap
    >
      {access && access !== "full" && access !== "unasked" && access !== "unavailable" ? (
        <button className="btn btn-sm btn-soft" onClick={() => void macCalendar?.openSettings()}>
          Open System Settings
        </button>
      ) : (
        <button className="btn btn-sm btn-soft" disabled={!!busy || access === "unavailable"} onClick={add}>
          {busy ? <Spinner /> : <PlusIcon size={16} />}
          Add
        </button>
      )}
    </ControlRow>
  );
}

export function CalendarSettings() {
  const { app } = useShell();
  const { data: sources } = useLive(calendarApi.sources);
  const [access, setAccess] = useState<CalendarAccess | null>(null);
  useEffect(() => {
    void macCalendar?.access().then(setAccess, () => undefined);
  }, []);
  const hasMac = sources?.some((s) => s.kind === "mac");
  return (
    <Section icon={<CalendarIcon size={16} />} title="Calendar" blurb={`Your meetings, for Muster’s day and the plan around them. ${app.name} only reads them.`}>
      {sources?.map((s) => <SourceRow key={s.id} source={s} access={access} />)}
      <AddFeed />
      {!hasMac &&
        (macCalendar ? (
          <AddMac access={access} onAccess={setAccess} />
        ) : (
          <ControlRow
            icon={<LaptopIcon size={16} />}
            label="This Mac’s Calendar"
            hint={`In the ${app.name} app on your Mac, you can add your Mac’s Calendar too: every account the Calendar app has.`}
          />
        ))}
    </Section>
  );
}
