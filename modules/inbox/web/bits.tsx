// Small pieces the inbox's screens share: where a capture came from, priorities, and the quiet dates on rows.
import { Mountain } from "lucide-react";
import { ChatIcon, DocIcon, MailIcon, SparkleIcon, WaveIcon, icon } from "@core/components/icons";
import { JobChip } from "@core/components/blocks";
import { StatusChip } from "@core/components/ui";
import type { CaptureListItem, Source } from "./api";

export const ProjectIcon = icon(Mountain);

/** Plane's five levels, as tasks keeps them. */
export const PRIORITIES = ["No priority", "Low", "Medium", "High", "Urgent"];

const SOURCE_LABEL: Record<Source, string> = { paste: "Pasted", file: "File", claude: "From Claude", trailmix: "Meeting" };

export function SourceIcon({ capture, size = 16 }: { capture: Pick<CaptureListItem, "source" | "origin_title">; size?: number }) {
  if (capture.source === "trailmix") return <WaveIcon size={size} />;
  if (capture.source === "claude") return <SparkleIcon size={size} />;
  if (capture.source === "file") return capture.origin_title?.toLowerCase().endsWith(".eml") ? <MailIcon size={size} /> : <DocIcon size={size} />;
  return <ChatIcon size={size} />;
}

/** "Meeting · Weekly sync · Oct 18" or "Pasted · 2:14 PM". */
export function sourceLine(c: Pick<CaptureListItem, "source" | "origin_title" | "origin_at" | "created_at">): string {
  const parts = [SOURCE_LABEL[c.source]];
  if (c.source === "file" && c.origin_title) parts.push(c.origin_title);
  parts.push(when(c.source === "trailmix" && c.origin_at ? c.origin_at : c.created_at));
  return parts.join(" · ");
}

/** A time today, otherwise the day. */
export function when(iso: string): string {
  const d = iso.length === 10 ? new Date(`${iso}T12:00:00`) : new Date(iso);
  return new Date().toDateString() === d.toDateString()
    ? d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
    : d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** "Fri, Oct 23" for a due day. */
export function dueLabel(day: string): string {
  return new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

/** Where a capture stands, for list rows: being read, waiting for you, or done. */
export function CaptureChip({ capture }: { capture: CaptureListItem }) {
  if (capture.status === "new") return capture.job ? <JobChip job={capture.job} /> : <StatusChip tone="sky" label="Reading" live />;
  if (capture.status === "review") return <StatusChip tone="sun" label={`${capture.waiting} to review`} />;
  return capture.accepted ? <StatusChip tone="forest" label={`${capture.accepted} filed`} /> : <StatusChip tone="neutral" label="Done" />;
}
