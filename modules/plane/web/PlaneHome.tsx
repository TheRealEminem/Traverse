// Home's card: what waits to go to Plane (the Outbox's waiting pushes, stopped ones first), what went today (and how
// much of it auto-send sent), and whether dry run is on.
import { icon } from "@core/components/icons";
import { StatusChip } from "@core/components/ui";
import type { Tone } from "@core/components/ui";
import { useLive } from "@core/live";
import { Send } from "lucide-react";
import { planeApi } from "./api";
import type { Push } from "./api";
import { plural } from "./bits";

const SendIcon = icon(Send);
const SHOWN = 4;
const ORDER: Push["status"][] = ["stopped", "failed", "sending", "waiting"];
const CHIP: Partial<Record<Push["status"], { tone: Tone; label: string; live?: boolean }>> = {
  stopped: { tone: "sun", label: "Changed in Plane" },
  failed: { tone: "trail", label: "Didn't go" },
  sending: { tone: "sky", label: "Sending", live: true },
  waiting: { tone: "sun", label: "Waiting" },
};

/** What a push asks for, in a few words: "Due and priority", "New in Software", "Comment on SOFTWARE-5". */
function asks(p: Push): string {
  if (p.kind === "create") return `New in ${p.project?.name ?? "Plane"}`;
  if (p.kind === "comment") return `Comment on ${p.item?.key ?? "an item"}`;
  const labels = p.fields.filter((f) => f.include && !f.skip).map((f) => f.label.toLowerCase());
  const words = labels.length > 1 ? `${labels.slice(0, -1).join(", ")} and ${labels[labels.length - 1]}` : labels[0] ?? "nothing chosen";
  return `${p.kind === "undo" ? "Undo: " : ""}${words.charAt(0).toUpperCase()}${words.slice(1)}${p.item ? ` · ${p.item.key}` : ""}`;
}

const startOfToday = () => new Date(new Date().setHours(0, 0, 0, 0)).toISOString();

export default function PlaneHome() {
  const { data: box } = useLive(() => planeApi.outbox(startOfToday()));
  const waiting = [...(box?.waiting ?? [])].sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status));
  const stopped = waiting.filter((p) => p.status === "stopped").length;
  const sentToday = box?.sent_since?.sent ?? 0;
  const byAuto = box?.sent_since?.auto ?? 0;
  const summary = !box
    ? "…"
    : !box.configured
      ? "Plane isn't connected yet"
      : waiting.length
        ? `${waiting.length} waiting for you${stopped ? `, ${stopped} changed in Plane too` : ""}`
        : "Nothing waiting";
  const notes = [
    sentToday ? `${plural(sentToday, "change")} sent today${byAuto ? `, ${byAuto} by auto-send` : ""}.` : "",
    box?.dry_run ? "Dry run is on: Send only checks." : "",
  ].filter(Boolean);
  return (
    <>
      <div className="flex items-center gap-3">
        <span className={`well ${stopped ? "bg-sun-soft text-sun-deep" : "well-forest"}`}>
          <SendIcon size={16} />
        </span>
        <div className="min-w-0">
          <h2 className="text-heading font-semibold tracking-[-0.01em]">Waiting to send</h2>
          <p className="text-hint text-ink-soft">{summary}</p>
        </div>
      </div>
      <div className="mt-3 space-y-px">
        {waiting.slice(0, SHOWN).map((p) => {
          const chip = CHIP[p.status] ?? CHIP.waiting!;
          return (
            <a
              key={p.id}
              href={`#/plane/outbox?push=${p.id}`}
              className="-mx-2 flex items-center justify-between gap-3 rounded-md px-2 py-2 transition-colors hover:bg-forest/[.05]"
            >
              <span className="min-w-0">
                <span className="block truncate text-ui font-medium">{p.task?.title ?? "A task that's gone from Traverse"}</span>
                <span className="block truncate text-meta text-ink-soft">{asks(p)}</span>
              </span>
              <span className="shrink-0">
                <StatusChip tone={chip.tone} label={chip.label} live={chip.live} />
              </span>
            </a>
          );
        })}
        {waiting.length > SHOWN && <p className="py-1 text-meta text-ink-soft">And {waiting.length - SHOWN} more.</p>}
        {box?.configured && !waiting.length && (
          <p className="py-2 text-ui text-ink-soft">When you send a task's changes to Plane, they wait here for your Send.</p>
        )}
        {box && !box.configured && <p className="py-2 text-ui text-ink-soft">Add your Plane key in Settings to see the team's work and send yours.</p>}
      </div>
      {notes.length > 0 && <p className="mt-2 text-meta text-ink-soft">{notes.join(" ")}</p>}
      <a href={box && !box.configured ? "#/settings?section=plane" : "#/plane/outbox"} className="btn btn-sm btn-ghost -ml-3 mt-2">
        {box && !box.configured ? "Open Settings" : waiting.length ? "Review and send" : "Open the Outbox"}
      </a>
    </>
  );
}
