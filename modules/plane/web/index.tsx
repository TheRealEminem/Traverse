// The plane module's web half: the Team view, Linking, and its section in Settings.
import { NetworkIcon, UsersIcon } from "@core/components/icons";
import type { ModuleWeb } from "@core/registry";
import Linking from "./Linking";
import PlaneSettings from "./PlaneSettings";
import TeamView from "./TeamView";

const plane: ModuleWeb = {
  id: "plane",
  name: "Plane",
  nav: [
    { label: "Team", icon: <UsersIcon size={16} />, path: "plane/team" },
    { label: "Linking", icon: <NetworkIcon size={16} />, path: "plane/links" },
  ],
  routes: [
    { path: "plane", view: TeamView, wide: true },
    { path: "plane/team", view: TeamView, wide: true },
    { path: "plane/links", view: Linking },
  ],
  settings: PlaneSettings,
};

export default plane;
