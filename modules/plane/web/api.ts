import { json, request } from "@core/api";
import type { Job } from "@core/api";

export type Group = "triage" | "backlog" | "unstarted" | "started";
export type Split = Record<Group, number>;

export interface TeamPerson {
  id: string | null; // Plane member id; null is "No one"
  ref: string | null; // "core:me" for you, "plane:<id>" for teammates
  name: string;
  display_name: string;
  is_me: boolean;
  open: number;
  by_group: Split;
  past_due: number;
  due_soon: number;
  projects: Record<string, number>;
}

export interface TeamProject {
  id: string;
  identifier: string;
  name: string;
  open: number;
  by_group: Split;
  past_due: number;
  unassigned: number;
  people: Record<string, number>; // member id (or "none") -> open items
  linked: InTraverse | null; // the Traverse project it goes to
}

/** Something in Traverse, as its module names it. */
export interface InTraverse {
  ref: string;
  title: string;
  href: string;
}

export interface TeamItem {
  id: string;
  ref: string;
  key: string; // "SOFTWARE-5"
  name: string;
  project_id: string;
  project: string;
  state: { id: string | null; name: string; group: Group };
  priority: "none" | "low" | "medium" | "high" | "urgent";
  target_date: string | null;
  past_due: boolean;
  due_soon: boolean;
  assignees: { id: string; name: string; is_me: boolean }[];
  labels: string[];
  cycle: string | null;
  updated_at: string | null;
  url: string;
  task: InTraverse | null; // its linked copy in Traverse, once brought in
}

export interface Team {
  configured: boolean;
  workspace: string;
  web_url: string;
  today: string;
  projects_chosen: number;
  pulled_at: string | null;
  totals: { open: number; past_due: number; unassigned: number; due_soon: number; in_progress: number };
  states: { group: Group; label: string; open: number }[];
  people: TeamPerson[];
  projects: TeamProject[];
  items: TeamItem[];
  job: Job | null;
}

export interface PlaneStatus {
  configured: boolean;
  workspace: string;
  web_url: string;
  me: { id: string; name: string } | null;
  me_from_key: boolean;
  last_pull: { at: string; changed: number; requests: number; projects: number } | null;
  job: Job | null;
  counts: Record<"projects" | "members" | "states" | "labels" | "cycles" | "items", number>;
}

export interface PlaneProject {
  id: string;
  identifier: string;
  name: string;
  description: string;
  mirrored: boolean;
}

export interface PlaneMember {
  id: string;
  name: string;
  display_name: string;
  email: string | null;
}

export type Status = "todo" | "doing" | "waiting" | "done" | "dropped";

export interface PlaneState {
  id: string;
  name: string;
  group: "triage" | "backlog" | "unstarted" | "started" | "completed" | "cancelled";
  color: string | null;
}

export interface LinkedProject {
  id: string;
  identifier: string;
  name: string;
  link: { local_ref: string; title: string | null; href: string | null; created_at: string; state_map: Record<Status, string | null> } | null;
  preset: Record<Status, string | null>;
  states: PlaneState[];
  open: number;
  mine: number;
  in_traverse: number;
  open_waiting: string[]; // open items not in Traverse yet
  mine_waiting: string[]; // of those, yours
}

export interface Links {
  projects: LinkedProject[];
  statuses: { value: Status; label: string; group: string }[];
  mine: number;
  mine_waiting: string[];
}

export interface Brought {
  brought: number;
  already: number;
  new_projects: string[];
  missing: number;
}

/** Traverse's fields, as a push names them. */
export type PushField = "text" | "notes" | "status" | "priority" | "start_on" | "due_on" | "assignee";

export interface PushFieldView {
  field: PushField;
  label: string;
  include: boolean; // sent only when on (notes start off)
  skip: string | null; // why it can't be sent at all
  before: string; // waiting: Plane now (as of the last read); sent: Plane just before writing ("" for nothing)
  after: string; // what Plane will have (or had once sent)
  changed: boolean; // a read of Plane saw it change since you asked: Send will stop and ask
  already: boolean; // Plane has this value already (as of the last read): nothing to write for it
  theirs: string | null; // stopped: Plane's value now…
  yours: string | null; // …and yours (before is then what you last saw)
  over: boolean; // you chose to send yours over a change made in Plane
}

export type PushStatus = "waiting" | "sending" | "stopped" | "failed" | "sent" | "discarded";

export interface Push {
  id: string;
  kind: "update" | "create" | "undo";
  status: PushStatus;
  note: string | null;
  created_at: string;
  approved_at: string | null;
  sent_at: string | null;
  checked_at: string | null;
  undo_of: string | null;
  undone: { id: string; status: PushStatus; sent_at: string | null } | null;
  task: { title: string; href: string } | null;
  item: { id: string; key: string; name: string; url: string | null; removed: boolean } | null;
  project: { id: string; name: string } | null;
  fields: PushFieldView[];
  job: Job | null;
}

export interface Outbox {
  dry_run: boolean;
  configured: boolean;
  waiting: Push[];
  sent: Push[];
}

export const planeApi = {
  team: () => request<Team>("/plane/team"),
  status: () => request<PlaneStatus>("/plane/status"),
  projects: () => request<PlaneProject[]>("/plane/projects"),
  members: () => request<PlaneMember[]>("/plane/members"),
  pull: () => request<{ job: string }>("/plane/pull", json("POST")),
  test: () => request<{ message: string; projects: number }>("/plane/test", json("POST")),
  links: () => request<Links>("/plane/links"),
  /** Links a Plane project to a Traverse project (its ref), or to a new one named after it. */
  link: (projectId: string, localRef?: string) => request<LinkedProject>(`/plane/links/${projectId}`, json("POST", localRef ? { local_ref: localRef } : {})),
  mapStates: (projectId: string, stateMap: Partial<Record<Status, string>>) =>
    request<LinkedProject>(`/plane/links/${projectId}`, json("PATCH", { state_map: stateMap })),
  unlink: (projectId: string) => request<void>(`/plane/links/${projectId}`, { method: "DELETE" }),
  /** Brings items into Traverse as linked tasks (or every open item assigned to you). Changes nothing in Plane. */
  bring: (body: { items: string[] } | { mine: true }) => request<Brought>("/plane/bring", json("POST", body)),
  outbox: () => request<Outbox>("/plane/outbox"),
  outboxCount: () => request<{ waiting: number }>("/plane/outbox/count"),
  /** Approves a push: Traverse reads the item from Plane again and writes only if nothing it sends changed there. */
  send: (id: string) => request<Push>(`/plane/pushes/${id}/send`, json("POST")),
  discard: (id: string) => request<Push>(`/plane/pushes/${id}/discard`, json("POST")),
  include: (id: string, include: Partial<Record<PushField, boolean>>) => request<Push>(`/plane/pushes/${id}`, json("PATCH", { include })),
  /** A field changed in Plane since you last saw it: keep Plane's (the task takes it) or send yours over it. */
  choose: (id: string, field: PushField, keep: "plane" | "mine") => request<Push>(`/plane/pushes/${id}/choose`, json("POST", { field, keep })),
  /** Undo is a new push of the values from before, waiting for you like any other. */
  undo: (id: string) => request<Push>(`/plane/pushes/${id}/undo`, json("POST")),
  /** Traverse's own projects, to link one (read through the Projects module's API; the servers never talk). */
  traverseProjects: () => request<{ id: string; name: string; archived: boolean }[]>("/tasks/projects"),
};
