// The calendar module's web half: no page of its own. Its calendars are chosen in Settings → Calendar, and in the Mac
// app's window it sends this Mac's Calendar to the server (MacSync.tsx). Its events reach other pages (Muster) through
// the day's briefing.
import type { ModuleWeb } from "@core/registry";
import { CalendarSettings } from "./CalendarSettings";
import { MacCalendarSync } from "./MacSync";

const calendar: ModuleWeb = {
  id: "calendar",
  name: "Calendar",
  routes: [],
  settings: CalendarSettings,
  background: MacCalendarSync,
};

export default calendar;
