// Muster's section on the Settings page: whether the first look each day lands on it, and the working hours its plan
// is measured against.
import { Section } from "@core/components/blocks";
import { ClockIcon, SunIcon } from "@core/components/icons";
import { ControlRow, Select, SwitchRow } from "@core/components/ui";
import { useSettings } from "@core/shell";
import { hourMinutes, hourWords } from "./bits";

const HOURS = Array.from({ length: 37 }, (_, i) => {
  const minutes = 5 * 60 + i * 30;
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
});

export function MusterSettings() {
  const { get, save } = useSettings();
  const start = get<string>("muster.day_starts") || "09:00";
  const end = get<string>("muster.day_ends") || "17:00";
  const options = (after?: string) =>
    HOURS.filter((h) => !after || hourMinutes(h) > hourMinutes(after)).map((h) => ({ value: h, label: hourWords(h) }));
  return (
    <Section icon={<SunIcon size={16} />} title="Muster" blurb="The day's kick-off.">
      <SwitchRow
        icon={<SunIcon size={16} />}
        label="Open Muster first"
        hint="The first time you open Traverse each day, it starts on Muster. Off: it opens at Home."
        checked={get<boolean>("muster.open_first") !== false}
        onChange={(v) => void save({ "muster.open_first": v })}
      />
      <ControlRow icon={<ClockIcon size={16} />} label="Working hours" hint="What “Plan the day” measures your picks against." wrap>
        <div className="flex items-center gap-2">
          <Select label="Day starts" size="sm" value={start} options={options()} onChange={(v) => void save({ "muster.day_starts": v })} />
          <span className="text-ui text-ink-soft">to</span>
          <Select label="Day ends" size="sm" value={end} options={options(start)} onChange={(v) => void save({ "muster.day_ends": v })} />
        </div>
      </ControlRow>
    </Section>
  );
}
