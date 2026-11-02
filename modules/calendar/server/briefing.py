"""The calendar's part of the day's briefing (core/server/briefing.py, Module.brief): today's events in "today", the
next seven days' in "ahead", and calendars that couldn't be read in "waiting". Nothing in "moved".

An event's entry says when it starts ("when": "2026-10-21T10:00", this computer's time) and how long it takes
("minutes"), so a page that plans the day (Muster) can see the free time between meetings without knowing where they
came from:
    kind "meeting"  takes your time
    kind "event"    doesn't: all day ("when" is a day, no minutes), or shown as free
"project" is the calendar's name.
"""
from datetime import date, datetime, time, timedelta

from . import store


def _minutes(e: dict) -> int | None:
    if e["all_day"]:
        return None
    return max(0, int((datetime.fromisoformat(e["ends"]) - datetime.fromisoformat(e["starts"])).total_seconds() // 60))


def _entry(e: dict, day: date | None = None) -> dict:
    when = e["starts"]
    if e["all_day"] and day is not None:
        when = max(e["starts"], day.isoformat())       # a multi-day one that began earlier is on today too
    return {"id": e["id"], "title": e["title"], "href": None, "when": when, "minutes": _minutes(e),
            "kind": "event" if e["all_day"] or e["free"] else "meeting",
            "what": "All day" if e["all_day"] else ("Shown as free" if e["free"] else "Meeting"),
            "project": e["calendar"] or e["source_name"], "tone": "neutral"}


def brief(since: str, today: date) -> dict:
    start = datetime.combine(today, time())
    tomorrow, week = start + timedelta(days=1), start + timedelta(days=store.WINDOW_DAYS)
    on_today = [_entry(e, today) for e in store.events_between(start, tomorrow)]
    ahead = [_entry(e) for e in store.events_between(tomorrow, week) if e["starts"] >= tomorrow.date().isoformat()]
    waiting = [{"id": s["id"], "title": s["name"], "href": "#/settings", "kind": "calendar", "tone": "sun",
                "what": "Couldn't be read: " + s["error"]}
               for s in store.sources() if s["enabled"] and s["error"]]
    return {"today": on_today, "waiting": waiting, "ahead": ahead}
