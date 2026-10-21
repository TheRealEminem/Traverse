"""Comments (chunk 12, PLAN.md §3.1): your Traverse updates go to Plane only as new comments on linked items, only after
you approve each one in the outbox, and never as an edit or a delete. End to end against the fake Plane, the way the
screens do it: a comment on a linked task, or a project's status draft posted on one of its linked tasks."""
import pytest

from core.server import db, jobs, mcp, settings
from modules.plane.server import pull, push
from modules.tasks.server.drafts import StatusDraft


@pytest.fixture
def plane(pulled):
    """The fake workspace, pulled, with dry run off and nothing in Traverse yet."""
    def wipe():
        for t in ("tasks_drafts", "tasks_synced", "tasks_blockers", "tasks_updates", "tasks_items", "tasks_milestones",
                  "tasks_projects", "tasks_fts", "plane_links", "plane_pushes", "plane_sent"):
            db.execute(f"DELETE FROM {t}")
        db.execute("DELETE FROM core_links")
    wipe()
    settings.update({"plane.dry_run": False})
    pulled.requests.clear()
    yield pulled
    jobs.drain()
    wipe()


def _bring(client, fake, key: str) -> str:
    item = fake.item(key)
    assert client.post("/api/plane/bring", json={"items": [item["id"]]}).json()["brought"] == 1
    return next(t["id"] for t in client.get("/api/tasks", params={"status": "all"}).json()
                if t["synced"] and t["synced"]["ref"] == f"plane:{item['id']}")


def _comment(client, tid: str, body: str) -> dict:
    """A comment on the task, then "Post it in Plane too"."""
    update = client.post(f"/api/tasks/{tid}/updates", json={"body": body}).json()
    r = client.post(f"/api/tasks/updates/{update['id']}/share", json={})
    assert r.status_code == 200, r.text
    return {**update, "waiting": r.json()}


def _waiting(client) -> dict:
    [found] = client.get("/api/plane/outbox").json()["waiting"]
    return found


def _send(client, push_id: str) -> dict:
    r = client.post(f"/api/plane/pushes/{push_id}/send")
    assert r.status_code == 200, r.text
    jobs.drain()
    box = client.get("/api/plane/outbox").json()
    return next(p for p in box["waiting"] + box["sent"] if p["id"] == push_id)


