import datetime

import pytest

from core.server import db, settings
from modules.muster.server import days

TODAY = datetime.date(2026, 10, 21)


class Clock:
    """The day Muster thinks it is; move it with `clock.day = …`."""
    def __init__(self):
        self.day = TODAY


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    """Every test starts with no days mustered, Muster opening first, 9 to 5, and Wednesday 21 October 2026."""
    def wipe():
        db.execute("DELETE FROM muster_days")
        settings.update({"muster.open_first": True, "muster.day_starts": "09:00", "muster.day_ends": "17:00"})
    wipe()
    found = Clock()
    monkeypatch.setattr(days, "today", lambda: found.day)
    yield found
    wipe()
