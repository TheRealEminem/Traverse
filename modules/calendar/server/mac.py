"""This Mac's Calendar as a source. The server can't read it: the Mac app's window reads it through its calendar bridge
(mac/Sources/AppHost/CalendarBridge.swift; macOS asks you once) and sends today's and the next week's events here
(the web half's MacCalendarSync), when it opens, every few minutes and when it comes back. They replace what the source
had, like any read.

An event as the bridge gives it:
    {"id", "title", "start", "end", "all_day", "calendar", "free"}
    start, end  ISO moments with the Mac's offset ("2026-10-21T10:00:00+11:00"). An all-day event runs from its first
                day's midnight to its last day's end (23:59:59, as EventKit says it, or the next midnight).
"""
from datetime import date, datetime, timedelta

from core.server import events

from . import store

MOST_SENT = 500


def _moment(value, what: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"An event's {what} is a moment like 2026-10-21T10:00:00+11:00")
    try:
        found = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"An event's {what} is a moment like 2026-10-21T10:00:00+11:00") from None
    return found.astimezone().replace(tzinfo=None) if found.tzinfo else found


def _text(value, longest: int) -> str:
    return " ".join(value.split())[:longest] if isinstance(value, str) else ""


def clean(sent, on: date) -> list[dict]:
    """The events that touch the window from `on`, checked and in this computer's time, as store.replace takes them.
    Raises ValueError for anything that isn't a list of events."""
    if not isinstance(sent, list) or len(sent) > MOST_SENT:
        raise ValueError(f"Send a list of up to {MOST_SENT} events")
    start, end = store.window(on)
    out = []
    for e in sent:
        if not isinstance(e, dict):
            raise ValueError("An event is {id, title, start, end, all_day, calendar, free}")
        begins, finishes = _moment(e.get("start"), "start"), _moment(e.get("end"), "end")
        if finishes < begins:
            raise ValueError("An event can't end before it starts")
        if finishes <= start or begins >= end:
            continue
        all_day = e.get("all_day") is True
        if all_day:
            first, after = begins.date(), (finishes - timedelta(seconds=1)).date() + timedelta(days=1)
            starts, ends = first.isoformat(), max(after, first + timedelta(days=1)).isoformat()
        else:
            starts, ends = begins.isoformat(timespec="minutes"), finishes.isoformat(timespec="minutes")
        out.append({"uid": _text(e.get("id"), 300) or starts, "title": _text(e.get("title"), 200) or "Busy",
                    "starts": starts, "ends": ends, "all_day": all_day, "free": e.get("free") is True,
                    "calendar": _text(e.get("calendar"), 100)})
    return out


def take(source_id: str, sent) -> int:
    """What the Mac app's window read, in place of the source's events. Returns how many are kept."""
    row = store.source(source_id)
    if row is None:
        raise KeyError(source_id)
    if row["kind"] != "mac":
        raise ValueError("Only this Mac's Calendar is sent from the app; an iCal calendar is read by Traverse itself")
    kept = store.replace(source_id, clean(sent, store.today()))
    store.tried(source_id, None)
    events.publish("calendar.changed", {})
    return kept
