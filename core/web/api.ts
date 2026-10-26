// The host's API client. Each module has its own small client next to its views (modules/<id>/web/api.ts),
// built on request() and json() from here.

/** Fired when the server says we need to sign in (installs with an access token only). */
export const AUTH_EVENT = "app:auth-required";
/** Fired after this app changes something on the server, so screens refresh at once instead of on the next poll. */
export const CHANGED_EVENT = "app:changed";

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, { credentials: "same-origin", ...init });
  if (res.status === 401 && !path.startsWith("/login")) window.dispatchEvent(new Event(AUTH_EVENT));
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  if (init?.method && init.method !== "GET") window.dispatchEvent(new Event(CHANGED_EVENT)); // see live.ts
  return res.status === 204 ? (undefined as T) : res.json();
}

export const json = (method: string, body?: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export interface AppInfo {
  id: string;
  name: string;
  tagline: string;
  version: string;
  modules: { id: string; name: string }[];
  auth_required: boolean;
}

/** A thing's latest background job, as the server reports it next to the thing. */
export interface Job {
  id: string;
  kind: string;
  status: "queued" | "running" | "waiting" | "done" | "error";
  stage: string | null;
  wait_reason: string | null;
  error: string | null;
  updated_at: string;
}

/** Lockdown (core/server/lockdown.py): nothing leaves this Mac. `parked`: jobs waiting for it to be off. */
export interface LockdownStatus {
  on: boolean;
  parked: number;
}
export const LOCKDOWN = "Lockdown is on";

/** The job is parked until Lockdown is off: it goes ahead by itself then, so there's nothing to press. */
export function heldByLockdown(job: Job | null | undefined): boolean {
  return job?.status === "waiting" && !!job.wait_reason?.startsWith(LOCKDOWN);
}

/** Something in another module, described by that module. */
export interface Linked {
  ref: string;
  module: string;
  id: string;
  title: string;
  href: string;
  kind: string;
  direction: "to" | "from";
}

export interface SearchGroup {
  module: string;
  module_name: string;
  hits: { ref: string; id: string; title: string; snippet: string; href: string }[];
}

export type SettingValue = string | number | boolean | string[];
export interface SettingsState {
  values: Record<string, SettingValue>;
  secret_hints: Record<string, string | null>;
}

export type ProviderId = "ollama" | "anthropic" | "openai" | "gemini" | "deepseek" | "custom";
export interface ProviderInfo {
  id: ProviderId;
  label: string;
  kind: "local" | "cloud" | "custom";
  ready: boolean; // keyed (or reachable, for Ollama) and configured
  reason: string;
}

/** What AI calls cost (core/server/pricing.py). Costs are US dollars; `unknown` counts calls at a price nobody
 * published, which aren't in `cost`; `stopped` counts calls Lockdown stopped, which aren't in `failed`. */
export interface UsageTotals {
  calls: number;
  cost: number;
  failed: number;
  stopped: number;
  unknown: number;
  input_tokens: number;
  output_tokens: number;
}
export interface UsageGroup extends UsageTotals {
  id: string; // a provider id, or a module id ("core" for Settings, "" for calls made outside a job)
  label: string;
}
export interface UsageCall {
  at: string;
  module: string;
  module_label: string;
  job: string;
  call: "complete" | "structured";
  provider: string;
  provider_label: string;
  model: string;
  input_tokens: number | null;
  cached_tokens: number | null;
  output_tokens: number | null;
  cost: number | null; // null: unknown, or a failure that spent nothing
  failed: boolean;
  stopped: boolean; // Lockdown stopped it before anything was sent
  unknown: boolean;
  error: string | null;
}
export interface AIUsage {
  month: UsageTotals & { start: string };
  last_30_days: UsageTotals & { by_provider: UsageGroup[]; by_module: UsageGroup[] };
  recent: UsageCall[];
  prices_checked: string;
}

/** Running inside the Mac app's own window (rather than a browser): it can be asked to quit, or to show a file,
 *  and it lists the sidebar's sections in its menu bar menu. */
type AppBridge = { postMessage: (message: string) => void };
const bridge = (window as unknown as { webkit?: { messageHandlers?: { app?: AppBridge } } }).webkit?.messageHandlers?.app;
export const inApp = !!bridge;
export const quitApp = () => bridge?.postMessage("quit");
export const revealInFinder = (path: string) => bridge?.postMessage(`reveal:${path}`);
export const showInAppMenu = (sections: { label: string; path: string }[]) => bridge?.postMessage(`menu:${JSON.stringify(sections)}`);

/** Where the Mac app's updates stand (Updater.report in mac/), sent by its window as an "app-updates" event. */
export interface UpdateReport {
  enabled: boolean;
  current: string;
  state: "idle" | "checking" | "up-to-date" | "offline" | "locked-down" | "available" | "downloading" | "installing" | "going-back" | "failed";
  version?: string;
  progress?: number | null;
  error?: string;
  prerelease?: boolean;
  beta: boolean;
  skipped?: string | null;
  previous?: string | null;
  working: boolean;
  checked_at?: string | null;
}
export type UpdateCommand = "get" | "check" | "install" | "skip" | "unskip" | "beta-on" | "beta-off" | "go-back" | "try-again";
export const sendUpdates = (what: UpdateCommand) => bridge?.postMessage(`updates:${what}`);

/** Whether the Mac app may read your calendar: "unasked" until macOS has asked you, "unavailable" when this app
 *  doesn't use it (mac/Sources/AppHost/CalendarBridge.swift). */
export type CalendarAccess = "full" | "unasked" | "denied" | "restricted" | "write_only" | "unavailable";
/** An event from your Mac's Calendar. start and end carry the Mac's offset; free: it doesn't block time. */
export interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  all_day: boolean;
  calendar: string;
  free: boolean;
}
type CalendarBridge = { postMessage: (message: object) => Promise<unknown> };
const calendarBridge = (window as unknown as { webkit?: { messageHandlers?: { calendar?: CalendarBridge } } }).webkit?.messageHandlers?.calendar;
const askCalendar = <T>(message: object) => calendarBridge!.postMessage(message) as Promise<T>;

