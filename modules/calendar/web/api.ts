import { json, request } from "@core/api";
import type { CalendarEvent, Job } from "@core/api";

/** A calendar Traverse reads (modules/calendar/server/store.py). Its private address never comes back: only its host. */
export interface Source {
  id: string;
  kind: "ical" | "mac";
  name: string;
  enabled: boolean;
  host: string | null;
  read_at: string | null;
  tried_at: string | null;
  error: string | null;
  /** Events kept, from today to a week ahead. */
  events: number;
  job: Job | null;
}

export const calendarApi = {
  sources: () => request<Source[]>("/calendar/sources"),
  add: (body: { kind: "ical" | "mac"; name?: string; url?: string }) => request<Source>("/calendar/sources", json("POST", body)),
  change: (id: string, changes: { name?: string; enabled?: boolean; url?: string }) => request<Source>(`/calendar/sources/${id}`, json("PATCH", changes)),
  remove: (id: string) => request<void>(`/calendar/sources/${id}`, { method: "DELETE" }),
  readNow: (id: string) => request<Source>(`/calendar/sources/${id}/read`, json("POST")),
  /** This Mac's Calendar, as the app's window read it. */
  send: (id: string, events: CalendarEvent[]) => request<{ kept: number }>(`/calendar/sources/${id}/events`, json("PUT", { events })),
};
