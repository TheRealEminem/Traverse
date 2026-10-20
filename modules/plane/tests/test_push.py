"""Pushing to Plane (chunk 7): every rule of PLAN.md §3.3, end to end against the fake Plane. Changes are made the way
the screens make them (the tasks API, "Send to Plane", the outbox's buttons), and what reached Plane is read from the
fake's record of every write."""
import pytest

from core.server import db, jobs, settings
from modules.plane.server import pull, push
from modules.plane.tests.fakeplane import MEMBERS, PROJECTS

MARK, ELI, MICKEY = MEMBERS["mark"], MEMBERS["eli"], MEMBERS["mickey"]


@pytest.fixture
def plane(pulled):
    """The fake workspace, pulled, with dry run off and nothing in Traverse yet."""
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


def _pull():
    pull.pull_now()
    jobs.drain()


def _state(project: str, name: str) -> str:
    return db.one("SELECT id FROM plane_states WHERE project_id = ? AND name = ?", (PROJECTS[project], name))["id"]


def _bring(client, fake, key: str) -> str:
    """Brings a Plane item into Traverse; returns its task's id."""
    item = fake.item(key)
    assert client.post("/api/plane/bring", json={"items": [item["id"]]}).json()["brought"] == 1
    return next(t["id"] for t in client.get("/api/tasks", params={"status": "all"}).json()
                if t["synced"] and t["synced"]["ref"] == f"plane:{item['id']}")


def _task(client, tid: str) -> dict:
    return client.get(f"/api/tasks/{tid}").json()


def _edit(client, tid: str, **changes) -> None:
    assert client.patch(f"/api/tasks/{tid}", json=changes).status_code == 200


def _share(client, tid: str) -> dict:
    r = client.post(f"/api/tasks/{tid}/share")
    assert r.status_code == 200, r.text
    return r.json()


def _waiting(client) -> dict:
    [found] = client.get("/api/plane/outbox").json()["waiting"]
    return found


def _send(client, push_id: str) -> dict:
    r = client.post(f"/api/plane/pushes/{push_id}/send")
    assert r.status_code == 200, r.text
    jobs.drain()
    return _push(client, push_id)


def _push(client, push_id: str) -> dict:
    box = client.get("/api/plane/outbox").json()
    return next(p for p in box["waiting"] + box["sent"] if p["id"] == push_id)


def _field(found: dict, name: str) -> dict:
    return next(f for f in found["fields"] if f["field"] == name)


def _writes(fake) -> list[tuple[str, dict]]:
    return [(method, body) for method, _, body in fake.writes]


# ── Rule 2: nothing is sent without approval ───────────────────────────

