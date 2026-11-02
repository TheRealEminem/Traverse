"""Calendar: your meetings, for the day's briefing (Traverse PLAN.md chunk 15b). Traverse's own module, built so any
family app could take it.

It reads calendars you add in Settings → Calendar and keeps a short-lived copy of today's and the next week's events
(store.py): a calendar's private iCal address, which the server reads every few minutes (feeds.py), and this Mac's
Calendar, which the Mac app's window reads and sends (mac.py). It never writes to a calendar. Other modules see the
events only through the briefing (briefing.py): Muster plans the day around them without knowing where they're from.
"""
from core.server.module import Module

from . import briefing, feeds, routes, store

MODULE = Module(
    id="calendar",
    name="Calendar",
    router=routes.router,
    migrations=store.MIGRATIONS,
    jobs={feeds.KIND: feeds.read},
    lanes={feeds.KIND: "cloud"},
    recurring={feeds.KIND: feeds.every},
    brief=briefing.brief,
    describe=store.describe,
    export=store.export,
    count=store.count,
)
