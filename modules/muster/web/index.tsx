// Muster's web half: its sidebar entry, its page (wide), its section in Settings, and the start hook that makes it the
// first page of the day.
import { icon } from "@core/components/icons";
import type { ModuleWeb } from "@core/registry";
import { Sunrise } from "lucide-react";
import { musterApi } from "./api";
import { MusterSettings } from "./extras";
import MusterView from "./MusterView";

const SunriseIcon = icon(Sunrise);

const muster: ModuleWeb = {
  id: "muster",
  name: "Muster",
  nav: [{ label: "Muster", icon: <SunriseIcon size={16} className="text-[color:var(--mustard)]" />, path: "muster" }],
  routes: [{ path: "muster", view: MusterView, wide: true }],
  settings: MusterSettings,
  start: musterApi.start,
};

export default muster;
