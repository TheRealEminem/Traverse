"""Claude and Plane (chunk 11): the plane module's tools read the mirror and the outbox, and no tool, in any module,
can write to Plane. Claude proposes a push the way you do (tasks_propose_send); only your Send in the outbox writes,
and here dry run is off, so that's the only thing standing in the way."""
import ast
import inspect
import json
from pathlib import Path

import pytest

from core.server import db, jobs, mcp, module, settings
from core.server.mcp import Tool
from modules.plane.server import pull, push
from modules.plane.tests.fakeplane import PROJECTS


@pytest.fixture
def plane(pulled, client):
    """The fake workspace, pulled, with dry run OFF, nothing in Traverse yet, and Claude's access on."""
    def wipe():
        for t in ("tasks_synced", "tasks_blockers", "tasks_updates", "tasks_items", "tasks_milestones", "tasks_projects",
                  "tasks_fts", "plane_links", "plane_pushes", "plane_sent", "inbox_proposals", "inbox_captures",
                  "inbox_fts"):
            db.execute(f"DELETE FROM {t}")
        db.execute("DELETE FROM core_links")
    wipe()
    settings.update({"plane.dry_run": False})
    pulled.requests.clear()
    made = client.post("/api/mcp/token").json()["setup"]["claude_code"]
    pulled.token = made.rsplit("Bearer ", 1)[1].rstrip('"')
    yield pulled
    jobs.drain()
    client.delete("/api/mcp/token")
    wipe()


def call(client, fake, name: str, **args) -> dict:
    """Through /mcp, as Claude Code calls it."""
    r = client.post("/mcp", headers={"Authorization": f"Bearer {fake.token}"}, json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}})
    assert r.status_code == 200, r.text
    result = r.json()["result"]
    text = result["content"][0]["text"]
    return {"error": text} if result["isError"] else json.loads(text)


def _bring(client, fake, key: str) -> str:
    item = fake.item(key)
    assert client.post("/api/plane/bring", json={"items": [item["id"]]}).json()["brought"] == 1
    return next(t["id"] for t in client.get("/api/tasks", params={"status": "all"}).json()
                if t["synced"] and t["synced"]["ref"] == f"plane:{item['id']}")


# ── Reading ───────────────────────────────────────────────────────────

def test_team_workload_matches_the_team_view(plane, client):
    found = call(client, plane, "plane_team_workload")
    assert found["totals"]["open"] == 34
    assert {p["name"]: p["open"] for p in found["people"]} == {
        "Mark Morrison (you)": 23, "Mickey": 5, "Elijah Anderson-Justis": 2, "No one": 4}
    assert found["items_shown"] == "Past due" and all(i["past_due"] for i in found["items"])
    mickey = call(client, plane, "plane_team_workload", person="mickey")
    assert mickey["items_shown"] == "Mickey's open items" and len(mickey["items"]) == 5
    assert all(i["assignees"] == ["Mickey"] for i in mickey["items"])
    assert len(call(client, plane, "plane_team_workload", person="no one")["items"]) == 4
    assert len(call(client, plane, "plane_team_workload", person="me")["items"]) == 23
    software = call(client, plane, "plane_team_workload", project="software")
    assert software["items_shown"] == "Open items in Software" and len(software["items"]) == 3
    assert software["items"][0]["url"].startswith("https://app.plane.so/cold-connect/browse/SOFTWARE-")
    assert call(client, plane, "plane_team_workload", person="Zed")["error"].startswith("No one called “Zed”")
    assert plane.requests == []                                       # the mirror only, never Plane


