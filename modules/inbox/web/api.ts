import { api, json, request } from "@core/api";
import type { Job } from "@core/api";

export type Source = "paste" | "file" | "claude" | "trailmix";

export interface CaptureListItem {
  id: string;
  source: Source;
  title: string;
  title_auto: boolean;
  status: "new" | "review" | "done";
  origin_id: string | null;
  origin_title: string | null;
  origin_url: string | null;
  origin_at: string | null;
  read_by: string | null;
  read_at: string | null;
  created_at: string;
  updated_at: string;
  /** Proposals still waiting for you, and ones you accepted. */
  waiting: number;
  accepted: number;
  job: Job | null;
}

export interface Proposal {
  id: string;
  capture_id: string;
  text: string;
  assignee_name: string | null;
  due_on: string | null;
  /** 0 none, 1 low, 2 medium, 3 high, 4 urgent (Plane's scale). */
  priority: number;
  quote: string;
  status: "proposed" | "accepted" | "dropped";
}

export interface ProjectChoice {
  ref: string;
  title: string;
  href: string;
}

export interface Capture extends Omit<CaptureListItem, "waiting" | "accepted"> {
  raw_text: string;
  proposals: Proposal[];
  project: ProjectChoice | null;
}

export interface TrailmixStatus {
  enabled: boolean;
  url: string;
  last: { at: string; reachable: boolean; meetings?: number; brought_in?: number; error?: string } | null;
  brought_in: number;
  job: Job | null;
}

export type ProposalChanges = Partial<Pick<Proposal, "text" | "assignee_name" | "due_on" | "priority">>;

export const inboxApi = {
  list: () => request<CaptureListItem[]>("/inbox/captures"),
  count: () => request<{ waiting: number }>("/inbox/count"),
  get: (id: string) => request<Capture>(`/inbox/captures/${id}`),
  paste: (text: string) => request<{ id: string }>("/inbox/paste", json("POST", { text })),
  file: (name: string, text: string) => request<{ id: string }>("/inbox/file", json("POST", { name, text })),
  rename: (id: string, title: string) => request<{ ok: true }>(`/inbox/captures/${id}`, json("PATCH", { title })),
  readAgain: (id: string) => request<{ ok: true }>(`/inbox/captures/${id}/read`, json("POST")),
  setProject: (id: string, ref: string | null) => request<{ project: ProjectChoice | null }>(`/inbox/captures/${id}/project`, json("PUT", { ref })),
  acceptAll: (id: string) => request<{ accepted: number }>(`/inbox/captures/${id}/accept`, json("POST", {})),
  remove: (id: string) => request<void>(`/inbox/captures/${id}`, { method: "DELETE" }),
  edit: (id: string, changes: ProposalChanges) => request<Proposal>(`/inbox/proposals/${id}`, json("PATCH", changes)),
  accept: (id: string) => request<{ accepted: number }>(`/inbox/proposals/${id}/accept`, json("POST")),
  drop: (id: string) => request<{ ok: true }>(`/inbox/proposals/${id}/drop`, json("POST")),
  restore: (id: string) => request<{ ok: true }>(`/inbox/proposals/${id}/restore`, json("POST")),
  trailmix: () => request<TrailmixStatus>("/inbox/trailmix"),
  checkTrailmix: () => request<{ ok: true }>("/inbox/trailmix/check", json("POST")),

  /** Projects whose names match, through the host's search (the inbox never asks the tasks module directly). The
   * tasks module marks its projects' hits with the snippet "Project". */
  findProjects: async (q: string): Promise<ProjectChoice[]> => {
    const groups = await api.search(q);
    return (groups.find((g) => g.module === "tasks")?.hits ?? [])
      .filter((h) => h.snippet === "Project")
      .map((h) => ({ ref: h.ref, title: h.title, href: h.href }));
  },
};

/** Files the inbox reads; the page reads them and sends their text. */
export const FILE_KINDS = [".txt", ".md", ".eml"];
