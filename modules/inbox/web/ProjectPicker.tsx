// Choosing the project a capture files into. Projects are found through the host's search, by name.
import { useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { CheckIcon, ChevronDownIcon, SearchIcon } from "@core/components/icons";
import { inboxApi } from "./api";
import type { ProjectChoice } from "./api";
import { ProjectIcon } from "./bits";

type Option = ProjectChoice | null; // null: no project

export default function ProjectPicker({ value, onChange }: { value: ProjectChoice | null; onChange: (p: ProjectChoice | null) => void }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<ProjectChoice[] | null>(null);
  const [active, setActive] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const listId = useId();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => !box.current?.contains(e.target as Node) && setOpen(false);
    window.addEventListener("pointerdown", onDown, true);
    return () => window.removeEventListener("pointerdown", onDown, true);
  }, [open]);

  useEffect(() => {
    if (!q.trim()) return setHits(null);
    let live = true;
    const t = setTimeout(() => void inboxApi.findProjects(q).then((found) => live && (setHits(found), setActive(0)), () => live && setHits([])), 180);
    return () => {
      live = false;
      clearTimeout(t);
    };
  }, [q]);

  const options: Option[] = [...(hits ?? []), ...(value ? [null] : [])];
  const choose = (o: Option) => {
    setOpen(false);
    setQ("");
    trigger.current?.focus();
    if ((o?.ref ?? null) !== (value?.ref ?? null)) onChange(o);
  };
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "ArrowDown") setActive((a) => Math.min(options.length - 1, a + 1));
    else if (e.key === "ArrowUp") setActive((a) => Math.max(0, a - 1));
    else if (e.key === "Enter" && options.length) choose(options[active]);
    else if (e.key === "Escape") {
      setOpen(false);
      trigger.current?.focus();
    } else return;
    e.preventDefault();
  };

  return (
    <div ref={box} className="relative min-w-0 max-w-full">
      <button
        ref={trigger}
        type="button"
        className="btn btn-sm btn-soft max-w-full"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <ProjectIcon size={16} className={value ? "text-forest" : ""} />
        <span className="truncate">{value ? value.title : "Choose a project"}</span>
        <ChevronDownIcon size={16} className="text-ink-soft" />
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-1.5 w-[min(18rem,calc(100vw-2.5rem))] animate-pop rounded-md border border-line bg-surface p-1.5 shadow-lg">
          <div className="relative">
            <SearchIcon size={16} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-faint" />
            <input
              autoFocus
              role="combobox"
              aria-label="Find a project"
              aria-controls={listId}
              aria-expanded={options.length > 0}
              aria-activedescendant={options.length ? `${listId}-${active}` : undefined}
              className="field w-full pl-8"
              placeholder="Find a project"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={onKey}
            />
          </div>
          <ul id={listId} role="listbox" aria-label="Projects" className="mt-1 max-h-64 overflow-y-auto">
            {options.map((o, i) => (
              <li
                key={o?.ref ?? "none"}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={(o?.ref ?? null) === (value?.ref ?? null)}
                onPointerEnter={() => setActive(i)}
                onClick={() => choose(o)}
                className={`flex cursor-pointer items-center gap-2.5 rounded-sm px-2.5 py-2 text-ui ${i === active ? "bg-forest/[.07]" : ""} ${o ? "" : "text-ink-soft"}`}
              >
                <ProjectIcon size={16} className={o ? "text-ink-soft" : "text-ink-faint"} />
                <span className="min-w-0 flex-1 truncate">{o ? o.title : "No project"}</span>
                {(o?.ref ?? null) === (value?.ref ?? null) && <CheckIcon size={16} className="text-forest" />}
              </li>
            ))}
          </ul>
          <p className="px-2.5 py-1.5 text-hint text-ink-soft empty:hidden" aria-live="polite">
            {!q.trim() ? "Type a project’s name." : hits?.length === 0 ? "No project by that name." : null}
          </p>
        </div>
      )}
    </div>
  );
}