def test_a_comment_waits_for_you_then_is_added_and_nothing_else_is_written(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    before = dict(plane.item("OPERATIONS-10"))
    update = _comment(client, tid, "Called the broker. **Quote** by Friday.")
    assert update["waiting"]["title"] == "Waiting for you to send it to Plane"
    waiting = _waiting(client)
    assert waiting["kind"] == "comment" and waiting["status"] == "waiting" and waiting["job"]["status"] == "waiting"
    assert waiting["task"]["title"] == "Renew the insurance policy" and waiting["item"]["key"] == "OPERATIONS-10"
    assert [(f["field"], f["after"], f["include"]) for f in waiting["fields"]] == [
        ("comment", "Called the broker. **Quote** by Friday.", True)]
    assert client.get("/api/plane/outbox/count").json() == {"waiting": 1}
    assert plane.writes == [] and {r.method for r in plane.requests} <= {"GET"}           # nothing yet
    assert "goes whole" in client.patch(f"/api/plane/pushes/{waiting['id']}", json={"include": {"comment": False}}).json()["detail"]

    sent = _send(client, waiting["id"])
    assert sent["status"] == "sent" and sent["approved_at"]
    [(method, path, body)] = plane.writes
    assert method == "POST" and path == plane.item_path("OPERATIONS-10") + "comments/"
    assert body == {"comment_html": "<p>Called the broker. <strong>Quote</strong> by Friday.</p>",
                    "external_source": "traverse", "external_id": waiting["id"]}
    assert [c["comment_html"] for c in plane.comments("OPERATIONS-10")] == [body["comment_html"]]
    assert plane.item("OPERATIONS-10") == before                                      # the item itself: untouched
    [shown] = client.get(f"/api/tasks/{tid}").json()["updates"]
    assert shown["shared"] == [{"title": "Posted in Plane", "href": f"#/plane/outbox?push={waiting['id']}",
                                "state": "posted"}]

    # Once there it stays as it is: not again, and no Undo (that would be an edit or a delete).
    assert "already" in client.post(f"/api/tasks/updates/{update['id']}/share", json={}).json()["detail"]
    r = client.post(f"/api/plane/pushes/{waiting['id']}/undo")
    assert r.status_code == 400 and "never edits or deletes comments" in r.json()["detail"]
    assert [w[0] for w in plane.writes] == ["POST"]


def test_a_status_draft_goes_on_a_linked_task_and_says_which_ai_drafted_it(plane, client, fake_structured):
    tid = _bring(client, plane, "OPERATIONS-10")
    pid = client.get(f"/api/tasks/{tid}").json()["project_id"]
    fake_structured.reply = StatusDraft(body="On track: the policy renewal is the last open item.", why="Nothing late.",
                                        health="on_track")
    client.post(f"/api/tasks/projects/{pid}/draft")
    jobs.drain()
    draft = client.get(f"/api/tasks/projects/{pid}/draft").json()
    update = client.post(f"/api/tasks/drafts/{draft['id']}/post", json={"share_on": tid}).json()
    assert update["kind"] == "status" and update["asked"]["title"] == "Waiting for you to send it to Plane"
    waiting = _waiting(client)
    assert waiting["kind"] == "comment" and waiting["item"]["key"] == "OPERATIONS-10"
    words = waiting["fields"][0]["after"]
    assert words == f"On track: the policy renewal is the last open item.\n\n*Drafted by {draft['written_by']}*"
    _send(client, waiting["id"])
    [(_, _, body)] = plane.writes
    assert body["comment_html"] == (f"<p>On track: the policy renewal is the last open item.</p>"
                                    f"<p><em>Drafted by {draft['written_by']}</em></p>")
    project = client.get(f"/api/tasks/projects/{pid}").json()
    assert project["latest_status"]["shared"][0]["state"] == "posted" and project["health"] == "on_track"


def test_dry_run_checks_the_item_but_adds_no_comment(plane, client):
    settings.update({"plane.dry_run": True})
    tid = _bring(client, plane, "OPERATIONS-10")
    _comment(client, tid, "Called the broker.")
    push_id = _waiting(client)["id"]
    plane.requests.clear()
    tried = _send(client, push_id)
    assert tried["status"] == "waiting"
    assert tried["note"] == "Dry run: checked against Plane. Send would add this comment to OPERATIONS-10. Nothing was sent."
    assert plane.writes == [] and {r.method for r in plane.requests} == {"GET"} and plane.comments("OPERATIONS-10") == []
    settings.update({"plane.dry_run": False})
    assert _send(client, push_id)["status"] == "sent" and len(plane.comments("OPERATIONS-10")) == 1


def test_asking_again_replaces_the_words_and_discard_forgets_it(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    update = _comment(client, tid, "Called the broker.")
    first = _waiting(client)["id"]
    db.execute("UPDATE tasks_updates SET body = 'Called the broker twice.' WHERE id = ?", (update["id"],))
    client.post(f"/api/tasks/updates/{update['id']}/share", json={})
    again = _waiting(client)
    assert again["id"] == first and again["fields"][0]["after"] == "Called the broker twice."     # one push, new words
    assert client.post(f"/api/plane/pushes/{first}/discard").json()["status"] == "discarded"
    assert client.get("/api/plane/outbox").json()["waiting"] == []
    assert client.get(f"/api/tasks/{tid}").json()["updates"][0]["shared"] == []
    assert plane.writes == []


def test_a_comment_whose_answer_was_lost_is_not_added_twice(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _comment(client, tid, "Called the broker.")
    push_id = _waiting(client)["id"]
    plane.lose_next_answer = True
    failed = _send(client, push_id)
    assert failed["status"] == "failed" and "didn't answer in time" in failed["note"]
    assert len(plane.comments("OPERATIONS-10")) == 1                     # it was made; Traverse just didn't hear
    assert _send(client, push_id)["status"] == "sent"
    assert len(plane.comments("OPERATIONS-10")) == 1 and [w[0] for w in plane.writes] == ["POST"]


def test_an_item_gone_from_plane_gets_no_comment_and_a_deleted_task_takes_its_comment_with_it(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _comment(client, tid, "Called the broker.")
    plane.items("OPERATIONS").remove(plane.item("OPERATIONS-10"))
    failed = _send(client, _waiting(client)["id"])
    assert failed["status"] == "failed" and "isn't in Plane any more" in failed["note"] and plane.writes == []
    other = _bring(client, plane, "BD-8")
    _comment(client, other, "Sent the deck.")
    client.delete(f"/api/tasks/{other}")
    assert [p["task"] for p in client.get("/api/plane/outbox").json()["waiting"]] == [
        {"title": "Renew the insurance policy", "href": f"#/tasks/t/{tid}"}]
    assert plane.writes == []


def test_claude_cant_send_a_comment(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _comment(client, tid, "Called the broker.")
    push_id = _waiting(client)["id"]
    item = plane.item("OPERATIONS-10")
    token = mcp._calling.set("probe_send_it")                           # as if inside one of Claude's tools
    try:
        with pytest.raises(PermissionError):
            push.approve(push_id)
        with pytest.raises(PermissionError), pull.client() as c:
            c.create_comment(item["project"], item["id"], {"comment_html": "<p>Hi</p>"})
    finally:
        mcp._calling.reset(token)
    assert plane.writes == [] and _waiting(client)["status"] == "waiting"
