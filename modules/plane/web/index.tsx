// The plane module's web half: the Team view, Linking, the Outbox (with how many pushes wait for you), and its
// section in Settings.
import { NetworkIcon, UsersIcon, icon } from "@core/components/icons";
import type { ModuleWeb } from "@core/registry";
import { Send } from "lucide-react";
import Linking from "./Linking";
import Outbox, { OutboxCount } from "./Outbox";
import PlaneSettings from "./PlaneSettings";
import TeamView from "./TeamView";

const SendIcon = icon(Send);

const plane: ModuleWeb = {
  id: "plane",
  name: "Plane",
  nav: [
    { label: "Team", icon: <UsersIcon size={16} />, path: "plane/team" },
    { label: "Linking", icon: <NetworkIcon size={16} />, path: "plane/links" },
    { label: "Outbox", icon: <SendIcon size={16} />, path: "plane/outbox", badge: OutboxCount },
  ],
  routes: [
    { path: "plane", view: TeamView, wide: true },
    { path: "plane/team", view: TeamView, wide: true },
    { path: "plane/links", view: Linking },
    { path: "plane/outbox", view: Outbox },
  ],
  settings: PlaneSettings,
};

export default plane;
