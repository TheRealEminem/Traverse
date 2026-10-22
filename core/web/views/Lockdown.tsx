// Lockdown (core/server/lockdown.py): one switch that keeps everything on this Mac. Its section in Settings, and the
// sign the app's chrome shows while it's on.
import { useEffect, useRef } from "react";
import { Shield } from "lucide-react";
import { api } from "../api";
import type { LockdownStatus } from "../api";
import { Section } from "../components/blocks";
import { icon } from "../components/icons";
import { SwitchRow } from "../components/ui";
import { useLive } from "../live";
import { useQueryParams } from "../router";
import { useSettings, useShell } from "../shell";

export const ShieldIcon = icon(Shield);

const WHAT_STOPS = [
  "Cloud AI (Claude, OpenAI, Gemini, DeepSeek) stops. AI on this Mac, such as Ollama, keeps working.",
  "Services on the internet aren't read or written: syncs and sends wait.",
  "The Mac app doesn't check for updates.",
  "Work that needs the cloud waits, and goes ahead by itself when you turn Lockdown off.",
];

export function useLockdown() {
  return useLive<LockdownStatus>(api.lockdown).data;
}

function waiting(n: number) {
  return `${n} ${n === 1 ? "thing waits" : "things wait"} for it to be off`;
}

/** The sign in the app's chrome while Lockdown is on: the sidebar's, or a small one for the top bar of a narrow window. */
export function LockdownSign({ compact = false }: { compact?: boolean }) {
  const status = useLockdown();
  if (!status?.on) return null;
  const tip = `Nothing leaves this Mac.${status.parked ? ` ${waiting(status.parked)}.` : ""} Open Settings to turn it off.`;
  if (compact) {
    return (
      <a href="#/settings?section=lockdown" className="chip ml-auto bg-sun-soft text-sun-deep" data-tip={tip}>
        <ShieldIcon size={14} />
        Lockdown
      </a>
    );
  }
  return (
    <a
      href="#/settings?section=lockdown"
      data-tip={tip}
      className="mx-4 mb-4 flex animate-enter items-center gap-2.5 rounded-md border border-sun/30 bg-sun-soft/70 px-3 py-2 text-ui font-medium text-sun-deep transition-colors hover:bg-sun-soft"
    >
      <ShieldIcon size={16} />
      <span className="flex-1">Lockdown is on</span>
      {status.parked > 0 && <span className="text-meta tabular-nums">{status.parked} waiting</span>}
    </a>
  );
}

/** Settings → Lockdown. `shared`: the family link shares it, so it turns on and off in the other family apps too. */
export default function Lockdown({ shared }: { shared: boolean }) {
  const { confirm, toast } = useShell();
  const { values, save } = useSettings();
  const status = useLockdown();
  const [params] = useQueryParams();
  const here = useRef<HTMLDivElement>(null);
  const asked = params.get("section") === "lockdown";
  useEffect(() => {
    if (asked && values) here.current?.scrollIntoView({ block: "start" });
  }, [asked, values]);
  if (!values) return null;
  const on = values["core.lockdown"] === true;
  const parked = status?.parked ?? 0;

  const turn = async (want: boolean) => {
    if (want) {
      const ok = await confirm({
        title: "Turn on Lockdown?",
        body:
          "Nothing will leave this Mac until you turn it off. Cloud AI, update checks and services on the internet stop; AI on " +
          `this Mac keeps working, and work that needs the cloud waits, then goes ahead by itself.${shared ? " It turns on in your other family apps too." : ""}`,
        confirmLabel: "Turn on Lockdown",
        tone: "primary",
      });
      if (!ok) return;
    }
    if ((await save({ "core.lockdown": want })) && !want && parked) toast(`Lockdown is off. ${parked} waiting ${parked === 1 ? "thing goes" : "things go"} ahead now.`);
  };

  return (
    <div ref={here} className="scroll-mt-6">
      <Section
        icon={<ShieldIcon size={16} />}
        title="Lockdown"
        blurb={`One switch that keeps everything on this Mac.${shared ? " Shared with your other family apps." : ""}`}
        delay={60}
      >
        <SwitchRow
          icon={<ShieldIcon size={16} />}
          label="Lockdown"
          hint={
            on ? (
              <>
                On: nothing leaves this Mac until you turn it off.{parked ? ` ${waiting(parked)}.` : ""}
                <ul className="mt-1 list-disc space-y-0.5 pl-4">
                  {WHAT_STOPS.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </>
            ) : (
              "Off: the AI providers and services you've set up are used as usual. On: nothing leaves this Mac, and only AI on this Mac works."
            )
          }
          checked={on}
          onChange={(v) => void turn(v)}
        />
      </Section>
    </div>
  );
}
