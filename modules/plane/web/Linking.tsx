// #/plane/links: which Traverse project each mirrored Plane project goes to, what its states mean there, and
// bringing Plane items into Traverse as linked tasks (yours, or a project's). All of it changes only Traverse:
// nothing is sent to Plane. ?project=<id> points at one project (where a link to a Plane project opens).
import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { Empty } from "@core/components/blocks";
import { NetworkIcon, PlusIcon } from "@core/components/icons";
import { PageHeader, Select, Skeleton, StatusChip, useConfirm } from "@core/components/ui";
import { useLive } from "@core/live";
import { useQueryParams } from "@core/router";
import { useShell } from "@core/shell";
import { planeApi } from "./api";
import type { Brought, LinkedProject, Links, Status } from "./api";
import { plural } from "./bits";

const GROUP_LABEL: Record<string, string> = {
  triage: "Triage",
  backlog: "Backlog",
  unstarted: "To do",
  started: "In progress",
  completed: "Done",
  cancelled: "Cancelled",
};

/** What a bring-in did, as one sentence. */
function broughtWords(r: Brought): string {
  const parts = [r.brought ? `Brought ${plural(r.brought, "item")} into Traverse.` : "Nothing new to bring in."];
  if (r.new_projects.length) parts.push(`Made ${plural(r.new_projects.length, "project")} for them: ${r.new_projects.join(", ")}.`);
  if (r.already) parts.push(`${plural(r.already, "item was", "items were")} in Traverse already.`);
  return parts.join(" ");
}

