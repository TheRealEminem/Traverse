"""Muster: the day's kick-off (Traverse PLAN.md chunk 15, D10). Traverse's own module. A muster is the roll call
before setting out.

It shows what's on today, what waits on you, what moved since your last Muster and what's ahead, all from the host's
briefing (core/server/briefing.py), which every module answers for itself through Module.brief; and it keeps the one
thing that's its own, a plan for each day (muster_days): picks as refs, in order, with minutes, carried over until
they're done, and the evening's wrap-up. It reads no other module's tables and calls no other module's API; a pick
ticked here reaches its module through the shared contract work.marked_done. The first look each day can land here
(the web registry's start hook, while "Open Muster first" is on).
"""
from core.server.module import Module

from . import routes, store

# Half-hour steps for working hours, 05:00 to 23:00.
HOURS = tuple(f"{h:02d}:{m:02d}" for h in range(5, 24) for m in (0, 30) if (h, m) != (23, 30))

MODULE = Module(
    id="muster",
    name="Muster",
    router=routes.router,
    migrations=store.MIGRATIONS,
    settings={
        "open_first": True,          # the first look each day lands on Muster
        "day_starts": "09:00",       # working hours, to plan the day against
        "day_ends": "17:00",
    },
    choices={"day_starts": HOURS, "day_ends": HOURS},
    describe=store.describe,
    export=store.export,
    count=store.count,
)
