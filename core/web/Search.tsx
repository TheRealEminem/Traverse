// ⌘K: one box for finding anything (every module's search: notes, tasks, people, whatever a module keeps) and for going to
// any section. Keyboard first: ⌘K (Ctrl K) opens it anywhere, ↑ ↓ move, Enter opens, Esc closes. The sidebar's
// search field and the narrow top bar's search button open it too (openSearch). App mounts it once.
import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api } from "./api";
import type { SearchGroup } from "./api";
import { ChevronRightIcon, HomeIcon, SearchIcon, SlidersIcon } from "./components/icons";
import { Spinner } from "./components/ui";
import type { ModuleWeb } from "./registry";
import { navigate } from "./router";
import { useShell } from "./shell";

const OPEN_EVENT = "app:search";
export const mac = navigator.platform.toLowerCase().includes("mac");

/** Opens the search box (from a button; ⌘K opens it on its own). */
export function openSearch() {
  window.dispatchEvent(new Event(OPEN_EVENT));
}

interface Row {
  key: string;
  group: string;
  title: string;
  snippet?: string;
  href: string;
  icon?: ReactNode;
}

/** The app's places (Home, each section, Settings) whose name has the words typed, or all of them for no words. */
function placesFor(modules: ModuleWeb[], q: string): Row[] {
  const all: Row[] = [
    ...(modules.length > 1 || modules.some((m) => m.home) ? [{ key: "place:", group: "Go to", title: "Home", href: "#/", icon: <HomeIcon size={16} /> }] : []),
    ...modules.flatMap((m) => (m.nav ?? []).map((n) => ({ key: `place:${n.path}`, group: "Go to", title: n.label, href: `#/${n.path}`, icon: n.icon }))),
    { key: "place:settings", group: "Go to", title: "Settings", href: "#/settings", icon: <SlidersIcon size={16} /> },
  ];
  const words = q.toLowerCase().split(/\s+/).filter(Boolean);
  return all.filter((r) => words.every((w) => r.title.toLowerCase().includes(w)));
}

export default function SearchPalette({ modules }: { modules: ModuleWeb[] }) {
  const { app } = useShell();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [found, setFound] = useState<{ q: string; groups: SearchGroup[] } | null>(null);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const q = query.trim();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && !e.altKey && !e.shiftKey && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((was) => !was);
      }
    };
    const onOpen = () => setOpen(true);
    window.addEventListener("keydown", onKey);
    window.addEventListener(OPEN_EVENT, onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener(OPEN_EVENT, onOpen);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    requestAnimationFrame(() => inputRef.current?.select());
    const before = document.activeElement as HTMLElement | null;
    return () => before?.focus?.();
  }, [open]);

  useEffect(() => {
    if (!open || !q) return;
    let alive = true;
    const t = setTimeout(() => api.search(q).then((groups) => alive && setFound({ q, groups }), () => alive && setFound({ q, groups: [] })), 120);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [q, open]);

  const rows = useMemo<Row[]>(() => {
    const places = placesFor(modules, q).slice(0, q ? 4 : 20);
    if (!q) return places;
    const hits = (found?.groups ?? []).flatMap((g) =>
      g.hits.map((h) => ({ key: h.ref, group: g.module_name, title: h.title, snippet: h.snippet || undefined, href: h.href })),
    );
    return [...hits, ...places];
  }, [modules, q, found]);

  useEffect(() => setActive(0), [q, found]);

  useEffect(() => {
    listRef.current?.querySelector(`[data-row="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [active]);

  if (!open) return null;
  const searching = !!q && found?.q !== q;
  const go = (row: Row | undefined) => {
    if (!row) return;
    setOpen(false);
    navigate(row.href.replace(/^#\/?/, ""));
  };
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown" || (e.key === "n" && e.ctrlKey)) {
      e.preventDefault();
      setActive((a) => (rows.length ? (a + 1) % rows.length : 0));
    } else if (e.key === "ArrowUp" || (e.key === "p" && e.ctrlKey)) {
      e.preventDefault();
      setActive((a) => (rows.length ? (a - 1 + rows.length) % rows.length : 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      go(rows[active]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      if (query) setQuery("");
      else setOpen(false);
    }
  };

  let lastGroup = "";
  return (
    <div
      className="fixed inset-0 z-50 flex animate-fade-in justify-center bg-[var(--scrim)] px-4 pt-[min(14vh,120px)] backdrop-blur-[3px]"
      onMouseDown={(e) => e.target === e.currentTarget && setOpen(false)}
    >
      <div role="dialog" aria-modal="true" aria-label="Search" className="flex h-fit max-h-[min(72vh,560px)] w-full max-w-[600px] animate-dialog-in flex-col overflow-hidden rounded-xl border border-line bg-surface shadow-lg">
        <div className="flex items-center gap-3 border-b border-line px-4">
          {searching ? <Spinner className="text-ink-faint" /> : <SearchIcon size={18} className="shrink-0 text-ink-faint" />}
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={`Search ${app.name}, or go to…`}
            role="combobox"
            aria-expanded="true"
            aria-controls="search-results"
            aria-activedescendant={rows[active] ? `search-row-${active}` : undefined}
            aria-autocomplete="list"
            className="h-14 min-w-0 flex-1 bg-transparent text-body text-ink outline-none placeholder:text-ink-faint focus-visible:outline-none"
          />
          <kbd className="kbd shrink-0 [@media(pointer:coarse)]:hidden">esc</kbd>
        </div>
        <div ref={listRef} id="search-results" role="listbox" aria-label="Results" className="min-h-0 flex-1 overflow-y-auto p-2">
          {q && !searching && rows.length === 0 && <p className="px-3 py-6 text-center text-ui text-ink-soft">Nothing matches “{q}”.</p>}
          {rows.map((row, n) => {
            const heading = row.group !== lastGroup ? row.group : null;
            lastGroup = row.group;
            return (
              <div key={row.key}>
                {heading && <div className="eyebrow px-3 pb-1 pt-2.5">{heading}</div>}
                <a
                  id={`search-row-${n}`}
                  data-row={n}
                  role="option"
                  aria-selected={n === active}
                  href={row.href}
                  onClick={(e) => {
                    e.preventDefault();
                    go(row);
                  }}
                  onMouseMove={() => n !== active && setActive(n)}
                  className={`flex items-center gap-3 rounded-md px-3 py-2 transition-colors duration-100 ${n === active ? "bg-forest/[.07]" : ""}`}
                >
                  {row.icon && <span className={n === active ? "text-forest" : "text-ink-soft"}>{row.icon}</span>}
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-ui font-medium">{row.title}</span>
                    {row.snippet && <span className="mt-0.5 line-clamp-1 block text-meta text-ink-soft">{row.snippet}</span>}
                  </span>
                  {n === active && <ChevronRightIcon size={16} className="shrink-0 text-ink-faint" />}
                </a>
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-4 border-t border-line px-4 py-2 text-meta text-ink-soft [@media(pointer:coarse)]:hidden">
          <span>
            <kbd className="kbd">↑</kbd> <kbd className="kbd">↓</kbd> to move
          </span>
          <span>
            <kbd className="kbd">↵</kbd> to open
          </span>
          <span className="ml-auto">
            <kbd className="kbd">{mac ? "⌘K" : "Ctrl K"}</kbd> anywhere
          </span>
        </div>
      </div>
    </div>
  );
}
