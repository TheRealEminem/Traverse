// A starting shell for a new family app, and a live specimen of every piece in the kit.
// Keep the structure (Ambient behind everything, a 288px glass sidebar, an 872px reading column),
// replace the contents with your app's own screens.
import { useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import {
  CheckSquareIcon,
  CompassIcon,
  LeafIcon,
  MicIcon,
  MonitorIcon,
  MoonIcon,
  PlusIcon,
  SearchIcon,
  SignpostIcon,
  SlidersIcon,
  SparkleIcon,
  SunIcon,
  TrashIcon,
} from "./components/icons";
import { Ambient, ContourBadge, Logo, TrailScene } from "./components/illustrations";
import {
  ControlRow,
  CopyButton,
  PageHeader,
  Pulse,
  Segmented,
  Select,
  Skeleton,
  SpeakerChip,
  StatusChip,
  SwitchRow,
  Toast,
  TooltipLayer,
  useConfirm,
} from "./components/ui";
import type { ToastState } from "./components/ui";
import { useTheme } from "./theme";
import type { ThemePref } from "./theme";

const delay = (ms: number) => ({ animationDelay: `${ms}ms` }) as CSSProperties;

function NavItem({ icon, label, active, count }: { icon: ReactNode; label: string; active?: boolean; count?: number }) {
  return (
    <button
      className={`flex h-9 w-full items-center gap-2.5 rounded-md px-2.5 text-ui font-medium transition-[background-color,color,transform] duration-150 ease-out hover:translate-x-px ${
        active ? "bg-surface text-ink shadow-sm ring-1 ring-line" : "text-ink-soft hover:bg-forest/[.05] hover:text-ink"
      }`}
    >
      <span className={`transition-colors ${active ? "text-forest" : ""}`}>{icon}</span>
      <span className="flex-1 text-left">{label}</span>
      {count !== undefined && (
        <span className="min-w-[20px] rounded-full bg-forest/10 px-1.5 py-0.5 text-center text-caption font-semibold tabular-nums text-forest-deep">
          {count}
        </span>
      )}
    </button>
  );
}

/** A settings-style section: a forest well, a heading with a one-line blurb, then a panel of rows. */
function Section({ icon, title, blurb, ms = 0, children }: { icon: ReactNode; title: string; blurb: string; ms?: number; children: ReactNode }) {
  return (
    <section className="mb-10 animate-enter" style={delay(ms)}>
      <div className="mb-3 flex items-start gap-3 px-1">
        <span className="well well-forest">{icon}</span>
        <div className="min-w-0">
          <h2 className="text-heading font-semibold tracking-[-0.01em]">{title}</h2>
          <p className="mt-0.5 text-ui leading-snug text-ink-soft">{blurb}</p>
        </div>
      </div>
      <div className="panel divide-y divide-line px-5 sm:px-6">{children}</div>
    </section>
  );
}

function Sidebar() {
  return (
    <aside className="chrome relative z-10 hidden h-full w-[288px] shrink-0 flex-col border-r border-line shadow-chrome lg:flex">
      <div className="flex items-center gap-3 px-6 pb-5 pt-7">
        <Logo size={38} />
        <div className="min-w-0">
          <div className="font-display text-wordmark font-semibold leading-none tracking-[-0.02em] text-ink">Trailmix</div>
          <div className="mt-1.5 text-caption leading-none text-ink-faint">notes from along the way</div>
        </div>
      </div>
      <div className="px-4">
        <button className="group btn btn-primary h-11 w-full rounded-md text-label font-semibold">
          <MicIcon size={18} className="transition-transform duration-200 ease-spring group-hover:-rotate-6 group-hover:scale-110" />
          New recording
        </button>
        <div className="relative mt-4">
          <SearchIcon size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
          <input
            placeholder="Search"
            className="field h-9 w-full border-transparent bg-forest/[.045] py-0 pl-9 pr-12 shadow-none hover:border-line focus:bg-surface"
          />
          <kbd className="kbd pointer-events-none absolute right-2 top-1/2 -translate-y-1/2">⌘K</kbd>
        </div>
      </div>
      <nav className="mt-3 space-y-0.5 px-3">
        <NavItem icon={<CompassIcon size={16} />} label="Specimen" active />
        <NavItem icon={<CheckSquareIcon size={16} />} label="Tasks" count={3} />
      </nav>
      <nav className="fade-edges-y mt-3 flex-1 overflow-y-auto px-3 pb-4 pt-1">
        <h3 className="eyebrow px-3 pb-1 pt-3">Yesterday</h3>
        {["Launch planning", "Design review"].map((t, i) => (
          <button
            key={t}
            className={`mb-0.5 block w-full rounded-md px-3 py-2.5 text-left transition-colors duration-150 ${
              i === 0 ? "bg-surface shadow-sm ring-1 ring-line" : "hover:bg-forest/[.05]"
            }`}
          >
            <div className={`truncate text-ui leading-5 ${i === 0 ? "font-semibold" : "font-medium"}`}>{t}</div>
            <div className="mt-0.5 flex items-center gap-1.5 text-meta leading-4 text-ink-soft">
              <span className="tabular-nums">4:00 PM</span>
              <span className="text-ink-faint">·</span>
              <span className="tabular-nums">0:37</span>
            </div>
          </button>
        ))}
      </nav>
      <div className="border-t border-line px-3 py-2">
        <NavItem icon={<SlidersIcon size={16} />} label="Settings" />
      </div>
    </aside>
  );
}

export default function App() {
  const theme = useTheme();
  const [toast, setToast] = useState<ToastState | null>(null);
  const [confirm, confirmDialog] = useConfirm();
  const [auto, setAuto] = useState(true);
  const [local, setLocal] = useState(false);
  const [model, setModel] = useState("small");
  const [view, setView] = useState<"summary" | "transcript" | "ask">("summary");
  const [pct, setPct] = useState(38);

  return (
    <div className="relative flex h-full">
      <Ambient />
      <Sidebar />
      <main className="relative z-10 min-w-0 flex-1 overflow-y-auto">
        <div className="relative mx-auto w-full max-w-[872px] px-5 pb-24 pt-7 sm:px-8 lg:px-10 lg:pt-12">
          {/* Hero: artwork in a frame that fades into the page, then eyebrow, title, sub, action */}
          <div className="relative animate-enter">
            <div aria-hidden="true" className="absolute inset-x-[10%] bottom-0 top-1/3 rounded-hero bg-forest/10 blur-3xl" />
            <div className="art-frame h-[clamp(168px,20vw+48px,250px)]">
              <TrailScene parallax walking dusk={theme.dusk} className="absolute inset-0 h-full w-full" />
            </div>
          </div>
          <div className="mt-8 animate-enter" style={delay(60)}>
            <p className="eyebrow mb-2.5">Thursday, October 8</p>
            <h1 className="hero-title">Ready when you are</h1>
            <p className="hero-sub mt-3">Trailmix quietly records, transcribes, and organizes your conversations locally.</p>
          </div>
          <div className="mt-7 flex animate-enter flex-wrap items-center gap-3" style={delay(120)}>
            <button className="btn btn-hero btn-record">
              <span className="h-2.5 w-2.5 rounded-full bg-on-accent" />
              Start recording
            </button>
            <Segmented<ThemePref>
              label="Theme"
              value={theme.pref}
              onChange={theme.setPref}
              options={[
                { id: "light", label: "Day", icon: <SunIcon size={16} /> },
                { id: "dusk", label: "Dusk", icon: <MoonIcon size={16} /> },
                { id: "system", label: "System", icon: <MonitorIcon size={16} /> },
              ]}
            />
          </div>

          <div className="mt-16">
            <PageHeader
              title="Specimen"
              subtitle="Every piece of the kit, in context."
              actions={
                <div className="flex gap-1">
                  <button className="icon-btn" data-tip="Add">
                    <PlusIcon size={18} />
                  </button>
                  <button
                    className="icon-btn hover:!bg-trail-soft hover:!text-trail-deep"
                    data-tip="Delete"
                    onClick={async () => {
                      if (await confirm({ title: "Delete this meeting?", body: "The recording, transcript and summary go with it.", confirmLabel: "Delete", tone: "danger" }))
                        setToast({ tone: "success", text: "Deleted." });
                    }}
                  >
                    <TrashIcon size={18} />
                  </button>
                </div>
              }
            />
          </div>

          <Section icon={<SparkleIcon size={16} />} title="Buttons" blurb="One primary per screen. Orange only for the app's one live action.">
            <div className="flex flex-wrap items-center gap-2 py-5">
              <button className="btn btn-md btn-primary">Primary</button>
              <button className="btn btn-md btn-record">Record</button>
              <button className="btn btn-md btn-sun">Needs you</button>
              <button className="btn btn-md btn-soft">Soft</button>
              <button className="btn btn-md btn-ghost">Ghost</button>
              <button className="btn btn-md btn-danger-ghost">Delete</button>
              <button className="btn btn-md btn-primary" disabled>
                Disabled
              </button>
            </div>
            <div className="flex flex-wrap items-center gap-2 py-5">
              <button className="btn btn-sm btn-soft">Small soft</button>
              <button className="btn btn-sm btn-ghost">Small ghost</button>
              <CopyButton text="Copied from the specimen" />
              <button className="btn btn-sm btn-soft" onClick={() => setToast({ tone: "success", text: "Saved to your folder." })}>
                Show toast
              </button>
              <button className="btn btn-sm btn-soft" onClick={() => setToast({ tone: "error", text: "The summary didn't come through. Ollama isn't running." })}>
                Show error
              </button>
            </div>
          </Section>

          <Section icon={<SlidersIcon size={16} />} title="Controls" blurb="Rows: a well, a label with a hint, the control on the right." ms={60}>
            <SwitchRow icon={<LeafIcon size={16} />} label="Summarize automatically" hint="Off: the meeting waits for you to press “Summarize”." checked={auto} onChange={setAuto} />
            <SwitchRow icon={<MonitorIcon size={16} />} label="Local only" hint="Nothing leaves this Mac." checked={local} onChange={setLocal} />
            <ControlRow icon={<SignpostIcon size={16} />} label="Speech model" hint="Smaller and faster is fine for drafts.">
              <Select
                label="Speech model"
                value={model}
                onChange={setModel}
                className="w-52"
                options={[
                  { value: "small", label: "Whisper small", hint: "Fast" },
                  { value: "large", label: "Whisper large v3", hint: "Most accurate" },
                ]}
              />
            </ControlRow>
            <ControlRow label="Your name" hint="Used instead of “You” in transcripts.">
              <input className="field w-full sm:w-64" placeholder="e.g. Sam" />
            </ControlRow>
            <ControlRow label="View" hint="Segmented, as tabs.">
              <Segmented
                kind="tab"
                size="sm"
                value={view}
                onChange={setView}
                options={[
                  { id: "summary", label: "Summary" },
                  { id: "transcript", label: "Transcript" },
                  { id: "ask", label: "Ask" },
                ]}
              />
            </ControlRow>
            <div className="py-4">
              <input
                type="range"
                className="range"
                value={pct}
                onChange={(e) => setPct(+e.target.value)}
                style={{ "--pct": `${pct}%` } as CSSProperties}
              />
            </div>
          </Section>

          <Section icon={<CompassIcon size={16} />} title="Status and small pieces" blurb="Each color has one job." ms={120}>
            <div className="flex flex-wrap items-center gap-2 py-5">
              <StatusChip tone="trail" label="Recording" live />
              <StatusChip tone="sun" label="Needs you" />
              <StatusChip tone="sky" label="Transcribing" live />
              <StatusChip tone="forest" label="Done" />
              <StatusChip tone="neutral" label="Queued" />
              <StatusChip tone="trail" label="Failed" />
              <SpeakerChip speaker="You" />
              <SpeakerChip speaker="Them" />
              <span className="inline-flex items-center gap-2 text-ui text-ink-soft">
                <Pulse /> Live
              </span>
              <kbd className="kbd">M</kbd>
              <kbd className="kbd">⌘K</kbd>
            </div>
            <div className="flex items-start gap-3 py-5">
              <div className="flex flex-1 items-start gap-3 rounded-lg border border-trail/20 bg-trail-soft/70 p-4 text-label text-trail-deep">
                <div className="min-w-0">
                  <div className="font-semibold">The summary didn't come through</div>
                  <div className="mt-0.5 opacity-90">Ollama isn't running. Start it, then try again.</div>
                </div>
              </div>
            </div>
            <div className="space-y-3 py-5">
              <Skeleton className="h-3.5 w-56" />
              <Skeleton className="h-9 w-2/3" />
            </div>
          </Section>

          <Section icon={<LeafIcon size={16} />} title="Reading text" blurb="Rendered markdown, in .prose-family." ms={180}>
            <div className="prose-family py-6">
              <h2>
                <span className="well well-forest h-7 w-7">
                  <CompassIcon size={16} />
                </span>
                Overview
              </h2>
              <p>
                The team set the beta launch for <strong>Tuesday</strong>, provided the login fix lands on Monday. See <a href="#">the plan</a>.
              </p>
              <ul>
                <li>Engineering confirmed the beta is ready once the fix is in.</li>
                <li>
                  Docs will be updated before the beta goes out, including <code>config.yml</code>.
                </li>
              </ul>
            </div>
          </Section>

          <div className="inset-surface px-4 py-10 text-center">
            <ContourBadge>
              <CheckSquareIcon size={20} />
            </ContourBadge>
            <p className="mt-3 font-medium">No tasks yet</p>
            <p className="mx-auto mt-1 max-w-sm text-label leading-relaxed text-ink-soft">Action items from your meetings will gather here.</p>
          </div>
        </div>
      </main>
      <TooltipLayer />
      <Toast toast={toast} onClose={() => setToast(null)} />
      {confirmDialog}
    </div>
  );
}
