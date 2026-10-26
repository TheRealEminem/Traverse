import datetime

import pytest

from core.server import db, jobs, settings
from modules.muster.server import days, suggest

TODAY = datetime.date(2026, 10, 21)


class Clock:
    """The day Muster thinks it is, and the time; move them with `clock.day = …` and `clock.time = …`."""
    def __init__(self):
        self.day = TODAY
        self.time = datetime.time(8, 30)


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    """Every test starts with no days mustered and none of Muster's jobs, Muster opening first, 9 to 5, and Wednesday
    21 October 2026 at 8:30 in the morning. AI in Muster is off, so nothing reaches a real model: a test that turns it
    on fakes the AI (fake_structured)."""
    def wipe():
        jobs.drain()
        db.execute("DELETE FROM muster_days")
        db.execute("DELETE FROM core_jobs WHERE module = 'muster'")
        settings.update({"muster.open_first": True, "muster.day_starts": "09:00", "muster.day_ends": "17:00",
                         "muster.ai": False})
    wipe()
    found = Clock()
    monkeypatch.setattr(days, "today", lambda: found.day)
    monkeypatch.setattr(suggest, "now", lambda: datetime.datetime.combine(found.day, found.time))
    yield found
    wipe()
