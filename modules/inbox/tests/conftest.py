import pytest

from core.server import db, jobs, settings


@pytest.fixture(autouse=True)
def clean_inbox():
    """Every test starts with an empty inbox, Trailmix off and no name set, and leaves it that way."""
    def wipe():
        jobs.drain()
        for table in ("inbox_proposals", "inbox_captures", "inbox_imports", "inbox_fts"):
            db.execute(f"DELETE FROM {table}")
        db.execute("DELETE FROM core_links WHERE from_ref LIKE 'inbox:%' OR to_ref LIKE 'inbox:%'")
        db.execute("DELETE FROM core_jobs WHERE module = 'inbox'")
        settings.update({"inbox.trailmix": False, "inbox.trailmix_url": "http://127.0.0.1:8765", "core.your_name": ""})
    wipe()
    yield
    wipe()