/** Your Mac's Calendar, read-only, through the Mac app's window: every account the Calendar app has. null in a browser
 *  (and in an app built before it could). Nothing is kept: each call reads it afresh. */
export const macCalendar = calendarBridge
  ? {
      access: () => askCalendar<{ access: CalendarAccess }>({ ask: "access" }).then((r) => r.access),
      /** macOS asks you, the first time; afterwards it answers for you (System Settings changes it). */
      request: () => askCalendar<{ access: CalendarAccess }>({ ask: "request" }).then((r) => r.access),
      events: (from: Date, to: Date) =>
        askCalendar<{ access: CalendarAccess; events: CalendarEvent[] }>({ ask: "events", from: from.toISOString(), to: to.toISOString() }),
      openSettings: () => askCalendar<unknown>({ ask: "settings" }),
    }
  : null;

/** A family app installed on this Mac (core/server/family.py). */
export interface FamilyApp {
  id: string;
  name: string;
  version: string;
  running: boolean;
  offers: string[];
  seen_at: string;
  self: boolean;
}
export interface FamilyStatus {
  enabled: boolean;
  folder: string | null;
  sharing: boolean;
  apps: FamilyApp[];
}

/** Someone from the people directory (core/server/people.py): you as "core:me", or a module's or family app's ref. */
export interface Person {
  ref: string;
  name: string;
  email: string | null;
  detail: string | null;
  module: string; // the module that knows them, "core" for you, "family" for another family app
}
export interface PeopleResult {
  people: Person[];
  /** How to see people another family app knows, when it's closed ("Open The Lodge to see this here."). */
  note: string | null;
}
/** What a PersonPicker gives back: a ref from the directory, or null for a name typed in by hand. */
export interface PersonChoice {
  ref: string | null;
  name: string;
}

/** Claude's access through the MCP server (core/server/mcp.py). The token itself comes back only inside `setup`, once. */
export interface McpStatus {
  on: boolean;
  hint: string | null;
  url: string;
  tools: { name: string; title: string; module: string; writes: boolean }[];
}
export interface McpSetup {
  claude_code: string;
  claude_desktop: string;
}

export interface BackupItem {
  name: string;
  kind: "auto" | "manual" | "before-restore" | "before-update";
  created_at: string;
  bytes: number;
}

export const api = {
  app: () => request<AppInfo>("/app"),
  auth: () => request<{ required: boolean; ok: boolean }>("/auth"),
  login: (token: string) => request<{ ok: true }>("/login", json("POST", { token })),
  logout: () => request<{ ok: true }>("/logout", json("POST")),
  shutdown: () => request<{ ok: true }>("/shutdown", json("POST")),
  changes: (since: number) => request<{ seq: number; names: string[] }>(`/changes?since=${since}`),

  backups: () => request<{ items: BackupItem[]; folder: string }>("/backups"),
  backUpNow: () => request<BackupItem>("/backups", json("POST")),
  restoreBackup: (name: string) => request<{ restored: string; kept: string; counts: Record<string, number> }>(`/backups/${name}/restore`, json("POST")),
  deleteBackup: (name: string) => request<void>(`/backups/${name}`, { method: "DELETE" }),
  exportAll: () => request<{ name: string; folder: string; bytes: number; counts: Record<string, Record<string, number>> }>("/export", json("POST")),

  settings: () => request<SettingsState>("/settings"),
  putSettings: (changes: Record<string, SettingValue>) => request<SettingsState>("/settings", json("PUT", changes)),
  family: () => request<FamilyStatus>("/family"),
  mcp: () => request<McpStatus>("/mcp"),
  mcpToken: () => request<McpStatus & { setup: McpSetup }>("/mcp/token", json("POST")),
  mcpOff: () => request<void>("/mcp/token", { method: "DELETE" }),
  providers: () => request<ProviderInfo[]>("/ai/providers"),
  providerModels: (id: ProviderId) => request<{ models: string[] }>(`/ai/providers/${id}/models`),
  providerTest: (id: ProviderId) => request<{ message: string }>(`/ai/providers/${id}/test`, json("POST")),
  aiUsage: () => request<AIUsage>("/ai/usage"),
  lockdown: () => request<LockdownStatus>("/lockdown"),

  search: (q: string) => request<SearchGroup[]>(`/search?q=${encodeURIComponent(q)}`),
  people: (q: string, limit = 8) => request<PeopleResult>(`/people?q=${encodeURIComponent(q)}&limit=${limit}`),
  links: (ref: string) => request<Linked[]>(`/links?ref=${encodeURIComponent(ref)}`),
  jobGo: (id: string, force = false) => request<{ ok: true }>(`/jobs/${id}/go`, json("POST", { force })),
  jobRetry: (id: string) => request<{ ok: true }>(`/jobs/${id}/retry`, json("POST")),
};
