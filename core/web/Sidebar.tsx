// The sidebar: the app's mark, Lockdown's sign while it's on, the main action, search across every module (it opens
// the ⌘K box, Search.tsx), and each module's navigation.
import type { ReactNode } from "react";
import { HomeIcon, SearchIcon, SlidersIcon } from "./components/icons";
import { Logo } from "./components/illustrations";
import type { ModuleWeb } from "./registry";
import { mac, openSearch } from "./Search";
import { useShell } from "./shell";
import { LockdownSign } from "./views/Lockdown";

function NavLink({ icon, label, href, active, badge }: { icon: ReactNode; label: string; href: string; active: boolean; badge?: ReactNode }) {
  return (
    <a
      href={href}
      aria-current={active ? "page" : undefined}
      className={`flex h-9 w-full items-center gap-2.5 rounded-md px-2.5 text-ui font-medium transition-[background-color,color,transform] duration-150 ease-out hover:translate-x-px ${
        active ? "bg-surface text-ink shadow-sm ring-1 ring-line" : "text-ink-soft hover:bg-forest/[.05] hover:text-ink"
      }`}
    >
      <span className={`transition-colors ${active ? "text-forest" : ""}`}>{icon}</span>
      <span className="flex-1 text-left">{label}</span>
      {badge}
    </a>
  );
}

/** A count for a nav item (open tasks…), styled the family way. Modules render it from their badge component. */
export function NavCount({ n }: { n: number | null | undefined }) {
  if (!n) return null;
  return (
    <span className="min-w-[20px] rounded-full bg-forest/10 px-1.5 py-0.5 text-center text-caption font-semibold tabular-nums text-forest-deep">
      {n}
    </span>
  );
}

export default function Sidebar({ modules, path, opaque }: { modules: ModuleWeb[]; path: string; opaque?: boolean }) {
  const { app } = useShell();
  const primary = modules.find((m) => m.primary)?.primary;
  const showHome = modules.length > 1 || modules.some((m) => m.home);
  const under = (p: string) => path === p || path.startsWith(p + "/");
  // Only the most specific entry is current: on "tasks/projects", Projects, not My tasks ("tasks") as well.
  const current = modules
    .flatMap((m) => (m.nav ?? []).map((item) => item.path))
    .filter(under)
    .sort((a, b) => b.length - a.length)[0];

  return (
    <aside className={`chrome relative z-10 flex h-full w-[288px] shrink-0 flex-col border-r border-line shadow-chrome ${opaque ? "chrome-opaque" : ""}`}>
      <a href="#/" className="flex items-center gap-3 px-6 pb-5 pt-7">
        <Logo size={38} />
        <div className="min-w-0">
          <div className="font-display text-wordmark font-semibold leading-none tracking-[-0.02em] text-ink">{app.name}</div>
          {app.tagline && <div className="mt-1.5 text-caption leading-none text-ink-faint">{app.tagline}</div>}
        </div>
      </a>

      <LockdownSign />

      <div className="px-4">
        {primary && (
          <button onClick={() => void primary.run()} className="group btn btn-primary mb-4 h-11 w-full rounded-md text-label font-semibold">
            <span className="transition-transform duration-200 ease-spring group-hover:-rotate-6 group-hover:scale-110">{primary.icon}</span>
            {primary.label}
          </button>
        )}
        <button
          onClick={openSearch}
          aria-label="Search everything"
          aria-keyshortcuts={mac ? "Meta+K" : "Control+K"}
          className="field flex h-9 w-full items-center gap-2.5 border-transparent bg-forest/[.045] py-0 pl-3 pr-2 text-left text-ink-faint shadow-none hover:border-line"
        >
          <SearchIcon size={16} />
          <span className="flex-1">Search</span>
          <kbd className="kbd pointer-events-none [@media(pointer:coarse)]:hidden">{mac ? "⌘K" : "Ctrl K"}</kbd>
        </button>
      </div>

      {modules.map((m) => m.sidebarTop && <m.sidebarTop key={m.id} />)}

      <nav className="mt-3 flex-1 space-y-0.5 overflow-y-auto px-3" aria-label="Sections">
        {showHome && <NavLink icon={<HomeIcon size={16} />} label="Home" href="#/" active={path === ""} />}
        {modules.flatMap((m) =>
          (m.nav ?? []).map((item) => {
            const Badge = item.badge;
            return (
              <NavLink
                key={m.id + item.path}
                icon={item.icon}
                label={item.label}
                href={`#/${item.path}`}
                active={item.path === current}
                badge={Badge ? <Badge /> : undefined}
              />
            );
          }),
        )}
      </nav>

      <div className="border-t border-line px-3 py-2">
        <NavLink icon={<SlidersIcon size={16} />} label="Settings" href="#/settings" active={path === "settings"} />
      </div>
    </aside>
  );
}
