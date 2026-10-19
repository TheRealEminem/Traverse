"""The plane module's test fixtures: Plane set up in Settings and talking to the fake one (fakeplane.py)."""
import pytest

from core.server import db, jobs, settings
from modules.plane.server import pull, store
from modules.plane.tests.fakeplane import REAL_PROJECTS, WS, FakePlane


@pytest.fixture
def fake_plane(monkeypatch):
    """Plane set up in Settings (every project but the demo one), talking to the fake. Cleans up afterwards."""
    fake = FakePlane()
    def client(cfg=None, **kw):
        cfg = cfg or pull.config()
        return fake.client(cfg["personal_api_key"], cfg["workspace_slug"], **kw)

    monkeypatch.setattr(pull, "client", client)
    settings.update({"plane.personal_api_key": "plane_api_test", "plane.workspace_slug": WS,
                     "plane.projects": REAL_PROJECTS})
    jobs.drain()                              # the settings change queued a pull; let it finish before the test
    _clear()
    fake.requests.clear()
    yield fake
    jobs.drain()
    settings.update({"plane.personal_api_key": "", "plane.workspace_slug": "", "plane.projects": [], "plane.me": "",
                     "plane.base_url": "https://api.plane.so", "plane.pull_minutes": 5})
    jobs.drain()
    _clear()


def _clear():
    with db.connect() as conn:
        for t in (*store.MIRROR_TABLES, "plane_meta"):
            conn.execute(f"DELETE FROM {t}")
        conn.execute("DELETE FROM core_jobs WHERE module = 'plane'")


@pytest.fixture
def pulled(fake_plane):
    """The fake workspace, pulled once."""
    pull.pull_now()
    jobs.drain()
    assert db.one("SELECT status, error FROM core_jobs WHERE module = 'plane'")["status"] == "done"
    return fake_plane