def test_send_to_plane_waits_for_you_and_shows_each_field(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31", priority=4)
    task = _share(client, tid)
    assert sorted(task["asked"]["fields"]) == ["due_on", "priority"] and task["asked"]["new"] is False
    assert task["sharing"] == [{"title": "Waiting for you to send it to Plane",
                                "href": f"#/plane/outbox?push={_waiting(client)['id']}"}]
    waiting = _waiting(client)
    assert waiting["status"] == "waiting" and waiting["job"]["status"] == "waiting"     # parked as "Needs you"
    assert waiting["task"]["title"] == "Renew the insurance policy" and waiting["item"]["key"] == "OPERATIONS-10"
    assert [(f["label"], f["before"], f["after"], f["include"]) for f in waiting["fields"]] == [
        ("Priority", "Medium", "Urgent", True), ("Due", "2026-10-16", "2026-10-31", True)]
    assert client.get("/api/plane/outbox/count").json() == {"waiting": 1}
    assert plane.writes == [] and {r.method for r in plane.requests} <= {"GET"}

    assert client.post(f"/api/plane/pushes/{waiting['id']}/discard").json()["status"] == "discarded"
    assert client.get("/api/plane/outbox").json()["waiting"] == []
    task = _task(client, tid)
    assert task["sharing"] == [] and sorted(task["synced"]["edited"]) == ["due_on", "priority"]   # still yours to send
    assert plane.writes == [] and plane.item("OPERATIONS-10")["target_date"] == "2026-10-16"


def test_asking_again_replaces_what_waits(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31")
    _share(client, tid)
    _edit(client, tid, text="Renew the insurance policy with the broker")
    _share(client, tid)
    waiting = _waiting(client)                                   # one push, now with both
    assert [f["field"] for f in waiting["fields"]] == ["text", "due_on"]
    with pytest.raises(AssertionError):
        _share(client, _bring(client, plane, "BD-8"))            # nothing changed there: nothing to send


# ── Rule 3: only the fields you changed are sent ───────────────────────

def test_only_the_changed_field_is_written_and_a_teammates_other_edit_survives(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31")
    _share(client, tid)
    plane.edit("OPERATIONS-10", name="Renew the insurance policy (broker has it)")     # a teammate, meanwhile
    sent = _send(client, _waiting(client)["id"])
    assert sent["status"] == "sent"
    assert _writes(plane) == [("PATCH", {"target_date": "2026-10-31"})]
    item = plane.item("OPERATIONS-10")
    assert (item["name"], item["target_date"]) == ("Renew the insurance policy (broker has it)", "2026-10-31")
    task = _task(client, tid)
    assert task["text"] == "Renew the insurance policy (broker has it)"     # followed: you hadn't changed it
    assert task["synced"]["edited"] == [] and task["synced"]["conflicts"] == [] and task["sharing"] == []


# ── Rule 4: check before writing ───────────────────────────────────────

def test_a_teammates_change_to_the_same_field_stops_the_push(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31")
    _share(client, tid)
    plane.edit("OPERATIONS-10", target_date="2026-10-24")                  # Mickey moved it in Plane
    stopped = _send(client, _waiting(client)["id"])
    assert stopped["status"] == "stopped" and "Due changed in Plane" in stopped["note"]
    due = _field(stopped, "due_on")
    assert (due["before"], due["theirs"], due["yours"]) == ("2026-10-16", "2026-10-24", "2026-10-31")
    assert plane.writes == [] and plane.item("OPERATIONS-10")["target_date"] == "2026-10-24"
    task = _task(client, tid)                                               # the task knows too
    assert task["due_on"] == "2026-10-31" and task["synced"]["conflicts"][0]["theirs"] == {"due_on": "2026-10-24"}
    assert client.post(f"/api/plane/pushes/{stopped['id']}/send").status_code == 400  # choose first

    r = client.post(f"/api/plane/pushes/{stopped['id']}/choose", json={"field": "due_on", "keep": "mine"})
    assert r.json()["status"] == "waiting" and _field(r.json(), "due_on")["over"]
    assert _send(client, stopped["id"])["status"] == "sent"
    assert _writes(plane) == [("PATCH", {"target_date": "2026-10-31"})]
    task = _task(client, tid)
    assert task["due_on"] == "2026-10-31" and task["synced"]["conflicts"] == [] and task["synced"]["edited"] == []


def test_keeping_planes_value_drops_it_from_the_push_and_the_task_takes_it(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31")
    _share(client, tid)
    plane.edit("OPERATIONS-10", target_date="2026-10-24")
    stopped = _send(client, _waiting(client)["id"])
    r = client.post(f"/api/plane/pushes/{stopped['id']}/choose", json={"field": "due_on", "keep": "plane"})
    assert r.json()["status"] == "discarded"                               # nothing left to send
    task = _task(client, tid)
    assert task["due_on"] == "2026-10-24" and task["synced"]["conflicts"] == [] and task["synced"]["edited"] == []
    assert plane.writes == []


def test_a_change_seen_by_a_pull_shows_in_the_preview_before_send(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31", priority=4)
    _share(client, tid)
    plane.edit("OPERATIONS-10", target_date="2026-10-24", priority="urgent")   # the due date, and the same priority
    _pull()
    waiting = _waiting(client)
    assert _field(waiting, "due_on")["changed"] and not _field(waiting, "due_on")["already"]
    assert _field(waiting, "priority")["already"] and not _field(waiting, "priority")["changed"]
    assert _field(waiting, "due_on")["before"] == "2026-10-24"


def test_sending_twice_writes_once(plane, client):
    """A push cut off after writing (Traverse stopped) goes again on restart: what's there already isn't rewritten."""
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31")
    _share(client, tid)
    push_id = _waiting(client)["id"]
    _send(client, push_id)
    db.execute("UPDATE plane_pushes SET status = 'sending' WHERE id = ?", (push_id,))
    jobs.enqueue("plane", push.KIND, push_id)
    jobs.drain()
    assert _push(client, push_id)["status"] == "sent" and [w[0] for w in plane.writes] == ["PATCH"]


# ── Rule 5: lists are merged, not replaced ─────────────────────────────

def test_an_assignee_added_in_plane_survives_a_push_that_adds_another(plane, client):
    tid = _bring(client, plane, "MARKETING-6")                              # yours
    _edit(client, tid, assignee_ref=f"plane:{MICKEY}", assignee_name="Mickey")
    _share(client, tid)
    waiting = _waiting(client)
    assert (_field(waiting, "assignee")["before"], _field(waiting, "assignee")["after"]) == ("Mark Morrison", "Mickey")
    plane.edit("MARKETING-6", assignees=[MARK, ELI])                       # Elijah added in Plane, meanwhile
    assert _send(client, waiting["id"])["status"] == "sent"
    assert _writes(plane) == [("PATCH", {"assignees": sorted([ELI, MICKEY])})]   # you're swapped for Mickey; Elijah stays
    task = _task(client, tid)
    assert task["assignee_ref"] == f"plane:{MICKEY}" and task["synced"]["edited"] == []
    assert task["synced"]["conflicts"] == []
    _pull()                                                                  # Plane says Elijah and Mickey: still Mickey here
    assert _task(client, tid)["assignee_ref"] == f"plane:{MICKEY}"


def test_someone_plane_doesnt_have_isnt_sent(plane, client):
    tid = _bring(client, plane, "MARKETING-6")
    _edit(client, tid, assignee_ref=None, assignee_name="Ana from the clinic", priority=4)
    _share(client, tid)
    waiting = _waiting(client)
    assignee = _field(waiting, "assignee")
    assert assignee["skip"] == "Ana from the clinic isn't in Plane" and not assignee["include"]
    assert client.patch(f"/api/plane/pushes/{waiting['id']}", json={"include": {"assignee": True}}).status_code == 400
    _send(client, waiting["id"])
    assert _writes(plane) == [("PATCH", {"priority": "urgent"})]
    assert _task(client, tid)["synced"]["edited"] == ["assignee"]           # still yours, here only


# ── Status and notes go out in Plane's terms ───────────────────────────

def test_status_goes_out_through_the_projects_state_map_and_reads_back_as_sent(plane, client):
    tid = _bring(client, plane, "MARKETING-6")
    _edit(client, tid, status="waiting")                                    # Marketing has no waiting state: In Progress
    _share(client, tid)
    _send(client, _waiting(client)["id"])
    assert _writes(plane) == [("PATCH", {"state": _state("MARKETING", "In Progress")})]
    task = _task(client, tid)
    assert task["status"] == "waiting" and task["synced"]["edited"] == []   # not "doing": it's what you sent
    _pull()
    assert _task(client, tid)["status"] == "waiting"
    plane.edit("MARKETING-6", state=_state("MARKETING", "Done"))
    _pull()
    plane.edit("MARKETING-6", state=_state("MARKETING", "In Progress"))     # someone else's In Progress now
    _pull()
    assert _task(client, tid)["status"] == "doing"


def test_notes_go_out_as_html_only_when_you_include_them(plane, client):
    tid = _bring(client, plane, "MARKETING-6")
    _edit(client, tid, notes="Draft the **outline** first\n\n- interview Ana\n- photos")
    _share(client, tid)
    waiting = _waiting(client)
    notes = _field(waiting, "notes")
    assert not notes["include"] and notes["after"] == "Draft the **outline** first\n\n- interview Ana\n- photos"
    r = client.post(f"/api/plane/pushes/{waiting['id']}/send")
    assert r.status_code == 400 and "at least one" in r.json()["detail"]
    client.patch(f"/api/plane/pushes/{waiting['id']}", json={"include": {"notes": True}})
    _send(client, waiting["id"])
    assert _writes(plane) == [("PATCH", {"description_html": "<p>Draft the <strong>outline</strong> first</p>"
                                                             "<ul><li><p>interview Ana</p></li><li><p>photos</p></li></ul>"})]
    assert _task(client, tid)["synced"]["edited"] == []


# ── New items ──────────────────────────────────────────────────────────

def test_a_task_made_in_traverse_is_created_in_plane_after_you_approve_then_edited(plane, client):
    client.post(f"/api/plane/links/{PROJECTS['SOFTWARE']}")
    project = client.get("/api/tasks/projects").json()[0]["id"]
    tid = client.post("/api/tasks", json={"text": "Write the API docs", "project_id": project, "status": "doing",
                                          "priority": 3, "due_on": "2026-11-06", "assignee_ref": "core:me"}).json()["id"]
    task = _share(client, tid)
    assert task["asked"]["new"] and task["synced"] is None
    waiting = _waiting(client)
    assert waiting["kind"] == "create" and waiting["item"] is None and waiting["project"]["name"] == "Software"
    assert [(f["label"], f["after"]) for f in waiting["fields"]] == [
        ("Title", "Write the API docs"), ("Status", "In Progress"), ("Priority", "High"), ("Due", "2026-11-06"),
        ("Assignee", "Mark Morrison")]
    assert plane.writes == []
    sent = _send(client, waiting["id"])
    assert sent["status"] == "sent" and sent["item"]["key"] == "SOFTWARE-6"
    assert _writes(plane) == [("POST", {"name": "Write the API docs", "state": _state("SOFTWARE", "In Progress"),
                                        "priority": "high", "target_date": "2026-11-06", "assignees": [MARK]})]
    task = _task(client, tid)
    assert task["synced"]["title"] == "SOFTWARE-6 Write the API docs" and task["synced"]["edited"] == []
    assert task["synced"]["url"].endswith("/browse/SOFTWARE-6/")
    assert client.post(f"/api/plane/pushes/{sent['id']}/undo").status_code == 400      # it would mean deleting

    _edit(client, tid, text="Write the API docs (v1)")
    _share(client, tid)
    _send(client, _waiting(client)["id"])
    assert _writes(plane)[-1] == ("PATCH", {"name": "Write the API docs (v1)"})
    assert plane.item("SOFTWARE-6")["name"] == "Write the API docs (v1)"


def test_a_create_whose_answer_was_lost_is_not_made_twice(plane, client):
    client.post(f"/api/plane/links/{PROJECTS['SOFTWARE']}")
    project = client.get("/api/tasks/projects").json()[0]["id"]
    tid = client.post("/api/tasks", json={"text": "Order the test rig", "project_id": project}).json()["id"]
    _share(client, tid)
    push_id = _waiting(client)["id"]
    plane.lose_next_answer = True
    failed = _send(client, push_id)
    assert failed["status"] == "failed" and "didn't answer" in failed["note"]
    assert _send(client, push_id)["status"] == "sent"                      # found the one it made
    assert [w[0] for w in plane.writes] == ["POST"]
    assert len([i for i in plane.items("SOFTWARE") if i["name"] == "Order the test rig"]) == 1
    assert _task(client, tid)["synced"]["title"] == "SOFTWARE-6 Order the test rig"


# ── Rule 6: only linked projects ───────────────────────────────────────

def test_a_private_project_has_nowhere_to_send(plane, client):
    project = client.post("/api/tasks/projects", json={"name": "Just mine"}).json()["id"]
    tid = client.post("/api/tasks", json={"text": "Private", "project_id": project}).json()["id"]
    r = client.post(f"/api/tasks/{tid}/share")
    assert r.status_code == 400 and "isn't linked anywhere" in r.json()["detail"]
    loose = client.post("/api/tasks", json={"text": "In no project"}).json()["id"]
    assert client.post(f"/api/tasks/{loose}/share").status_code == 400
    assert client.get("/api/plane/outbox").json()["waiting"] == [] and plane.writes == []


# ── Rule 7: everything sent is logged, and Undo ────────────────────────

def test_a_sent_push_is_logged_and_undo_is_a_push_with_the_same_check(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31", priority=4)
    _share(client, tid)
    sent = _send(client, _waiting(client)["id"])
    [logged] = client.get("/api/plane/outbox").json()["sent"]
    assert logged["id"] == sent["id"] and logged["approved_at"] and logged["sent_at"]
    assert [(f["label"], f["before"], f["after"]) for f in logged["fields"]] == [
        ("Priority", "Medium", "Urgent"), ("Due", "2026-10-16", "2026-10-31")]

    undo = client.post(f"/api/plane/pushes/{sent['id']}/undo")
    assert undo.status_code == 201 and undo.json()["kind"] == "undo" and undo.json()["status"] == "waiting"
    assert [(f["label"], f["before"], f["after"]) for f in undo.json()["fields"]] == [
        ("Priority", "Urgent", "Medium"), ("Due", "2026-10-31", "2026-10-16")]
    assert client.post(f"/api/plane/pushes/{sent['id']}/undo").status_code == 400      # once
    assert len(plane.writes) == 1                                                       # waits for you, like any push
    _send(client, undo.json()["id"])
    assert _writes(plane)[-1] == ("PATCH", {"priority": "medium", "target_date": "2026-10-16"})
    task = _task(client, tid)
    assert (task["due_on"], task["priority"]) == ("2026-10-16", 2) and task["synced"]["edited"] == []
    assert _push(client, sent["id"])["undone"]["status"] == "sent"


def test_undo_stops_if_plane_changed_since(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31")
    _share(client, tid)
    sent = _send(client, _waiting(client)["id"])
    undo_id = client.post(f"/api/plane/pushes/{sent['id']}/undo").json()["id"]
    plane.edit("OPERATIONS-10", target_date="2026-11-14")
    stopped = _send(client, undo_id)
    assert stopped["status"] == "stopped" and _field(stopped, "due_on")["theirs"] == "2026-11-14"
    assert len(plane.writes) == 1
    client.post(f"/api/plane/pushes/{undo_id}/discard")
    assert _push(client, sent["id"])["undone"] is None                      # can be undone again later


def test_undo_after_sending_over_a_change_in_plane_puts_back_plane_s_value(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31")
    _share(client, tid)
    plane.edit("OPERATIONS-10", target_date="2026-10-24")                  # a teammate's date, unseen in Traverse
    push_id = _waiting(client)["id"]
    _send(client, push_id)
    client.post(f"/api/plane/pushes/{push_id}/choose", json={"field": "due_on", "keep": "mine"})
    _send(client, push_id)
    undo_id = client.post(f"/api/plane/pushes/{push_id}/undo").json()["id"]
    assert _field(_push(client, undo_id), "due_on")["after"] == "2026-10-24"
    _send(client, undo_id)
    assert plane.item("OPERATIONS-10")["target_date"] == "2026-10-24"
    task = _task(client, tid)                                               # the task follows Plane, not its old base
    assert task["due_on"] == "2026-10-24" and task["synced"]["edited"] == [] and task["synced"]["conflicts"] == []


def test_undo_puts_back_the_list_it_changed_and_keeps_later_additions(plane, client):
    tid = _bring(client, plane, "MARKETING-6")
    _edit(client, tid, assignee_ref=f"plane:{MICKEY}", assignee_name="Mickey")
    _share(client, tid)
    sent = _send(client, _waiting(client)["id"])                           # Mark → Mickey
    plane.edit("MARKETING-6", assignees=[MICKEY, ELI])                     # then Elijah joins in Plane
    _pull()
    undo_id = client.post(f"/api/plane/pushes/{sent['id']}/undo").json()["id"]
    _send(client, undo_id)
    assert _writes(plane)[-1] == ("PATCH", {"assignees": sorted([MARK, ELI])})


# ── Rule 8: dry run ────────────────────────────────────────────────────

def test_dry_run_checks_and_previews_but_never_sends(plane, client):
    settings.update({"plane.dry_run": True})
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31")
    _share(client, tid)
    push_id = _waiting(client)["id"]
    plane.requests.clear()
    tried = _send(client, push_id)
    assert tried["status"] == "waiting" and tried["note"].startswith("Dry run: checked against Plane. Send would change Due")
    assert plane.writes == [] and {r.method for r in plane.requests} == {"GET"}
    assert client.get("/api/plane/outbox").json()["dry_run"] is True
    assert _task(client, tid)["synced"]["edited"] == ["due_on"]
    settings.update({"plane.dry_run": False})
    assert _send(client, push_id)["status"] == "sent" and _writes(plane) == [("PATCH", {"target_date": "2026-10-31"})]


def test_a_dry_run_still_stops_on_a_conflict(plane, client):
    settings.update({"plane.dry_run": True})
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31")
    _share(client, tid)
    plane.edit("OPERATIONS-10", target_date="2026-10-24")
    assert _send(client, _waiting(client)["id"])["status"] == "stopped" and plane.writes == []


# ── When Plane says no ─────────────────────────────────────────────────

def test_plane_saying_no_shows_why_and_send_tries_again(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31")
    _share(client, tid)
    push_id = _waiting(client)["id"]
    plane.fail(f"PATCH {plane.item_path('OPERATIONS-10')}", (400, {}))
    failed = _send(client, push_id)
    assert failed["status"] == "failed" and "Plane said no" in failed["note"]
    assert client.get("/api/plane/outbox/count").json() == {"waiting": 1}
    assert _send(client, push_id)["status"] == "sent"


def test_an_item_gone_from_plane_isnt_written(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31")
    _share(client, tid)
    plane.items("OPERATIONS").remove(plane.item("OPERATIONS-10"))
    failed = _send(client, _waiting(client)["id"])
    assert failed["status"] == "failed" and "isn't in Plane any more" in failed["note"] and plane.writes == []


# ── Rule 1: never a delete ─────────────────────────────────────────────

def test_deleting_or_unlinking_in_traverse_sends_nothing_to_plane(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    _edit(client, tid, due_on="2026-10-31")
    _share(client, tid)
    other = _bring(client, plane, "BD-8")
    client.delete(f"/api/tasks/{other}/synced")
    client.delete(f"/api/tasks/{tid}")                                      # its waiting push goes with it
    assert client.get("/api/plane/outbox").json()["waiting"] == []
    client.delete(f"/api/plane/links/{PROJECTS['BD']}")
    project = client.get("/api/tasks/projects").json()[0]["id"]
    client.delete(f"/api/tasks/projects/{project}")
    _pull()
    assert plane.writes == [] and {r.method for r in plane.requests} == {"GET"}
    assert plane.item("OPERATIONS-10")["target_date"] == "2026-10-16" and plane.item("BD-8")
