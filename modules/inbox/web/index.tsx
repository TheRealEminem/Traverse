// The inbox module's web half: its sidebar entry (with how many captures wait for you), pages, Home card and settings.
import { InboxIcon } from "@core/components/icons";
import type { ModuleWeb } from "@core/registry";
import CaptureView from "./CaptureView";
import { InboxHome, InboxSettings, WaitingCount } from "./extras";
import InboxView from "./InboxView";

const inbox: ModuleWeb = {
  id: "inbox",
  name: "Inbox",
  nav: [{ label: "Inbox", icon: <InboxIcon size={16} />, path: "inbox", badge: WaitingCount }],
  routes: [
    { path: "inbox", view: InboxView },
    { path: "inbox/:id", view: CaptureView },
  ],
  home: InboxHome,
  settings: InboxSettings,
};

export default inbox;