def test_the_outbox_shows_what_waits_and_says_only_you_can_send(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    client.patch(f"/api/tasks/{tid}", json={"due_on": "2026-10-31"})
    assert call(client, plane, "plane_outbox")["waiting"] == []
    call(client, plane, "tasks_propose_send", task=f"tasks:{tid}")
    box = call(client, plane, "plane_outbox")
    [waiting] = box["waiting"]
    assert waiting["plane_item"].startswith("OPERATIONS-10 ") and waiting["what"] == "Change it in Plane"
    assert waiting["status"] == "Waiting for you to send it"
    assert waiting["fields"] == [{"field": "Due", "in_plane_now": plane.item("OPERATIONS-10")["target_date"] or "None",
                                  "will_be": "2026-10-31", "included": True}]
    assert box["dry_run"] is False and "Only the user can send these" in box["note"]
    settings.update({"plane.dry_run": True})
    assert "Dry run is on" in call(client, plane, "plane_outbox")["note"]


# ── Nothing reaches Plane from a tool ─────────────────────────────────

# Every tool, with arguments that make it do the most it can. A new tool must be added here.
def _samples(task_id: str, new_id: str, project_ref: str) -> dict[str, list[dict]]:
    return {
        "tasks_my_plate": [{}, {"when": "all"}],
        "tasks_find": [{"q": "OPERATIONS"}, {"project": "Software"}],
        "tasks_add": [{"text": "Write the release notes", "project": "Software", "due_on": "2026-10-30"}],
        "tasks_propose_send": [{"task": f"tasks:{task_id}"}, {"task": f"tasks:{new_id}"}],
        "plane_team_workload": [{}, {"person": "me"}],
        "plane_outbox": [{}],
        "inbox_capture": [{"text": "Eli: I'll post the specs Friday", "project": project_ref,
                           "items": [{"text": "Post the specs", "assignee": "Eli", "due_on": "2026-10-23"}]}],
    }


def test_no_tool_can_write_to_plane(plane, client):
    tid = _bring(client, plane, "OPERATIONS-10")
    client.patch(f"/api/tasks/{tid}", json={"due_on": "2026-10-31", "priority": 4})
    client.post(f"/api/plane/links/{PROJECTS['SOFTWARE']}")
    software = next(p for p in client.get("/api/tasks/projects").json() if p["name"] == "Software")
    new_id = client.post("/api/tasks", json={"text": "Write the API docs", "project_id": software["id"]}).json()["id"]
    plane.requests.clear()

    samples = _samples(tid, new_id, f"tasks:{software['id']}")
    assert set(samples) == {name for name, _, _ in mcp.tools()}, "a tool without a sample here isn't checked"
    for name, runs in samples.items():
        for args in runs:
            assert "error" not in call(client, plane, name, **args), (name, args)
    jobs.drain()

    assert plane.writes == [] and plane.requests == []               # not a write, not even a read
    pushes = db.query("SELECT kind, status, approved_at FROM plane_pushes ORDER BY kind")
    assert [(p["kind"], p["status"], p["approved_at"]) for p in pushes] == [("create", "waiting", None),
                                                                            ("update", "waiting", None)]
    assert {j["status"] for j in db.query("SELECT status FROM core_jobs WHERE module = 'plane' AND kind = 'push'")} == {"waiting"}
    assert plane.item("OPERATIONS-10")["priority"] != "urgent"

    # Your Send is what writes (dry run is off here).
    update = db.one("SELECT id FROM plane_pushes WHERE kind = 'update'")["id"]
    assert client.post(f"/api/plane/pushes/{update}/send").status_code == 200
    jobs.drain()
    assert [method for method, _, _ in plane.writes] == ["PATCH"]


def test_inside_a_tool_sending_and_the_client_both_refuse(plane, client, monkeypatch):
    tid = _bring(client, plane, "OPERATIONS-10")
    client.patch(f"/api/tasks/{tid}", json={"priority": 4})
    client.post(f"/api/tasks/{tid}/share")
    push_id = db.one("SELECT id FROM plane_pushes")["id"]
    item = plane.item("OPERATIONS-10")

    def send_it(args):
        push.approve(push_id)

    def write_it(args):
        with pull.client() as c:
            c.update_work_item(item["project"], item["id"], {"priority": "urgent"})

    monkeypatch.setattr(module.get("probe"), "tools", [
        Tool(name="send_it", title="Send it", description="Presses Send.", handler=send_it, writes=True),
        Tool(name="write_it", title="Write it", description="Writes to Plane.", handler=write_it, writes=True)])
    assert call(client, plane, "probe_send_it")["error"] == "Claude can't send to Plane. Only you can, with Send in the outbox."
    assert call(client, plane, "probe_write_it")["error"] == "Claude can't write to Plane. Only a push you send from the outbox can."
    jobs.drain()
    assert plane.writes == []
    assert db.one("SELECT status, approved_at FROM plane_pushes WHERE id = ?", (push_id,)) == {"status": "waiting",
                                                                                           "approved_at": None}


FORBIDDEN = {("jobs", "go"), ("jobs", "retry"), ("settings", "update"), ("push", "approve"), ("push", "send"),
             ("push", "undo"), ("push", "choose"), ("push", "include"), ("push", "discard")}
FORBIDDEN_ANYWHERE = {"update_work_item", "create_work_item", "create_comment", "_send", "client"}


def test_no_tools_code_names_a_way_to_send_approve_or_change_settings():
    """The runtime guards above stop it; this keeps the tools' own code from even trying."""
    files = {Path(inspect.getsourcefile(t.handler)) for _, _, t in mcp.tools() if t.handler.__module__ != __name__}
    assert {f.parent.parent.name for f in files} >= {"tasks", "plane", "inbox"}
    for path in files:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Attribute):
                owner = node.value.id if isinstance(node.value, ast.Name) else None
                assert (owner, node.attr) not in FORBIDDEN, f"{path.name}: {owner}.{node.attr} (line {node.lineno})"
                assert node.attr not in FORBIDDEN_ANYWHERE, f"{path.name}: .{node.attr} (line {node.lineno})"
            if isinstance(node, ast.ImportFrom):
                assert not any(a.name in ("client", "pull", "linking") for a in node.names), f"{path.name} imports {node.module}"
