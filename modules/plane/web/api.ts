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
  /** Traverse's own projects, to link one (read through the Projects module's API; the servers never talk). */
  traverseProjects: () => request<{ id: string; name: string; archived: boolean }[]>("/tasks/projects"),
};
