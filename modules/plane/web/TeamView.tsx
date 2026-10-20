// #/plane/team: who's on what in Plane, from the read-only mirror. Open items by person, state and project, what's
// past due and what nobody has, and every open item in a table you can search and filter (filters live in the hash).
// Any item, or every item a filter shows, can be brought into Traverse as a linked task (Traverse only; Plane is
// never written to).
import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { Empty, JobStatus } from "@core/components/blocks";
import { CheckIcon, ClockIcon, ExternalIcon, FlagIcon, PlusIcon, RefreshIcon, SearchIcon, UsersIcon, icon } from "@core/components/icons";
import { PageHeader, Segmented, Select, Skeleton, StatusChip, useConfirm } from "@core/components/ui";
import { useLive } from "@core/live";
import { useQueryParams } from "@core/router";
import { useShell } from "@core/shell";
import { CircleDashed, Layers, Mountain } from "lucide-react";
import { planeApi } from "./api";
import type { Team, TeamItem, TeamPerson, TeamProject } from "./api";
import { Due, GROUPS, PersonAvatar, StateBar, StateKey, StateLegend, plural, since } from "./bits";

const MountainIcon = icon(Mountain);
const LayersIcon = icon(Layers);
const NobodyIcon = icon(CircleDashed);

type Show = "all" | "late" | "unassigned";

