"""Auto-send: a linked project whose new tasks go to Plane without waiting for Send (off by default). End to end
against the fake Plane: tasks made on the project page, accepted from the inbox, moved in, and sent in a batch with
"Send the new ones". What reached Plane is read from the fake's record of every write."""
import threading
import time

import pytest

from core.server import db, jobs, mcp, settings
from modules.inbox.server.extract import Proposal, Reading
from modules.plane.server import pull
from modules.plane.tests.fakeplane import PROJECTS
from modules.tasks.server import items


@pytest.fixture
def plane(pulled):
    """The fake workspace, pulled, with dry run off, Software linked to a new Traverse project, and nothing else."""
    def wipe():
        for t in ("tasks_synced", "tasks_blockers", "tasks_updates", "tasks_items", "tasks_milestones", "tasks_projects",
                  "tasks_fts", "plane_links", "plane_pushes", "plane_sent"):
            db.execute(f"DELETE FROM {t}")
        db.execute("DELETE FROM core_links")
    wipe()
    settings.update({"plane.dry_run": False})
    pulled.requests.clear()
    yield pulled
    jobs.drain()
    wipe()


def _link(client, auto: bool | None = None) -> str:
    """Links Software to a new Traverse project; returns that project's id."""
    client.post(f"/api/plane/links/{PROJECTS['SOFTWARE']}")
    if auto is not None:
        r = client.patch(f"/api/plane/links/{PROJECTS['SOFTWARE']}", json={"auto_send": auto})
        assert r.status_code == 200, r.text
        assert r.json()["link"]["auto_send"] is auto
    return client.get("/api/tasks/projects").json()[0]["id"]


def _add(client, text: str, project_id: str | None, **more) -> str:
    r = client.post("/api/tasks", json={"text": text, "project_id": project_id, **more})
    assert r.status_code in (200, 201), r.text
    jobs.drain()
    return r.json()["id"]


def _made(fake) -> list[str]:
    return [body["name"] for method, _, body in fake.writes if method == "POST"]


def _box(client) -> dict:
    jobs.drain()
    return client.get("/api/plane/outbox").json()


def test_auto_send_is_off_by_default_and_a_new_task_waits_for_you(plane, client):
    project = _link(client)
    software = next(p for p in client.get("/api/plane/links").json()["projects"] if p["id"] == PROJECTS["SOFTWARE"])
    assert software["link"]["auto_send"] is False
    tid = _add(client, "Write the API docs", project)
    assert _box(client)["waiting"] == [] and plane.writes == []        # nothing asked, nothing parked
    assert client.get(f"/api/tasks/projects/{project}").json()["unshared"] == 1
    assert client.get(f"/api/tasks/{tid}").json()["synced"] is None


def test_with_auto_send_on_a_new_task_is_made_in_plane_without_send_and_becomes_linked(plane, client):
    project = _link(client, auto=True)
    tid = _add(client, "Write the API docs", project, priority=3, due_on="2026-11-06")
    assert _made(plane) == ["Write the API docs"]
    box = _box(client)
    assert box["waiting"] == []
    [sent] = box["sent"]
    assert sent["kind"] == "create" and sent["auto"] is True and sent["item"]["key"] == "SOFTWARE-6"
    task = client.get(f"/api/tasks/{tid}").json()
    assert task["synced"]["title"] == "SOFTWARE-6 Write the API docs" and task["sharing"] == []
    assert client.get(f"/api/tasks/projects/{project}").json()["unshared"] == 0


def test_auto_send_only_makes_new_items_edits_still_wait_and_nothing_is_deleted(plane, client):
    project = _link(client, auto=True)
    tid = _add(client, "Write the API docs", project)
    client.patch(f"/api/tasks/{tid}", json={"text": "Write the API docs (v1)"})
    client.post(f"/api/tasks/{tid}/share")
    [waiting] = _box(client)["waiting"]
    assert waiting["kind"] == "update" and waiting["auto"] is False
    assert [m for m, _, _ in plane.writes] == ["POST"]                # the edit hasn't gone
    client.delete(f"/api/tasks/{tid}")
    jobs.drain()
    assert [m for m, _, _ in plane.writes] == ["POST"] and plane.item("SOFTWARE-6")["name"] == "Write the API docs"


