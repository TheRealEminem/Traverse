"""Chunk 15a's "done when", end to end against the fake Plane: after a pull with real changes, the first look the next
day lands on Muster, which shows what moved since yesterday's Muster from Plane's change log, today's due work and
what's waiting; picks carry over, the wrap-up rolls the open ones to tomorrow, and nothing reaches Plane but the pull's
GETs."""
from datetime import timedelta

import pytest

from core.server import config, db, jobs
from modules.muster.server import days
from modules.muster.tests.conftest import TODAY
from modules.tasks.server import items

pytestmark = pytest.mark.skipif(not {"plane", "tasks"} <= set(config.enabled_modules()),
                                reason="needs the plane and tasks modules")

if {"plane", "tasks"} <= set(config.enabled_modules()):
    from modules.plane.tests.conftest import fake_plane  # noqa: F401 - the fixture, for this file's tests
    from modules.plane.tests.fakeplane import MEMBERS, PROJECTS, WS


def _pull() -> None:
    from modules.plane.server import pull
    pull.pull_now()
    jobs.drain()


def _section(view: dict, name: str, module_id: str) -> list[dict]:
    return [e for e in view["briefing"]["sections"][name] if e["module"] == module_id]


def test_the_next_morning(client, clock, fake_plane):
    yesterday = TODAY - timedelta(days=1)
    clock.day = yesterday
    _pull()                                                          # the first pull: nothing logged
    due = items.create("Send the grant letter", due_on=TODAY.isoformat())
    open_pick = items.create("Draft the deck")
    try:
        client.post(f"/api/muster/days/{yesterday}/open")
        for ref in (f"tasks:{open_pick}", f"plane:{fake_plane.item('SOFTWARE-4')['id']}"):
            assert client.post(f"/api/muster/days/{yesterday}/picks", json={"ref": ref}).status_code == 201
        done = client.post(f"/api/muster/days/{yesterday}/picks", json={"title": "Call the bank"}).json()
        client.patch(f"/api/muster/days/{yesterday}/picks/{done['id']}", json={"done": True})

        # Overnight a teammate moves things in Plane, and a pull sees it.
        states = fake_plane.data[f"/api/v1/workspaces/{WS}/projects/{PROJECTS['SOFTWARE']}/states/"]["results"]
        fake_plane.edit("SOFTWARE-5", state=next(s["id"] for s in states if s["group"] == "started"),
                        updated_by=MEMBERS["alex"])
        fake_plane.edit("BD-14", assignees=[MEMBERS["sam"]], updated_by=MEMBERS["sam"])
        _pull()

        clock.day = TODAY
        assert client.get("/api/muster/start").json() == {"path": "muster"}
        view = client.post(f"/api/muster/days/{TODAY}/open").json()
        moved = {e["title"].split(" ")[0]: e["what"] for e in _section(view, "moved", "plane")}
        assert moved["SOFTWARE-5"] == "Todo → In Progress"              # Alex has it: the line says so, not "by Alex" too
        assert moved["BD-14"] == "Now with Sam (was you)"
        assert ("Send the grant letter", "Due today") in [(e["title"], e["what"]) for e in _section(view, "today", "tasks")]
        assert _section(view, "today", "plane")                     # the team's past-due items
        assert [p["title"] for p in view["picks"]] == ["Draft the deck", "SOFTWARE-4 Populate the demo site with data"]
        assert client.get("/api/muster/start").json() == {"path": None}

        wrapped = client.post(f"/api/muster/days/{TODAY}/wrapup", json={"note": "Deck first"}).json()
        assert (wrapped["rolled"], wrapped["to"]) == (2, (TODAY + timedelta(days=1)).isoformat())
        assert fake_plane.writes == []
        assert {r.method for r in fake_plane.requests} == {"GET"}
    finally:
        for item_id in (due, open_pick):
            items.delete(item_id)
        db.execute("DELETE FROM muster_days")
