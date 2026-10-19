"""Chunk 10: meetings from Trailmix, against a fake Trailmix (an httpx mock transport that answers like its local API
and records every request, so the tests can check that only GETs are ever sent)."""
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from core.server import jobs, schedule, settings
from modules.inbox.server import MODULE, store, trailmix
from modules.inbox.server.extract import Proposal, Reading


def _ago(days: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _meeting(mid: int, uid: str, title: str, days_ago: float, tasks, status="done") -> dict:
    return {"id": mid, "uid": uid, "title": title, "created_at": _ago(days_ago), "duration_sec": 1800, "status": status,
            "workspace_id": None, "ask_first": False, "summary": "## Action Items\n- …", "tasks": tasks}


class FakeTrailmix:
    """GET /api/meetings lists them without uid, as Trailmix's list does; GET /api/meetings/{id} has everything."""

    def __init__(self, meetings: list[dict]):
        self.meetings = {m["id"]: m for m in meetings}
        self.requests: list[httpx.Request] = []
        self.down = False
        self.status = 200

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.down:
            raise httpx.ConnectError("Connection refused", request=request)
        if self.status != 200:
            return httpx.Response(self.status, json={"detail": "Not signed in"})
        path = request.url.path
        if path == "/api/meetings":
            listed = [{k: m[k] for k in ("id", "title", "created_at", "duration_sec", "status", "workspace_id", "ask_first")}
                      for m in self.meetings.values()]
            return httpx.Response(200, json=sorted(listed, key=lambda m: m["created_at"], reverse=True))
        if path.startswith("/api/meetings/"):
            found = self.meetings.get(int(path.rsplit("/", 1)[1]))
            return httpx.Response(200, json=found) if found else httpx.Response(404, json={"detail": "Meeting not found"})
        return httpx.Response(404)


@pytest.fixture
def fake_trailmix(monkeypatch):
    fake = FakeTrailmix([
        _meeting(12, "uid-weekly", "Weekly sync", 1, [
            {"id": 1, "text": "Elijah to send Acme the revised quote by Friday", "done": False},
            {"id": 2, "text": "Mickey: update the pricing sheet", "done": False},
            {"id": 3, "text": "Book the room", "done": True},
        ]),
        _meeting(11, "uid-standup", "Standup", 2, []),                                     # nothing to do
        _meeting(13, "uid-live", "Recording now", 0, [{"id": 4, "text": "x", "done": False}], status="recording"),
        _meeting(5, "uid-old", "Last month", 30, [{"id": 5, "text": "Old thing", "done": False}]),
    ])
    monkeypatch.setattr(trailmix, "_transport", httpx.MockTransport(fake))
    monkeypatch.setattr(trailmix, "_last", {})
    yield fake
    assert {r.method for r in fake.requests} <= {"GET"}, "the inbox must only ever read Trailmix"


def _check(client):
    jobs.enqueue("inbox", "trailmix", "scheduled")
    jobs.drain()
    jobs.drain()


def _trailmix_captures() -> list[dict]:
    return [c for c in store.captures() if c["source"] == "trailmix"]


def test_it_is_off_by_default_and_then_reads_nothing(client, fake_trailmix):
    assert settings.section("inbox")["trailmix"] is False
    assert trailmix.every() == 0
    _check(client)
    assert fake_trailmix.requests == [] and _trailmix_captures() == []
    assert client.post("/api/inbox/trailmix/check").status_code == 400


def test_a_finished_meetings_open_action_items_wait_in_the_inbox_saying_which_meeting(client, fake_trailmix, fake_structured):
    """Chunk 10's "done when": yesterday's meeting's action items wait in the inbox, each saying where it came from."""
    fake_structured.reply = Reading(title="ignored", proposals=[
        Proposal(text="Send Acme the revised quote", assignee_name="Elijah", due_on="2026-10-23",
                 quote="Elijah to send Acme the revised quote by Friday"),
        Proposal(text="Update the pricing sheet", assignee_name="Mickey", quote="Mickey: update the pricing sheet"),
    ])
    settings.update({"inbox.trailmix": True})
    assert trailmix.every() == trailmix.EVERY_SECONDS
    _check(client)

    [capture] = _trailmix_captures()
    assert capture["title"] == "Weekly sync" and capture["origin_title"] == "Weekly sync"   # the meeting keeps its name
    assert capture["origin_id"] == "uid-weekly" and capture["origin_url"] == "http://127.0.0.1:8765/#meeting-12"
    got = client.get(f"/api/inbox/captures/{capture['id']}").json()
    assert got["status"] == "review" and [p["text"] for p in got["proposals"]] == [
        "Send Acme the revised quote", "Update the pricing sheet"]
    assert "Book the room" not in got["raw_text"]                                         # ticked in Trailmix: done
    assert got["raw_text"].startswith("Meeting: Weekly sync · ")
    assert "- Elijah to send Acme the revised quote by Friday" in got["raw_text"]
    prompt = fake_structured.calls[0]["prompt"]
    assert "A meeting's action items (Weekly sync)" in prompt                              # read as the meeting's day
    assert "REFERENCE DATE: " in prompt and capture["origin_at"] == fake_trailmix.meetings[12]["created_at"]
    links = client.get("/api/links", params={"ref": f"inbox:{capture['id']}"}).json()
    assert links == []          # the meeting link is kept for a future meetings module, which isn't on here
    assert store.db.one("SELECT 1 AS x FROM core_links WHERE from_ref = ? AND to_ref = 'meetings:uid-weekly'",
                        (f"inbox:{capture['id']}",))

    # Only what it needed: the list, then the two finished meetings from the last two weeks.
    assert [r.url.path for r in fake_trailmix.requests] == ["/api/meetings", "/api/meetings/12", "/api/meetings/11"]
    status = client.get("/api/inbox/trailmix").json()
    assert status["enabled"] and status["brought_in"] == 1
    assert status["last"]["reachable"] and status["last"]["meetings"] == 2 and status["last"]["brought_in"] == 1


def test_each_meeting_comes_in_once_by_its_uid_even_if_its_capture_is_deleted(client, fake_trailmix, fake_structured):
    fake_structured.reply = Reading(title="x", proposals=[Proposal(text="Send the quote", quote="q")])
    settings.update({"inbox.trailmix": True})
    _check(client)
    _check(client)
    [capture] = _trailmix_captures()

    # The same meeting under another id (Trailmix's database restored, say) is still the same meeting.
    moved = dict(fake_trailmix.meetings.pop(12), id=40)
    fake_trailmix.meetings[40] = moved
    _check(client)
    assert len(_trailmix_captures()) == 1

    client.delete(f"/api/inbox/captures/{capture['id']}")
    _check(client)
    assert _trailmix_captures() == []

    fake_trailmix.meetings[41] = _meeting(41, "uid-new", "Planning", 0.1, [{"id": 9, "text": "Draft the plan", "done": False}])
    _check(client)
    assert [c["title"] for c in _trailmix_captures()] == ["Planning"]


def test_when_trailmix_isnt_running_nothing_happens_and_settings_say_so(client, fake_trailmix, fake_structured):
    settings.update({"inbox.trailmix": True})
    fake_trailmix.down = True
    _check(client)
    assert _trailmix_captures() == []
    status = client.get("/api/inbox/trailmix").json()
    assert status["last"]["reachable"] is False and status["job"]["status"] == "done"     # not an error: it's just closed

    fake_trailmix.down = False
    fake_trailmix.status = 401
    _check(client)
    assert "sign-in" in client.get("/api/inbox/trailmix").json()["last"]["error"]


def test_the_host_runs_it_on_a_schedule_only_while_it_is_on(client, fake_trailmix, fake_structured):
    fake_structured.reply = Reading(title="x", proposals=[])
    schedule.register("inbox", "trailmix", MODULE.recurring["trailmix"])    # as the host does at startup (the host's
    start = 1_000_000.0                                                      # own tests reset the schedule)
    assert "inbox/trailmix" not in schedule.tick(start + 10_000)
    settings.update({"inbox.trailmix": True})
    assert "inbox/trailmix" in schedule.tick(start + 20_000)
    jobs.drain()
    jobs.drain()
    assert fake_trailmix.requests and fake_trailmix.requests[0].url.path == "/api/meetings"
    assert client.post("/api/inbox/trailmix/check").status_code == 202
