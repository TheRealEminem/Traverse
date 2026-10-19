// Navigation is the URL hash: "#/notes/3f2a…". No router library: one hook, one function, one matcher.
import { useSyncExternalStore } from "react";

const current = () => decodeURI(location.hash.replace(/^#\/?/, ""));

const subscribe = (on: () => void) => {
  window.addEventListener("hashchange", on);
  return () => window.removeEventListener("hashchange", on);
};

/** The current path without "#/", e.g. "notes/3f2a…" ("" is Home). */
export function useRoute(): string {
  return useSyncExternalStore(subscribe, current);
}

export function navigate(path: string) {
  location.hash = `/${path.replace(/^#?\/?/, "")}`;
}

/** match("notes/:id", "notes/abc") -> { id: "abc" }; null when it doesn't fit. */
export function match(pattern: string, path: string): Record<string, string> | null {
  const want = pattern.split("/").filter(Boolean);
  const have = path.split("/").filter(Boolean);
  if (want.length !== have.length) return null;
  const params: Record<string, string> = {};
  for (let i = 0; i < want.length; i++) {
    if (want[i].startsWith(":")) params[want[i].slice(1)] = have[i];
    else if (want[i] !== have[i]) return null;
  }
  return params;
}
