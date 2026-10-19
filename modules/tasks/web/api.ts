import { json, request } from "@core/api";

export type Status = "todo" | "doing" | "waiting" | "done" | "dropped";

export interface Task {
  id: string;
  text: string;
  done: boolean;
  status: Status;
  notes: string;
  priority: number; // 0 none, 1 low, 2 medium, 3 high, 4 urgent (Plane's scale)
  start_on: string | null;
  due_on: string | null;
  assignee_ref: string | null;
  assignee_name: string | null;
  estimate_min: number | null;
  tags: string[];
  project_id: string | null;
  milestone_id: string | null;
  parent_id: string | null;
  source: string; // manual | action-item | ai | import
  source_ref: string | null;
  created_at: string;
  updated_at: string | null;
  completed_at: string | null;
  /** Where it came from, described by that module (null if it's gone or its module is off). */
  came_from: Described | null;
  blocked: boolean;
  subtask_count?: number;
  subtasks_done?: number;
}

/** Something in another module, as that module describes it. */
export interface Described {
  title: string;
  href: string;
  module: string;
}

export interface Update {
  id: string;
  kind: "comment" | "status" | "summary";
  body: string;
  author_ref: string | null;
  author_name: string | null;
  written_by: string | null;
  created_at: string;
}

export interface TaskDetail extends Task {
  subtasks: Task[];
  blocked_by: { id: string; text: string; status: Status }[];
  blocks: { id: string; text: string; status: Status }[];
  updates: Update[];
}

export interface Labelled<T = string> {
  value: T;
  label: string;
  tone: "trail" | "sun" | "sky" | "forest" | "berry" | "neutral";
}

export interface Meta {
  statuses: Labelled<Status>[];
  open: Status[];
  project_statuses: Labelled[];
  health: Labelled[];
  priorities: Labelled<number>[];
}

export interface ProjectSummary {
  id: string;
  name: string;
  status: string;
  archived: boolean;
}

export interface Milestone {
  id: string;
  name: string;
  due_on: string | null;
  done: boolean;
}

export interface ProjectDetail extends ProjectSummary {
  milestones: Milestone[];
}

export interface ListParams {
  project?: string;
  assignee?: string;
  status?: string;
  when?: "late" | "today" | "week" | "waiting";
  q?: string;
  parent?: string;
}

const query = (params: ListParams) => {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== "") as [string, string][]).toString();
  return q ? `?${q}` : "";
};

export const tasksApi = {
  list: (params: ListParams = {}) => request<Task[]>(`/tasks${query(params)}`),
  count: (assignee?: string) => request<{ open: number; due_today: number; late: number }>(`/tasks/count${assignee ? `?assignee=${assignee}` : ""}`),
  meta: () => request<Meta>("/tasks/meta"),
  get: (id: string) => request<TaskDetail>(`/tasks/${id}`),
  create: (body: Partial<Task> & { text: string }) => request<{ id: string }>("/tasks", json("POST", body)),
  update: (id: string, changes: Partial<Task>) => request<TaskDetail>(`/tasks/${id}`, json("PATCH", changes)),
  setDone: (id: string, done: boolean) => request<unknown>(`/tasks/${id}`, json("PATCH", { done })),
  remove: (id: string) => request<void>(`/tasks/${id}`, { method: "DELETE" }),
  block: (id: string, blockedBy: string) => request<unknown>(`/tasks/${id}/blockers`, json("POST", { blocked_by: blockedBy })),
  unblock: (id: string, blockedBy: string) => request<unknown>(`/tasks/${id}/blockers/${blockedBy}`, { method: "DELETE" }),
  comment: (id: string, body: string) => request<Update>(`/tasks/${id}/updates`, json("POST", { body })),
  projects: () => request<ProjectSummary[]>("/tasks/projects"),
  project: (id: string) => request<ProjectDetail>(`/tasks/projects/${id}`),
};
