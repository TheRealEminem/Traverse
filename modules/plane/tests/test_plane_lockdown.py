"""Lockdown and Plane: while it's on, nothing reaches Plane, neither a pull nor a push you sent; both park as "Lockdown
is on" and go ahead by themselves when it's off. Against the fake Plane, which records every request."""
from core.server import db, jobs, lockdown, settings
from modules.plane.server import pull, store
from modules.plane.server.client import PlaneClient
from modules.plane.tests.fakeplane import WS
from modules.plane.tests.test_push import _bring, _edit, _push, _share, _waiting, plane  # noqa: F401 (a fixture)


def _pull_job() -> dict:
    return db.one("SELECT status, wait_reason, error FROM core_jobs WHERE module = 'plane' AND kind = 'pull'")


def _off(client) -> None:
    """Lockdown off, the way Settings does it (what it parked goes at once)."""
    assert client.put("/api/settings", json={lockdown.KEY: False}).status_code == 200
    jobs.drain()


def test_a_pull_waits_and_nothing_reaches_plane_until_lockdown_is_off(fake_plane, lockdown_on, client):
    pull.pull_now()
    jobs.drain()
    assert _pull_job() == {"status": "waiting", "wait_reason": lockdown.REASON, "error": None}
    assert fake_plane.requests == [] and store.meta("last_pull") is None
    assert client.post("/api/plane/pull").status_code == 202                  # "Pull now" doesn't get past it
    jobs.drain()
    assert _pull_job()["status"] == "waiting" and fake_plane.requests == []

    _off(client)
    assert _pull_job()["status"] == "done" and fake_plane.requests and store.meta("last_pull")


def test_a_pull_already_reading_stops_at_its_next_request(fake_plane, client, lockdown_on):
    settings.update({lockdown.KEY: False})
    answer = fake_plane.handle

    def first_then_lockdown(request):
        settings.update({lockdown.KEY: True})                                  # turned on while the pull reads
        return answer(request)
    fake_plane.transport.handler = first_then_lockdown
    pull.pull_now()
    jobs.drain()
    assert _pull_job()["status"] == "waiting" and len(fake_plane.requests) == 1
    assert store.meta("last_pull") is None and store.counts()["items"] == 0   # it writes all or nothing


def test_a_push_you_sent_waits_for_lockdown_and_then_goes(plane, client, lockdown_on):
    settings.update({lockdown.KEY: False})
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, priority=4)
    _share(client, tid)
    push_id = _waiting(client)["id"]
    plane.requests.clear()

    settings.update({lockdown.KEY: True})
    assert client.post(f"/api/plane/pushes/{push_id}/send").status_code == 200
    jobs.drain()
    held = _push(client, push_id)
    assert held["status"] == "sending" and held["job"]["status"] == "waiting"
    assert held["job"]["wait_reason"] == lockdown.REASON
    assert plane.requests == [] and plane.writes == []

    _off(client)
    sent = _push(client, push_id)
    assert sent["status"] == "sent" and [(m, body) for m, _, body in plane.writes] == [("PATCH", {"priority": "urgent"})]


def test_testing_the_connection_says_lockdown_is_on(fake_plane, lockdown_on, client):
    r = client.post("/api/plane/test")
    assert r.status_code == 409 and r.json()["detail"] == lockdown.SENTENCE
    assert fake_plane.requests == []


def test_a_plane_on_this_mac_is_still_reached(fake_plane, lockdown_on):
    with PlaneClient("http://127.0.0.1:8080", "plane_api_test", WS, transport=fake_plane.transport) as here:
        assert here.me()["id"]
    assert len(fake_plane.requests) == 1
