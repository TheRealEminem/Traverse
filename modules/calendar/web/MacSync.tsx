// This Mac's Calendar, sent to the calendar module: while the Mac app's window is open and "This Mac's Calendar" is one
// of your calendars, it reads today's and the next week's events through the app's calendar bridge (macCalendar) and
// sends them, when it opens, every few minutes and when the window comes back. It never asks macOS for access itself:
// Settings → Calendar does, when you add it. In a browser it does nothing.
import { useEffect } from "react";
import { macCalendar } from "@core/api";
import { useLive } from "@core/live";
import { calendarApi } from "./api";

const EVERY_MS = 5 * 60_000;
const DAYS = 8;

function Sync() {
  const { data: sources } = useLive(calendarApi.sources);
  const macId = sources?.find((s) => s.kind === "mac" && s.enabled)?.id;
  useEffect(() => {
    if (!macCalendar || !macId) return;
    let stopped = false;
    const send = async () => {
      try {
        if ((await macCalendar!.access()) !== "full" || stopped) return;
        const start = new Date();
        start.setHours(0, 0, 0, 0);
        const end = new Date(start);
        end.setDate(end.getDate() + DAYS);
        const found = await macCalendar!.events(start, end);
        if (!stopped && found.access === "full") await calendarApi.send(macId, found.events);
      } catch {
        /* the calendar or the server didn't answer: the next round tries again */
      }
    };
    void send();
    const every = setInterval(() => void send(), EVERY_MS);
    const back = () => void send();
    window.addEventListener("focus", back);
    return () => {
      stopped = true;
      clearInterval(every);
      window.removeEventListener("focus", back);
    };
  }, [macId]);
  return null;
}

export function MacCalendarSync() {
  return macCalendar ? <Sync /> : null;
}