/** Bringing items into Traverse from the table: says first which Traverse projects it will make, then does it. */
function useBring(team: Team | null, reload: () => void) {
  const { toast } = useShell();
  const [confirm, dialog] = useConfirm();
  const [busy, setBusy] = useState(false);
  const run = async (items: TeamItem[]) => {
    const waiting = items.filter((i) => !i.task);
    if (!waiting.length) return;
    const unlinked = (team?.projects ?? []).filter((p) => !p.linked && waiting.some((i) => i.project_id === p.id));
    if (unlinked.length || waiting.length > 1) {
      const made = unlinked.length
        ? `${unlinked.map((p) => p.name).join(", ")} ${unlinked.length === 1 ? "isn't" : "aren't"} linked to a Traverse project yet, so Traverse will make ${unlinked.length === 1 ? "one" : "one for each"}, named the same (Plane → Linking to choose another). `
        : "";
      const ok = await confirm({
        title: `Bring ${waiting.length === 1 ? waiting[0].key : plural(waiting.length, "item")} into Traverse?`,
        body: `${waiting.length > 1 ? "Each becomes a task in Traverse that follows its Plane item. " : ""}${made}Nothing changes in Plane.`,
        confirmLabel: "Bring in",
        tone: "primary",
      });
      if (!ok) return;
    }
    setBusy(true);
    try {
      const r = await planeApi.bring({ items: waiting.map((i) => i.id) });
      const brought = r.brought ? `Brought ${plural(r.brought, "item")} into Traverse.` : "Nothing new to bring in.";
      toast(r.new_projects.length ? `${brought} Made ${r.new_projects.join(", ")}.` : brought, "success");
      reload();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  };
  return { run, busy, dialog };
}

export default function TeamView() {
  const { data: team, error, reload } = useLive(planeApi.team);
  const bring = useBring(team ?? null, () => void reload());
  const [params, setParams] = useQueryParams();
  const filters = {
    person: params.get("person") ?? "",
    project: params.get("project") ?? "",
    show: (params.get("show") as Show) || "all",
    q: params.get("q") ?? "",
  };

  const itemsRef = useRef<HTMLDivElement>(null);
  /** A filter chosen from the cards above the table: apply it, and bring the table into view if it's off screen. */
  const pick = (changes: Record<string, string | null>) => {
    setParams(changes);
    const el = itemsRef.current;
    if (el && Object.values(changes).some(Boolean) && el.getBoundingClientRect().top > window.innerHeight - 120) {
      const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      el.scrollIntoView({ behavior: calm ? "auto" : "smooth", block: "start" });
    }
  };

  if (error && !team) {
    return (
      <>
        <PageHeader title="Team" />
        <div className="rounded-lg border border-trail/20 bg-trail-soft/70 p-4 text-label text-trail-deep">
          <div className="font-semibold">The team didn't load</div>
          <div className="mt-0.5 opacity-90">{error}</div>
        </div>
      </>
    );
  }
  if (!team) return <Loading />;
  if (!team.configured || !team.projects_chosen) return <NotSetUp team={team} />;

  const pulling = team.job && ["queued", "running"].includes(team.job.status);
  if (!team.pulled_at && pulling) return <Loading job={team.job} />;

  return (
    <>
      <Header team={team} />
      {team.job && team.job.status !== "done" && (
        <div className="-mt-4 mb-6">
          <JobStatus job={team.job} />
        </div>
      )}
      <Totals team={team} show={filters.show} onShow={(show) => setParams({ show: show === "all" ? null : show })} />
      <People team={team} selected={filters.person} onPick={(person) => pick({ person: person === filters.person ? null : person })} />
      <div className="mb-10 grid gap-x-6 gap-y-10 xl:grid-cols-[minmax(0,5fr)_minmax(0,8fr)]">
        <ByState team={team} />
        <ByProject team={team} selected={filters.project} onPick={(project) => pick({ project: project === filters.project ? null : project })} />
      </div>
      <div ref={itemsRef} className="scroll-mt-20">
        <Items team={team} filters={filters} setParams={setParams} onBring={(items) => void bring.run(items)} busy={bring.busy} />
      </div>
      {bring.dialog}
    </>
  );
}

// ── The page's top ─────────────────────────────────────────────────────

function Header({ team }: { team: Team }) {
  const { toast } = useShell();
  const [busy, setBusy] = useState(false);
  const running = team.job && ["queued", "running"].includes(team.job.status);
  const pull = async () => {
    setBusy(true);
    try {
      await planeApi.pull();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  };
  const projects = team.projects.length;
  return (
    <PageHeader
      title="Team"
      subtitle={
        <>
          {plural(team.totals.open, "open item")} in {plural(projects, "project")} · read from Plane{" "}
          <span data-tip={team.pulled_at ? new Date(team.pulled_at).toLocaleString() : undefined}>{since(team.pulled_at)}</span>
        </>
      }
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <a className="btn btn-md btn-ghost" href={`${team.web_url}/${team.workspace}/`} target="_blank" rel="noreferrer">
            <ExternalIcon size={18} />
            Open Plane
          </a>
          <button className="btn btn-md btn-soft" onClick={() => void pull()} disabled={busy || !!running}>
            <RefreshIcon size={18} className={running ? "animate-spin" : ""} />
            {running ? "Reading Plane…" : "Pull now"}
          </button>
        </div>
      }
    />
  );
}

function Totals({ team, show, onShow }: { team: Team; show: Show; onShow: (s: Show) => void }) {
  const t = team.totals;
  const tiles: { id: Show | null; label: string; value: number; hint: ReactNode; tone?: "trail" | "sun" }[] = [
    { id: "all", label: "Open", value: t.open, hint: <>{plural(t.in_progress, "item")} in progress</> },
    { id: null, label: "Due this week", value: t.due_soon, hint: "In the next 7 days", tone: t.due_soon ? "sun" : undefined },
    { id: "late", label: "Past due", value: t.past_due, hint: t.past_due ? "Show them below" : "Nothing late", tone: t.past_due ? "trail" : undefined },
    { id: "unassigned", label: "No one on it", value: t.unassigned, hint: t.unassigned ? "Show them below" : "Everything has someone" },
  ];
  return (
    <div className="mb-10 grid animate-enter grid-cols-2 gap-3 lg:grid-cols-4">
      {tiles.map((tile) => {
        const inner = (
          <>
            <span className="flex items-center gap-1.5 text-meta font-medium text-ink-soft">
              {tile.tone && <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${tile.tone === "trail" ? "bg-trail" : "bg-sun"}`} />}
              {tile.label}
            </span>
            <span className="mt-1 block text-[28px] font-semibold leading-none tracking-[-0.02em] tabular-nums text-ink">{tile.value}</span>
            <span className="mt-2 block truncate text-hint text-ink-soft">{tile.hint}</span>
          </>
        );
        const pressed = tile.id !== null && tile.id !== "all" && show === tile.id;
        return tile.id && tile.id !== "all" && tile.value ? (
          <button
            key={tile.label}
            aria-pressed={pressed}
            onClick={() => onShow(pressed ? "all" : (tile.id as Show))}
            className={`panel px-4 py-3.5 text-left transition-[transform,box-shadow,border-color] duration-fast hover:-translate-y-px hover:shadow-md ${
              pressed ? "border-forest/50 ring-2 ring-forest/15" : ""
            }`}
          >
            {inner}
          </button>
        ) : (
          <div key={tile.label} className="panel px-4 py-3.5">
            {inner}
          </div>
        );
      })}
    </div>
  );
}

function SectionHead({ icon: glyph, title, blurb, aside }: { icon: ReactNode; title: string; blurb: string; aside?: ReactNode }) {
  return (
    <div className="mb-3 flex flex-wrap items-end justify-between gap-x-4 gap-y-2 px-1">
      <div className="flex min-w-0 items-start gap-3">
        <span className="well well-forest">{glyph}</span>
        <div className="min-w-0">
          <h2 className="text-heading font-semibold tracking-[-0.01em]">{title}</h2>
          <p className="mt-0.5 text-ui leading-snug text-ink-soft">{blurb}</p>
        </div>
      </div>
      {aside}
    </div>
  );
}

// ── People ─────────────────────────────────────────────────────────────

function People({ team, selected, onPick }: { team: Team; selected: string; onPick: (id: string) => void }) {
  const busiest = Math.max(1, ...team.people.map((p) => p.open));
  const names = new Map(team.projects.map((p) => [p.id, p.name]));
  return (
    <section className="mb-10 animate-enter" style={{ animationDelay: "60ms" } as CSSProperties}>
      <SectionHead
        icon={<UsersIcon size={16} />}
        title="People"
        blurb="Open items for each person, split by state. Bars share one scale."
        aside={<StateKey triage={team.states.some((s) => s.group === "triage")} />}
      />
      <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(250px,1fr))]">
        {team.people.map((p) => (
          <PersonCard key={p.id ?? "none"} person={p} busiest={busiest} names={names} selected={selected === (p.id ?? "none")} onPick={onPick} />
        ))}
      </div>
    </section>
  );
}

function PersonCard({
  person: p,
  busiest,
  names,
  selected,
  onPick,
}: {
  person: TeamPerson;
  busiest: number;
  names: Map<string, string>;
  selected: boolean;
  onPick: (id: string) => void;
}) {
  const top = Object.entries(p.projects)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  const none = p.id === null;
  return (
    <button
      aria-pressed={selected}
      onClick={() => onPick(p.id ?? "none")}
      className={`panel flex flex-col px-4 pb-3.5 pt-4 text-left transition-[transform,box-shadow,border-color] duration-fast hover:-translate-y-px hover:shadow-md ${
        selected ? "border-forest/50 ring-2 ring-forest/15" : ""
      }`}
    >
      <span className="flex w-full items-center gap-3">
        <PersonAvatar name={p.name} me={p.is_me} none={none} size={36} />
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5">
            <span className="truncate text-label font-medium">{p.name}</span>
            {p.is_me && <span className="chip bg-sky-soft text-sky-deep">You</span>}
          </span>
          <span className="block truncate text-hint text-ink-soft">{none ? "Open items nobody has" : p.display_name ? `@${p.display_name}` : "In Plane"}</span>
        </span>
        <span className="text-right">
          <span className="block text-[22px] font-semibold leading-none tabular-nums">{p.open}</span>
          <span className="text-meta text-ink-soft">open</span>
        </span>
      </span>
      <span className="mt-4 block w-full">
        <StateBar split={p.by_group} scale={busiest} label={`${p.name}'s open items`} />
      </span>
      <span className="mt-2 block">
        <StateLegend split={p.by_group} />
      </span>
      <span className="mt-3 flex min-h-5 flex-wrap gap-1.5">
        {p.past_due > 0 && <StatusChip tone="trail" label={`${p.past_due} past due`} />}
        {p.due_soon > 0 && <StatusChip tone="sun" label={`${p.due_soon} due this week`} />}
      </span>
      {top.length > 0 && (
        <span className="mt-3 block w-full space-y-1 border-t border-line pt-3">
          {top.map(([pid, n]) => (
            <span key={pid} className="flex items-center justify-between gap-3 text-hint">
              <span className="truncate text-ink-soft">{names.get(pid) ?? "A project"}</span>
              <span className="tabular-nums text-ink">{n}</span>
            </span>
          ))}
          {Object.keys(p.projects).length > 3 && (
            <span className="block text-meta text-ink-soft">and {plural(Object.keys(p.projects).length - 3, "more project")}</span>
          )}
        </span>
      )}
    </button>
  );
}

// ── By state and by project ────────────────────────────────────────────

function ByState({ team }: { team: Team }) {
  const most = Math.max(1, ...team.states.map((s) => s.open));
  return (
    <section className="min-w-0 animate-enter" style={{ animationDelay: "120ms" } as CSSProperties}>
      <SectionHead icon={<LayersIcon size={16} />} title="By state" blurb="Where the open work sits, across everyone." />
      <div className="panel divide-y divide-line px-5">
        {team.states.map((s) => {
          const g = GROUPS.find((x) => x.id === s.group)!;
          return (
            <div key={s.group} className="flex items-center gap-3 py-3.5">
              <span className="w-24 shrink-0 text-label font-medium">{s.label}</span>
              <span className="h-2 min-w-0 flex-1 rounded-full bg-surface-subtle">
                <span data-tip={`${s.open} ${s.label.toLowerCase()}`} className={`block h-2 rounded-full ${g.swatch}`} style={{ width: `${(s.open / most) * 100}%` }} />
              </span>
              <span className="w-8 shrink-0 text-right text-label tabular-nums">{s.open}</span>
            </div>
          );
        })}
        <div className="flex items-center justify-between py-3 text-hint text-ink-soft">
          <span>Open</span>
          <span className="tabular-nums">{team.totals.open}</span>
        </div>
      </div>
    </section>
  );
}

function ByProject({ team, selected, onPick }: { team: Team; selected: string; onPick: (id: string) => void }) {
  const busiest = Math.max(1, ...team.projects.map((p) => p.open));
  return (
    <section className="min-w-0 animate-enter" style={{ animationDelay: "180ms" } as CSSProperties}>
      <SectionHead icon={<MountainIcon size={16} />} title="By project" blurb="Open items in each mirrored project. Pick one to see its items." />
      <div className="panel divide-y divide-line overflow-hidden">
        {team.projects.map((p) => (
          <ProjectRow key={p.id} project={p} busiest={busiest} selected={selected === p.id} onPick={onPick} />
        ))}
      </div>
    </section>
  );
}

function ProjectRow({ project: p, busiest, selected, onPick }: { project: TeamProject; busiest: number; selected: boolean; onPick: (id: string) => void }) {
  return (
    <button
      aria-pressed={selected}
      onClick={() => onPick(p.id)}
      className={`flex w-full flex-wrap items-center gap-x-3 gap-y-2 px-5 py-3 text-left transition-colors ${
        selected ? "bg-forest/[.07]" : "hover:bg-forest/[.05]"
      }`}
    >
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-sm bg-surface-subtle font-mono text-caption font-medium text-ink-soft">
        {p.identifier.slice(0, 2)}
      </span>
      <span className="min-w-0 flex-1 sm:w-44 sm:flex-none">
        <span className="block truncate text-label font-medium">{p.name}</span>
        <span className="block truncate font-mono text-meta text-ink-soft">{p.identifier}</span>
      </span>
      <span className="order-last w-full min-w-0 sm:order-none sm:w-auto sm:flex-1">
        <StateBar split={p.by_group} scale={busiest} label={`${p.name}: open items`} height={6} />
        <span className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-meta text-ink-soft">
          <StateLegend split={p.by_group} />
          {p.past_due > 0 && <span className="text-trail-deep">{p.past_due} past due</span>}
          {p.unassigned > 0 && <span>{p.unassigned} with no one</span>}
        </span>
      </span>
      <span className="w-10 shrink-0 text-right">
        <span className="block text-heading font-semibold leading-none tabular-nums">{p.open}</span>
        <span className="text-meta text-ink-soft">open</span>
      </span>
    </button>
  );
}

// ── Every open item ────────────────────────────────────────────────────

const PRIORITY: Record<string, { label: string; tone: "sun" | "neutral" } | undefined> = {
  urgent: { label: "Urgent", tone: "sun" },
  high: { label: "High", tone: "neutral" },
};
const STATE_TONE = { triage: "sun", backlog: "neutral", unstarted: "neutral", started: "sky" } as const;

function Items({
  team,
  filters,
  setParams,
  onBring,
  busy,
}: {
  team: Team;
  filters: { person: string; project: string; show: Show; q: string };
  setParams: (changes: Record<string, string | null>) => void;
  onBring: (items: TeamItem[]) => void;
  busy: boolean;
}) {
  const [q, setQ] = useState(filters.q);
  // The search lives in the hash too, so a link or Back can change it under the field.
  useEffect(() => {
    setQ((typed) => (typed.trim() === filters.q ? typed : filters.q));
  }, [filters.q]);
  const words = q.trim().toLowerCase();
  const base = useMemo(
    () =>
      team.items.filter((i) => {
        if (filters.person === "none" ? i.assignees.length : filters.person && !i.assignees.some((a) => a.id === filters.person)) return false;
        if (filters.project && i.project_id !== filters.project) return false;
        if (words && !`${i.key} ${i.name} ${i.project} ${i.labels.join(" ")} ${i.cycle ?? ""}`.toLowerCase().includes(words)) return false;
        return true;
      }),
    [team.items, filters.person, filters.project, words],
  );
  const late = base.filter((i) => i.past_due).length;
  const nobody = base.filter((i) => !i.assignees.length).length;
  const shown = filters.show === "late" ? base.filter((i) => i.past_due) : filters.show === "unassigned" ? base.filter((i) => !i.assignees.length) : base;
  const filtered = !!(filters.person || filters.project || words || filters.show !== "all");
  const notIn = shown.filter((i) => !i.task);
  const me = team.people.find((p) => p.is_me);
  const onlyMine = !!me && filters.person === me.id && !filters.project && !words && filters.show === "all";

  const people = [
    { value: "", label: "Everyone" },
    ...team.people.filter((p) => p.id).map((p) => ({ value: p.id!, label: p.is_me ? `${p.name} (you)` : p.name, hint: plural(p.open, "open item") })),
    { value: "none", label: "No one", hint: "Items nobody has" },
  ];
  const projects = [{ value: "", label: "All projects" }, ...team.projects.map((p) => ({ value: p.id, label: p.name, hint: p.identifier }))];

  return (
    <section className="animate-enter" style={{ animationDelay: "240ms" } as CSSProperties}>
      <SectionHead
        icon={<FlagIcon size={16} />}
        title="Open items"
        blurb="Past due first. Each one opens in Plane; bring one into Traverse to work on it there."
        aside={
          notIn.length > 0 && (
            <button className="btn btn-sm btn-soft" disabled={busy} onClick={() => onBring(notIn)}>
              <PlusIcon size={16} />
              {onlyMine
                ? `Bring in everything assigned to you (${notIn.length})`
                : filtered
                  ? `Bring these ${notIn.length} into Traverse`
                  : `Bring all ${notIn.length} into Traverse`}
            </button>
          )
        }
      />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <label className="relative min-w-0 flex-1 basis-full sm:basis-56">
          <SearchIcon size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
          <input
            className="field w-full pl-9"
            aria-label="Search open items"
            placeholder="Search by name, key or label"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setParams({ q: e.target.value.trim() || null });
            }}
          />
        </label>
        <Select label="Person" value={filters.person} onChange={(v) => setParams({ person: v || null })} options={people} className="w-[calc(50%-4px)] sm:w-48" />
        <Select label="Project" value={filters.project} onChange={(v) => setParams({ project: v || null })} options={projects} className="w-[calc(50%-4px)] sm:w-48" />
      </div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <Segmented<Show>
          label="Which items"
          size="sm"
          value={filters.show}
          onChange={(v) => setParams({ show: v === "all" ? null : v })}
          options={[
            { id: "all", label: <>All <Count n={base.length} /></> },
            { id: "late", label: <>Past due <Count n={late} /></>, icon: <ClockIcon size={14} /> },
            { id: "unassigned", label: <>No one <Count n={nobody} /></>, icon: <NobodyIcon size={14} /> },
          ]}
        />
        <span className="flex items-center gap-2 text-meta text-ink-soft">
          {filtered ? `${shown.length} of ${team.items.length}` : plural(team.items.length, "item")}
          {filtered && (
            <button
              className="btn btn-sm btn-ghost"
              onClick={() => {
                setQ("");
                setParams({ person: null, project: null, show: null, q: null });
              }}
            >
              Clear filters
            </button>
          )}
        </span>
      </div>
      {shown.length === 0 ? (
        <div className="inset-surface px-4 py-10 text-center">
          <p className="font-medium">Nothing open matches</p>
          <p className="mx-auto mt-1 max-w-sm text-ui text-ink-soft">Try another person or project, or clear the filters.</p>
        </div>
      ) : (
        <div className="panel overflow-hidden">
          <div className="hidden items-center border-b border-line pr-5 text-meta font-medium text-ink-soft md:flex">
            <div className="grid flex-1 grid-cols-[6.5rem_minmax(0,1fr)_8rem_10rem_7.5rem_1rem] gap-3 px-5 py-2.5">
              <span>Key</span>
              <span>Item</span>
              <span>State</span>
              <span>Who</span>
              <span>Due</span>
              <span />
            </div>
            <span className="w-[6.75rem] shrink-0">In Traverse</span>
          </div>
          <ul className="divide-y divide-line">
            {shown.map((i) => (
              <ItemRow key={i.id} item={i} onBring={() => onBring([i])} busy={busy} />
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Count({ n }: { n: number }) {
  return <span className="ml-0.5 tabular-nums text-ink-soft">{n}</span>;
}

function ItemRow({ item: i, onBring, busy }: { item: TeamItem; onBring: () => void; busy: boolean }) {
  const priority = PRIORITY[i.priority];
  const meta = [i.project, i.cycle, ...i.labels.map((l) => `#${l}`)].filter(Boolean).join(" · ");
  return (
    <li className="flex flex-col transition-colors hover:bg-forest/[.05] md:flex-row md:items-center md:pr-5">
      <a
        href={i.url}
        target="_blank"
        rel="noreferrer"
        aria-label={`${i.key} ${i.name}, opens in Plane`}
        className="group grid min-w-0 flex-1 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1.5 px-5 py-3 md:grid-cols-[6.5rem_minmax(0,1fr)_8rem_10rem_7.5rem_1rem]"
      >
        <span className="font-mono text-meta text-ink-soft md:order-none">{i.key}</span>
        <span className="justify-self-end md:hidden">
          <StatusChip tone={STATE_TONE[i.state.group]} label={i.state.name} />
        </span>
        <span className="col-span-2 min-w-0 md:col-span-1">
          <span className="flex items-center gap-2">
            <span className="truncate text-label font-medium">{i.name}</span>
            {priority && <StatusChip tone={priority.tone} label={priority.label} />}
          </span>
          <span className="block truncate text-hint text-ink-soft">{meta}</span>
        </span>
        <span className="hidden md:block">
          <StatusChip tone={STATE_TONE[i.state.group]} label={i.state.name} />
        </span>
        <span className="flex min-w-0 items-center gap-2">
          {i.assignees.length ? (
            <>
              <span className="flex -space-x-1.5">
                {i.assignees.slice(0, 3).map((a) => (
                  <span key={a.id} className="rounded-full ring-2 ring-[var(--surface-solid)]">
                    <PersonAvatar name={a.name} me={a.is_me} size={22} />
                  </span>
                ))}
              </span>
              <span className="truncate text-hint text-ink-soft">
                {i.assignees.length === 1 ? (i.assignees[0].is_me ? "You" : i.assignees[0].name.split(" ")[0]) : plural(i.assignees.length, "person", "people")}
              </span>
            </>
          ) : (
            <>
              <PersonAvatar name="" none size={22} />
              <span className="text-hint text-ink-soft">No one</span>
            </>
          )}
        </span>
        <span className="justify-self-end md:justify-self-start">
          <Due date={i.target_date} late={i.past_due} soon={i.due_soon} />
        </span>
        <ExternalIcon size={14} className="hidden text-ink-faint transition-colors group-hover:text-ink-soft md:block" />
      </a>
      <span className="-mt-1.5 flex w-full shrink-0 px-5 pb-3 md:mt-0 md:w-[6.75rem] md:px-0 md:pb-0">
        {i.task ? (
          <a href={i.task.href} className="btn btn-sm btn-ghost -ml-2.5 text-forest-deep" data-tip={`Open "${i.task.title}" in Traverse`}>
            <CheckIcon size={15} /> In Traverse
          </a>
        ) : (
          <button className="btn btn-sm btn-soft" disabled={busy} onClick={onBring} aria-label={`Bring ${i.key} into Traverse`}>
            <PlusIcon size={15} /> Bring in
          </button>
        )}
      </span>
    </li>
  );
}

// ── Before there's anything to show ────────────────────────────────────

function Loading({ job }: { job?: Team["job"] }) {
  return (
    <>
      <PageHeader title="Team" subtitle={job ? "Reading your Plane workspace for the first time…" : undefined} />
      {job && (
        <div className="-mt-4 mb-6">
          <JobStatus job={job} />
        </div>
      )}
      <div className="mb-10 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[0, 1, 2, 3].map((n) => (
          <Skeleton key={n} className="h-[92px] rounded-xl" />
        ))}
      </div>
      <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(250px,1fr))]">
        {[0, 1, 2].map((n) => (
          <Skeleton key={n} className="h-52 rounded-xl" />
        ))}
      </div>
    </>
  );
}

function NotSetUp({ team }: { team: Team }) {
  return (
    <>
      <PageHeader title="Team" subtitle="Who's on what in your team's Plane workspace." />
      <Empty icon={<UsersIcon size={20} />} title={team.configured ? "Choose which projects to mirror" : "Connect Plane to see your team"}>
        {team.configured
          ? "Pick the Plane projects that count in Settings → Plane, and their open items will appear here by person, state and project."
          : "Paste your Plane API key and workspace in Settings → Plane. Traverse only reads from Plane: nothing is sent there."}
      </Empty>
      <div className="mt-4 flex justify-center">
        <a className="btn btn-md btn-primary" href="#/settings">
          Open Settings
        </a>
      </div>
    </>
  );
}
