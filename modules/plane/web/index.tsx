// The plane module's web half: the Team view and its section in Settings.
import { UsersIcon } from "@core/components/icons";
import type { ModuleWeb } from "@core/registry";
import PlaneSettings from "./PlaneSettings";
import TeamView from "./TeamView";

const plane: ModuleWeb = {
  id: "plane",
  name: "Plane",
  nav: [{ label: "Team", icon: <UsersIcon size={16} />, path: "plane/team" }],
  routes: [
    { path: "plane", view: TeamView, wide: true },
    { path: "plane/team", view: TeamView, wide: true },
  ],
  settings: PlaneSettings,
};

export default plane;
