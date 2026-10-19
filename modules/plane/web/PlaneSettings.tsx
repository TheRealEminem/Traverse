// Settings → Plane: the key, the workspace, which projects to mirror, who you are, and how often to read Plane.
import { useState } from "react";
import { SecretSetting, Section, TextSetting } from "@core/components/blocks";
import { CheckIcon, ClockIcon, CloudIcon, KeyIcon, PersonIcon, icon } from "@core/components/icons";
import { ControlRow, Select, Spinner, Switch } from "@core/components/ui";
import { useLive } from "@core/live";
import { useSettings, useShell } from "@core/shell";
import { Building2, Mountain, PlugZap } from "lucide-react";
import { planeApi } from "./api";
import { plural, since } from "./bits";

const WorkspaceIcon = icon(Building2);
const MountainIcon = icon(Mountain);
const PlugIcon = icon(PlugZap);

const EVERY = [
  { value: "2", label: "Every 2 minutes" },
  { value: "5", label: "Every 5 minutes" },
  { value: "15", label: "Every 15 minutes" },
  { value: "30", label: "Every 30 minutes" },
  { value: "0", label: "Only when I press “Pull now”" },
];

export default function PlaneSettings() {
  const { get, hints, save } = useSettings();
  const { toast } = useShell();
  const { data: status } = useLive(planeApi.status);
  const { data: projects } = useLive(planeApi.projects);
  const { data: members } = useLive(planeApi.members);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);

  const chosen = new Set(get<string[]>("plane.projects") ?? []);
  const toggle = (id: string, on: boolean) => {
    const next = new Set(chosen);
    if (on) next.add(id);
    else next.delete(id);
    void save({ "plane.projects": [...next] });
  };
  const test = async () => {
    setTesting(true);
    setResult(null);
    try {
      setResult({ ok: true, text: (await planeApi.test()).message });
    } catch (e) {
      setResult({ ok: false, text: (e as Error).message });
    } finally {
      setTesting(false);
    }
  };
  const last = status?.last_pull;
  const running = status?.job && ["queued", "running"].includes(status.job.status);
  const keyOwner = status?.me_from_key ? status.me?.name : undefined;

  return (
    <Section icon={<CloudIcon size={16} />} title="Plane" blurb="Your team's Plane workspace. Traverse only reads from Plane: nothing is sent there.">
      <ControlRow
        icon={<KeyIcon size={16} />}
        label="Personal API key"
        hint="In Plane: Profile settings → Personal access tokens. It stays on this Mac and isn't shown again."
        wrap
      >
        <SecretSetting label="Plane API key" hint={hints["plane.personal_api_key"]} onSave={(v) => void save({ "plane.personal_api_key": v })} />
      </ControlRow>
      <ControlRow icon={<WorkspaceIcon size={16} />} label="Workspace" hint="The part after app.plane.so/ in your Plane address." wrap>
        <TextSetting
          label="Plane workspace"
          mono
          placeholder="cold-connect"
          value={get<string>("plane.workspace_slug") ?? ""}
          onSave={(v) => void save({ "plane.workspace_slug": v.replace(/^https?:\/\/[^/]+\//, "").replace(/\/.*$/, "") })}
        />
      </ControlRow>
      <ControlRow icon={<PlugIcon size={16} />} label="Server" hint="Plane Cloud is https://api.plane.so. Change it only for a Plane you host yourselves." wrap>
        <TextSetting
          label="Plane server"
          mono
          placeholder="https://api.plane.so"
          value={get<string>("plane.base_url") ?? ""}
          onSave={(v) => void save({ "plane.base_url": v || "https://api.plane.so" })}
        />
      </ControlRow>
      <div className="py-3.5">
        <ControlRow
          className="!py-0"
          icon={<CheckIcon size={16} />}
          label="Connection"
          hint={
            running
              ? "Reading Plane now…"
              : last
                ? `Read ${since(last.at)} · ${plural(status?.counts.items ?? 0, "item")} from ${plural(last.projects, "project")}`
                : status?.configured
                  ? "Not read yet."
                  : "Add the key and workspace, then test."
          }
          wrap
        >
          <button className="btn btn-sm btn-soft" disabled={testing || !status?.configured} onClick={() => void test()}>
            {testing && <Spinner />}
            Test connection
          </button>
        </ControlRow>
        {result && (
          <p
            role="status"
            className={`mt-3 rounded-lg px-3.5 py-2.5 text-ui ${result.ok ? "bg-forest-soft text-forest-deep" : "border border-trail/20 bg-trail-soft/70 text-trail-deep"}`}
          >
            {result.text}
          </p>
        )}
      </div>
      <div className="py-3.5">
        <ControlRow
          className="!py-0"
          icon={<MountainIcon size={16} />}
          label="Projects to mirror"
          hint={
            projects?.length
              ? `Only these count in Team view. ${plural(chosen.size, "project")} of ${projects.length} chosen.`
              : "Test the connection, and your workspace's projects will be listed here."
          }
        />
        {!!projects?.length && (
          <ul className="mt-3 divide-y divide-line rounded-lg border border-line sm:ml-[46px]">
            {projects.map((p) => (
              <li key={p.id} className="flex items-center justify-between gap-3 px-3.5 py-2.5">
                <label htmlFor={`plane-${p.id}`} className="min-w-0 cursor-pointer">
                  <span className="block truncate text-ui font-medium">{p.name}</span>
                  <span className="block truncate font-mono text-meta text-ink-soft">{p.identifier}</span>
                </label>
                <Switch id={`plane-${p.id}`} label={`Mirror ${p.name}`} checked={chosen.has(p.id)} onChange={(on) => toggle(p.id, on)} />
              </li>
            ))}
          </ul>
        )}
      </div>
      <ControlRow
        icon={<PersonIcon size={16} />}
        label="Which member is you"
        hint="You show as “You” in Team view and in pickers, and items assigned to you there are yours here."
        wrap
      >
        <Select
          label="Which Plane member is you"
          className="w-full sm:w-64"
          value={get<string>("plane.me") ?? ""}
          onChange={(v) => void save({ "plane.me": v })}
          options={[
            { value: "", label: keyOwner ? `${keyOwner} (the key's owner)` : "Whoever the API key belongs to" },
            ...(members ?? []).map((m) => ({ value: m.id, label: m.name, hint: m.email ?? `@${m.display_name}` })),
          ]}
        />
      </ControlRow>
      <ControlRow icon={<ClockIcon size={16} />} label="Read Plane" hint="While Traverse is open. Reading never changes anything in Plane." wrap>
        <Select
          label="How often to read Plane"
          className="w-full sm:w-64"
          value={String(get<number>("plane.pull_minutes") ?? 5)}
          onChange={(v) => {
            void save({ "plane.pull_minutes": Number(v) }).then((ok) => ok && toast("Saved"));
          }}
          options={EVERY}
        />
      </ControlRow>
    </Section>
  );
}