/** Bringing items in: says first which Traverse projects it will make, then does it. */
function useBring(links: Links | null, reload: () => void) {
  const { toast } = useShell();
  const [confirm, dialog] = useConfirm();
  const [busy, setBusy] = useState(false);
  const run = async (body: { items: string[] } | { mine: true }, items: string[]) => {
    const unlinked = (links?.projects ?? []).filter((p) => !p.link && p.open_waiting.some((id) => items.includes(id)));
    if (unlinked.length) {
      const ok = await confirm({
        title: `Bring in ${plural(items.length, "item")}?`,
        body:
          `${unlinked.map((p) => p.name).join(", ")} ${unlinked.length === 1 ? "isn't" : "aren't"} linked to a Traverse project yet, ` +
          `so Traverse will make ${unlinked.length === 1 ? "one" : "one for each"}, named the same. You can link ${unlinked.length === 1 ? "it" : "them"} ` +
          `to other projects instead first. Nothing changes in Plane.`,
        confirmLabel: "Bring them in",
        tone: "primary",
      });
      if (!ok) return;
    }
    setBusy(true);
    try {
      toast(broughtWords(await planeApi.bring(body)), "success");
      reload();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  };
  return { run, busy, dialog };
}

export default function Linking() {
  const { data: links, error, reload } = useLive(planeApi.links);
  const { data: mine } = useLive(planeApi.traverseProjects);
  const [params] = useQueryParams();
  const focus = params.get("project");
  const bring = useBring(links ?? null, () => void reload());

  useEffect(() => {
    if (focus && links) document.getElementById(`plane-project-${focus}`)?.scrollIntoView({ block: "center" });
  }, [focus, !!links]); // eslint-disable-line react-hooks/exhaustive-deps

  const header = (
    <PageHeader
      title="Linking"
      subtitle="Which Traverse project each Plane project goes to, and what its states mean here. Linking and bringing items in change only Traverse."
    />
  );
  if (error && !links) {
    return (
      <>
        {header}
        <div className="rounded-lg border border-trail/20 bg-trail-soft/70 p-4 text-label text-trail-deep">{error}</div>
      </>
    );
  }
  if (!links) {
    return (
      <>
        {header}
        <Skeleton className="mb-6 h-24 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </>
    );
  }
  if (!links.projects.length) {
    return (
      <>
        {header}
        <Empty icon={<NetworkIcon size={20} />} title="Choose which Plane projects to read">
          Pick the projects in Settings → Plane. Once they're read, you can link each one to a Traverse project here.
        </Empty>
        <div className="mt-4 flex justify-center">
          <a className="btn btn-md btn-primary" href="#/settings">
            Open Settings
          </a>
        </div>
      </>
    );
  }

  const taken = new Set(links.projects.map((p) => p.link?.local_ref).filter(Boolean));
  const choices = (mine ?? []).filter((p) => !p.archived && !taken.has(`tasks:${p.id}`));
  const waiting = links.mine_waiting.length;

  return (
    <>
      {header}
      <section className="panel mb-10 flex animate-enter flex-wrap items-center gap-x-6 gap-y-3 px-5 py-4">
        <div className="min-w-0 flex-1">
          <div className="text-label font-semibold">Everything assigned to you</div>
          <p className="mt-0.5 text-ui text-ink-soft">
            {plural(links.mine, "open item")} in Plane are yours.{" "}
            {waiting ? `${waiting} of them ${waiting === 1 ? "isn't" : "aren't"} in Traverse yet.` : links.mine ? "All of them are in Traverse." : ""}
          </p>
        </div>
        {waiting > 0 ? (
          <button className="btn btn-md btn-primary" disabled={bring.busy} onClick={() => void bring.run({ mine: true }, links.mine_waiting)}>
            <PlusIcon size={18} /> Bring in your {waiting}
          </button>
        ) : (
          links.mine > 0 && (
            <a className="btn btn-md btn-soft" href="#/tasks">
              Open My tasks
            </a>
          )
        )}
      </section>
      <div className="flex flex-col gap-4">
        {links.projects.map((p, n) => (
          <ProjectLink
            key={p.id}
            project={p}
            statuses={links.statuses}
            choices={choices}
            focused={focus === p.id}
            delay={n}
            busy={bring.busy}
            onBring={(items) => void bring.run({ items }, items)}
            onChanged={() => void reload()}
          />
        ))}
      </div>
      {bring.dialog}
    </>
  );
}

function ProjectLink({
  project: p,
  statuses,
  choices,
  focused,
  delay,
  busy,
  onBring,
  onChanged,
}: {
  project: LinkedProject;
  statuses: Links["statuses"];
  choices: { id: string; name: string }[];
  focused: boolean;
  delay: number;
  busy: boolean;
  onBring: (items: string[]) => void;
  onChanged: () => void;
}) {
  const { toast } = useShell();
  const [confirm, dialog] = useConfirm();
  const [working, setWorking] = useState(false);
  const act = async (work: () => Promise<unknown>, done?: string) => {
    setWorking(true);
    try {
      await work();
      if (done) toast(done, "success");
      onChanged();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setWorking(false);
    }
  };
  const unlink = async () => {
    const ok = await confirm({
      title: `Unlink ${p.name}?`,
      body: `${p.link?.title ?? "The Traverse project"} and its tasks stay, and tasks you brought in keep following their Plane items. New items you bring in from ${p.name} will go into a new project.`,
      confirmLabel: "Unlink",
    });
    if (ok) void act(() => planeApi.unlink(p.id));
  };
  const stateOptions = p.states.map((s) => ({
    value: s.id,
    label: s.name,
    hint: GROUP_LABEL[s.group] ?? s.group,
  }));

  return (
    <>
      <section
        id={`plane-project-${p.id}`}
        aria-label={p.name}
        className={`panel animate-enter scroll-mt-24 px-5 py-4 ${focused ? "border-forest/50 ring-2 ring-forest/15" : ""}`}
        style={{ animationDelay: `${Math.min(delay, 8) * 40}ms` } as CSSProperties}
      >
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-sm bg-surface-subtle font-mono text-caption font-medium text-ink-soft">
            {p.identifier.slice(0, 2)}
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-heading font-semibold tracking-[-0.01em]">{p.name}</h2>
            <p className="text-meta text-ink-soft">
              <span className="font-mono">{p.identifier}</span> · {plural(p.open, "open item")} · {p.mine} yours · {p.in_traverse} in Traverse
            </p>
          </div>
          {p.link ? <StatusChip tone="forest" label="Linked" /> : <StatusChip tone="neutral" label="Not linked" />}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-4">
          {p.link ? (
            <>
              <span className="text-ui text-ink-soft">Goes to</span>
              {p.link.href ? (
                <a href={p.link.href} className="inline-flex items-center gap-1 text-label font-medium hover:text-forest">
                  <NetworkIcon size={15} className="text-forest" />
                  {p.link.title}
                </a>
              ) : (
                <span className="text-label text-ink-soft">a project that's gone</span>
              )}
              <button className="btn btn-sm btn-ghost ml-auto" disabled={working} onClick={() => void unlink()}>
                Unlink
              </button>
            </>
          ) : (
            <>
              <button
                className="btn btn-sm btn-soft"
                disabled={working}
                onClick={() => void act(() => planeApi.link(p.id), `Made ${p.name} in Traverse and linked it.`)}
              >
                <PlusIcon size={16} /> Make a Traverse project
              </button>
              {choices.length > 0 && (
                <Select
                  label={`Link ${p.name} to a Traverse project`}
                  size="sm"
                  className="w-full sm:w-64"
                  value=""
                  disabled={working}
                  options={[{ value: "", label: "Or link one you have…" }, ...choices.map((c) => ({ value: c.id, label: c.name }))]}
                  onChange={(v) => v && void act(() => planeApi.link(p.id, `tasks:${v}`), `Linked ${p.name}.`)}
                />
              )}
            </>
          )}
        </div>

        {p.link && (
          <div className="mt-4">
            <h3 className="eyebrow mb-1 px-0.5">What its states mean</h3>
            <p className="mb-3 px-0.5 text-hint text-ink-soft">
              A linked task's status follows its Plane item's state. An item in the state you pick for a status shows as that status.
            </p>
            <div className="grid gap-x-6 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
              {statuses.map((s) => {
                const chosen = p.link!.state_map[s.value as Status] ?? "";
                const preset = p.preset[s.value as Status];
                const presetName = p.states.find((x) => x.id === preset)?.name;
                return (
                  <label key={s.value} className="flex min-w-0 items-center gap-3">
                    <span className="w-16 shrink-0 text-label">{s.label}</span>
                    <Select
                      label={`${s.label} in ${p.name}`}
                      size="sm"
                      className="min-w-0 flex-1"
                      value={chosen}
                      disabled={working || !stateOptions.length}
                      options={chosen ? stateOptions : [{ value: "", label: "No state in this group" }, ...stateOptions]}
                      onChange={(v) => v && v !== chosen && void act(() => planeApi.mapStates(p.id, { [s.value]: v }))}
                    />
                    {chosen && preset && chosen !== preset && (
                      <button
                        type="button"
                        className="btn btn-sm btn-ghost shrink-0 px-2"
                        data-tip={`Back to ${presetName}`}
                        onClick={() => void act(() => planeApi.mapStates(p.id, { [s.value]: preset }))}
                      >
                        Reset
                      </button>
                    )}
                  </label>
                );
              })}
            </div>
          </div>
        )}

        {(p.mine_waiting.length > 0 || p.open_waiting.length > 0) && (
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-4">
            <span className="mr-auto text-ui text-ink-soft">
              {plural(p.open_waiting.length, "open item")} not in Traverse yet
              {p.mine_waiting.length ? `, ${p.mine_waiting.length} of them yours` : ""}.
            </span>
            {p.mine_waiting.length > 0 && (
              <button className="btn btn-sm btn-soft" disabled={busy} onClick={() => onBring(p.mine_waiting)}>
                Bring in yours ({p.mine_waiting.length})
              </button>
            )}
            {p.open_waiting.length > p.mine_waiting.length && (
              <button className="btn btn-sm btn-ghost" disabled={busy} onClick={() => onBring(p.open_waiting)}>
                Bring in all {p.open_waiting.length}
              </button>
            )}
            <a className="btn btn-sm btn-ghost" href={`#/plane/team?project=${p.id}`}>
              See them
            </a>
          </div>
        )}
      </section>
      {dialog}
    </>
  );
}