def test_subtasks_closed_tasks_and_other_projects_are_not_sent(plane, client):
    project = _link(client, auto=True)
    parent = _add(client, "Ship v1", project)
    _add(client, "A subtask", project, parent_id=parent)
    _add(client, "Already done", project, status="done")
    private = client.post("/api/tasks/projects", json={"name": "Just mine"}).json()["id"]
    _add(client, "Private", private)
    _add(client, "In no project", None)
    assert _made(plane) == ["Ship v1"]


def test_moving_a_task_into_an_auto_send_project_sends_it(plane, client):
    project = _link(client, auto=True)
    tid = _add(client, "Loose idea", None)
    assert plane.writes == []
    client.patch(f"/api/tasks/{tid}", json={"project_id": project})
    jobs.drain()
    assert _made(plane) == ["Loose idea"]


def test_turning_it_on_doesnt_send_what_was_there_but_send_the_new_ones_does(plane, client):
    project = _link(client)
    _add(client, "First", project)
    _add(client, "Second", project)
    _link_auto = client.patch(f"/api/plane/links/{PROJECTS['SOFTWARE']}", json={"auto_send": True})
    assert _link_auto.json()["link"]["auto_send"] is True
    jobs.drain()
    assert plane.writes == []
    assert client.get(f"/api/tasks/projects/{project}").json()["unshared"] == 2
    assert client.post(f"/api/tasks/projects/{project}/share").json() == {"asked": 2}
    jobs.drain()
    assert sorted(_made(plane)) == ["First", "Second"]
    assert client.post(f"/api/tasks/projects/{project}/share").json() == {"asked": 0}     # none twice
    assert len(_made(plane)) == 2


def test_send_the_new_ones_without_auto_send_parks_each_in_the_outbox(plane, client):
    project = _link(client)
    for text in ("First", "Second", "Third"):
        _add(client, text, project)
    assert client.post(f"/api/tasks/projects/{project}/share").json() == {"asked": 3}
    box = _box(client)
    assert sorted(p["task"]["title"] for p in box["waiting"]) == ["First", "Second", "Third"]
    assert all(p["kind"] == "create" and p["status"] == "waiting" for p in box["waiting"])
    assert client.get(f"/api/tasks/projects/{project}").json()["unshared"] == 0      # all waiting already
    assert plane.writes == []


def test_send_the_new_ones_needs_a_linked_project(plane, client):
    private = client.post("/api/tasks/projects", json={"name": "Just mine"}).json()["id"]
    _add(client, "Private", private)
    r = client.post(f"/api/tasks/projects/{private}/share")
    assert r.status_code == 400 and "isn't linked anywhere" in r.json()["detail"]
    assert client.get(f"/api/tasks/projects/{private}").json()["unshared"] == 0


def test_claudes_tasks_wait_for_you_even_with_auto_send_on(plane, client):
    project = _link(client, auto=True)
    token = mcp._calling.set("tasks_add")
    try:
        items.create("Proposed by Claude", project_id=project)
    finally:
        mcp._calling.reset(token)
    [waiting] = _box(client)["waiting"]
    assert waiting["task"]["title"] == "Proposed by Claude" and waiting["status"] == "waiting"
    assert plane.writes == []


def test_dry_run_still_writes_nothing_and_leaves_it_waiting(plane, client):
    settings.update({"plane.dry_run": True})
    project = _link(client, auto=True)
    _add(client, "Trial", project)
    [waiting] = _box(client)["waiting"]
    assert waiting["status"] == "waiting" and waiting["note"].startswith("Dry run")
    assert plane.writes == []


