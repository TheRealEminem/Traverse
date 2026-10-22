import datetime
import os
import time

import pytest

from core.server import db, jobs
from modules.calendar.server import feeds, store

TODAY = datetime.date(2026, 10, 21)


@pytest.fixture(autouse=True)
def calendar_day(monkeypatch):
    """Every test starts with no calendars, on Wednesday 21 October 2026, with no calendar server to reach."""
    def wipe():
        jobs.drain()
        db.execute("DELETE FROM calendar_sources")
        db.execute("DELETE FROM core_jobs WHERE module = 'calendar'")
    wipe()
    monkeypatch.setattr(store, "today", lambda: TODAY)
    monkeypatch.setattr(feeds, "_transport", None)
    yield
    wipe()


@pytest.fixture
def melbourne():
    """This computer's clock in Melbourne (UTC+11 in October), so other zones have to be converted."""
    old = os.environ.get("TZ")
    os.environ["TZ"] = "Australia/Melbourne"
    time.tzset()
    yield
    if old is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = old
    time.tzset()
