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

export const planeApi = {
  team: () => request<Team>("/plane/team"),
  status: () => request<PlaneStatus>("/plane/status"),
  projects: () => request<PlaneProject[]>("/plane/projects"),
  members: () => request<PlaneMember[]>("/plane/members"),
  pull: () => request<{ job: string }>("/plane/pull", json("POST")),
  test: () => request<{ message: string; projects: number }>("/plane/test", json("POST")),
};