def test_auto_send_needs_a_link_and_a_true_or_false(plane, client):
    r = client.patch(f"/api/plane/links/{PROJECTS['SOFTWARE']}", json={"auto_send": True})
    assert r.status_code == 400 and "first" in r.json()["detail"]
    _link(client)
    r = client.patch(f"/api/plane/links/{PROJECTS['SOFTWARE']}", json={"auto_send": "yes"})
    assert r.status_code == 400


def test_whats_accepted_from_the_inbox_lands_in_plane_with_no_second_step(plane, client, fake_structured):
    """The whole path: paste loose text, the AI proposes, you accept, and they're Plane items."""
    project = _link(client, auto=True)
    fake_structured.reply = Reading(title="Launch follow-ups", proposals=[
        Proposal(text="Send Acme the revised quote", quote="I'll send Acme the revised quote."),
        Proposal(text="Update the pricing sheet", quote="Someone update the pricing sheet."),
    ])
    r = client.post("/api/inbox/paste", json={"text": "I'll send Acme the revised quote.\nSomeone update the pricing sheet."})
    assert r.status_code == 201, r.text
    capture_id = r.json()["id"]
    jobs.drain()
    client.put(f"/api/inbox/captures/{capture_id}/project", json={"ref": f"tasks:{project}"})
    assert client.post(f"/api/inbox/captures/{capture_id}/accept", json={}).json() == {"accepted": 2}
    jobs.drain()
    assert sorted(_made(plane)) == ["Send Acme the revised quote", "Update the pricing sheet"]
    assert _box(client)["waiting"] == []
    filed = [t for t in client.get("/api/tasks", params={"project": project}).json()]
    assert all(t["synced"] and t["synced"]["title"].startswith("SOFTWARE-") for t in filed) and len(filed) == 2


def test_accepted_with_no_project_then_filed_into_one_follows_it_to_plane(plane, client, fake_structured):
    project = _link(client, auto=True)
    fake_structured.reply = Reading(title="Loose", proposals=[
        Proposal(text="Call the printer", quote="Call the printer."),
        Proposal(text="Order labels", quote="Order labels."),
    ])
    capture_id = client.post("/api/inbox/paste", json={"text": "Call the printer.\nOrder labels."}).json()["id"]
    jobs.drain()
    first, second = client.get(f"/api/inbox/captures/{capture_id}").json()["proposals"]
    client.post(f"/api/inbox/proposals/{first['id']}/accept")
    jobs.drain()
    assert plane.writes == []                                          # in no project: nowhere to go
    client.put(f"/api/inbox/captures/{capture_id}/project", json={"ref": f"tasks:{project}"})
    client.post(f"/api/inbox/proposals/{second['id']}/accept")         # the first follows the capture in
    jobs.drain()
    assert sorted(_made(plane)) == ["Call the printer", "Order labels"]


def test_a_task_sent_while_a_pull_reads_isnt_taken_for_removed(plane, client, monkeypatch):
    """A pull that read the project before a push made the item, and saved after, used to mark the new item "Removed in
    Plane" (auto-send makes this likelier): the two now take turns (pull.LOCK)."""
    project = _link(client, auto=True)
    read, go = threading.Event(), threading.Event()
    real_read = pull.read

    def slow_read(*args, **kwargs):
        found = real_read(*args, **kwargs)
        read.set()
        go.wait(5)
        return found

    monkeypatch.setattr(pull, "read", slow_read)
    pull.pull_now()
    assert read.wait(5)
    r = client.post("/api/tasks", json={"text": "Made mid-pull", "project_id": project})
    assert r.status_code in (200, 201), r.text
    tid = r.json()["id"]
    time.sleep(0.3)                                                    # its push waits for the pull to finish
    go.set()
    jobs.drain()
    task = client.get(f"/api/tasks/{tid}").json()
    assert task["synced"] and not task["synced"]["removed_at"] and _made(plane) == ["Made mid-pull"]
    assert not db.one("SELECT removed_at FROM plane_items WHERE id = ?", (task["synced"]["ref"].split(":")[1],))["removed_at"]
