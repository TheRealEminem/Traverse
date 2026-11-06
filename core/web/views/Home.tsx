// Home: the place where every module shows what's new. In the unified app this is the front door. When a module
// starts the day (registry.start), Home points to it first rather than repeating it.
import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { ChevronRightIcon } from "../components/icons";
import { Scene } from "../components/illustrations";
import { useShell } from "../shell";
import { modulesFor } from "../registry";
import type { ModuleWeb } from "../registry";

const greeting = () => {
  const h = new Date().getHours();
  return h < 5 ? "Good evening" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
};

/** The module whose page starts the day: "Start the day" until you've looked today, then a way back to it. */
function DayStart({ module: m }: { module: ModuleWeb }) {
  const [fresh, setFresh] = useState<string | null | undefined>(undefined);
  useEffect(() => {
    m.start!().then(setFresh, () => setFresh(null));
  }, [m]);
  const nav = m.nav?.[0];
  const href = `#/${fresh ?? nav?.path ?? m.id}`;
  return (
    <a href={href} className="panel group flex items-center gap-4 p-5 transition-[border-color,transform] duration-150 ease-out hover:-translate-y-px hover:border-forest/30">
      <span className="well well-forest">{nav?.icon}</span>
      <span className="min-w-0 flex-1">
        <span className="block text-heading font-semibold tracking-[-0.01em]">{fresh ? "Start the day" : `Your day is in ${m.name}`}</span>
        <span className="block text-hint text-ink-soft">
          {fresh === undefined
            ? "…"
            : fresh
              ? `${m.name} has what's on today, what moved since you last looked, and a plan to make.`
              : `Today's plan, what moved, and what's ahead.`}
        </span>
      </span>
      <span className="btn btn-sm btn-soft shrink-0 max-sm:hidden">Open {m.name}</span>
      <ChevronRightIcon size={18} className="shrink-0 text-ink-faint sm:hidden" />
    </a>
  );
}

export default function Home() {
  const { app, theme } = useShell();
  const modules = modulesFor(app.modules.map((m) => m.id));
  const cards = modules.filter((m) => m.home);
  const day = modules.find((m) => m.start && m.nav?.length);
  return (
    <div className="flex flex-col">
      <div className="relative animate-enter">
        <div aria-hidden="true" className="absolute inset-x-[10%] bottom-0 top-1/3 rounded-hero bg-forest/10 blur-3xl" />
        <div className="art-frame h-[clamp(150px,18vw+40px,220px)]">
          <Scene parallax dusk={theme.dusk} className="absolute inset-0 h-full w-full" />
        </div>
      </div>
      <div className="mt-8 animate-enter" style={{ animationDelay: "60ms" } as CSSProperties}>
        <p className="eyebrow mb-2.5">{new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}</p>
        <h1 className="hero-title">{greeting()}</h1>
        {app.tagline && <p className="hero-sub mt-3">{app.name}: {app.tagline}.</p>}
      </div>
      <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {day && (
          <div className="animate-enter sm:col-span-2" style={{ animationDelay: "120ms" } as CSSProperties}>
            <DayStart module={day} />
          </div>
        )}
        {cards.map((m, i) => {
          const Card = m.home!;
          const delay = { animationDelay: `${(day ? 180 : 120) + i * 60}ms` } as CSSProperties;
          return m.homeWide ? (
            <div key={m.id} className="animate-enter sm:col-span-2" style={delay}>
              <Card />
            </div>
          ) : (
            <section key={m.id} className="panel animate-enter p-5" style={delay}>
              <Card />
            </section>
          );
        })}
      </div>
    </div>
  );
}
