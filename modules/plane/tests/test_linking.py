"""Linking (chunk 6): Plane projects go to Traverse projects with a state map, Plane items come in as linked tasks,
and a change in Plane reaches the local copy with the next pull. Traverse is looked at through its own API (the
tasks module's), the way the screens see it; nothing is ever sent to Plane."""
import pytest

from core.server import db, jobs
from modules.plane.server import html, linking
from modules.plane.tests.fakeplane import PROJECTS


@pytest.fixture(autouse=True)
def no_tasks():
    """Every test starts with nothing in Traverse (the tasks module's tables, emptied between tests)."""
    def wipe():
        for t in ("tasks_synced", "tasks_blockers", "tasks_updates", "tasks_items", "tasks_milestones", "tasks_projects",
                  "tasks_fts", "plane_links"):
            db.execute(f"DELETE FROM {t}")
        db.execute("DELETE FROM core_links")
    wipe()
    yield
    wipe()


def _pull():
    from modules.plane.server import pull
    pull.pull_now()
    jobs.drain()
    assert db.one("SELECT status, error FROM core_jobs WHERE module = 'plane' ORDER BY rowid DESC LIMIT 1")["status"] == "done"


def _state(project: str, name: str) -> str:
    return db.one("SELECT id FROM plane_states WHERE project_id = ? AND name = ?", (PROJECTS[project], name))["id"]


def _task_for(client, key: str) -> dict:
    """The linked task of a Plane item, by its key ("SOFTWARE-5")."""
    ident, _, seq = key.rpartition("-")
    item = db.one("SELECT id FROM plane_items WHERE project_id = ? AND sequence_id = ?", (PROJECTS[ident], int(seq)))
    found = [t for t in client.get("/api/tasks", params={"status": "all"}).json()
             if t["synced"] and t["synced"]["ref"] == f"plane:{item['id']}"]
    assert len(found) == 1, f"{key} isn't in Traverse"
    return client.get(f"/api/tasks/{found[0]['id']}").json()


def test_each_status_is_preset_to_a_state_of_its_group(pulled):
    preset = linking.default_map(PROJECTS["SOFTWARE"])
    assert preset == {"todo": _state("SOFTWARE", "Todo"), "doing": _state("SOFTWARE", "In Progress"),
                      "waiting": _state("SOFTWARE", "In Progress"), "done": _state("SOFTWARE", "Done"),
                      "dropped": _state("SOFTWARE", "Cancelled")}


def test_linking_makes_a_traverse_project_or_uses_yours(pulled, client):
    r = client.post(f"/api/plane/links/{PROJECTS['SOFTWARE']}")
    assert r.status_code == 200 and r.json()["link"]["title"] == "Software"
    made = client.get("/api/tasks/projects").json()
    assert [(p["name"], [s["title"] for s in p["synced_with"]]) for p in made] == [("Software", ["Software"])]
    assert client.post(f"/api/plane/links/{PROJECTS['SOFTWARE']}").status_code == 400          # linked already

    mine = client.post("/api/tasks/projects", json={"name": "Grant work"}).json()["id"]
    r = client.post(f"/api/plane/links/{PROJECTS['BD']}", json={"local_ref": f"tasks:{mine}"})
    assert r.json()["link"]["title"] == "Grant work"
    r = client.post(f"/api/plane/links/{PROJECTS['INFRA']}", json={"local_ref": f"tasks:{mine}"})
    assert r.status_code == 400 and "linked to Business Development" in r.json()["detail"]
    assert client.post("/api/plane/links/nope").status_code == 404

    assert client.delete(f"/api/plane/links/{PROJECTS['BD']}").status_code == 204          # both projects stay
    assert {p["name"] for p in client.get("/api/tasks/projects").json()} == {"Software", "Grant work"}
    client.delete(f"/api/tasks/projects/{made[0]['id']}")                                     # gone here: unlinked
    assert not db.one("SELECT 1 FROM plane_links")


def test_bringing_in_everything_assigned_to_me(pulled, client):
    r = client.post("/api/plane/bring", json={"mine": True}).json()
    assert r["brought"] == 23 and r["already"] == 0
    assert sorted(r["new_projects"]) == ["Business Development", "Customer Relationships", "Hardware", "Infrastructure",
                                         "Marketing", "Operations", "Software"]             # one per Plane project
    tasks = client.get("/api/tasks", params={"status": "all"}).json()
    assert len(tasks) == 23 and all(t["synced"] and t["source"] == "linked" for t in tasks)
    assert all(t["assignee_ref"] == "core:me" for t in tasks)
    assert {s: sum(t["status"] == s for t in tasks) for s in ("todo", "doing")} == {"todo": 11, "doing": 12}
    by_project = {}
    for t in tasks:
        by_project[t["project_id"]] = by_project.get(t["project_id"], 0) + 1
    names = {p["id"]: p["name"] for p in client.get("/api/tasks/projects").json()}
    assert {names[k]: v for k, v in by_project.items()} == {
        "Business Development": 9, "Customer Relationships": 1, "Hardware": 3, "Infrastructure": 4, "Marketing": 2,
        "Operations": 3, "Software": 1}
    again = client.post("/api/plane/bring", json={"mine": True}).json()
    assert (again["brought"], again["already"], again["new_projects"]) == (0, 23, [])
    team = client.get("/api/plane/team").json()
    assert sum(1 for i in team["items"] if i["task"]) == 23
    assert all(p["linked"] for p in team["projects"] if p["people"].get(pulled.data["/api/v1/users/me/"]["id"]))


def test_one_item_comes_in_with_its_fields(pulled, client):
    item = pulled.item("SOFTWARE-5")
    assert client.post("/api/plane/bring", json={"items": [item["id"]]}).json()["brought"] == 1
    task = _task_for(client, "SOFTWARE-5")
    assert (task["text"], task["notes"], task["priority"], task["due_on"], task["status"]) == \
        ("Share GitHub repos with Dale", "Share GitHub repos with Dale.", 3, "2026-10-13", "todo")
    assert task["synced"]["url"].endswith("/cold-connect/browse/SOFTWARE-5/") and task["synced"]["source"] == "Plane"
    assert task["synced"]["title"] == "SOFTWARE-5 Share GitHub repos with Dale"


def test_editing_an_item_in_plane_updates_its_copy_within_a_pull(pulled, client):
    item = pulled.item("SOFTWARE-5")
    client.post("/api/plane/bring", json={"items": [item["id"]]})
    item.update(name="Share the GitHub repos with Dale", target_date="2026-10-24", priority="urgent",
                state=_state("SOFTWARE", "In Progress"), updated_at="2026-10-20T09:00:00Z")
    _pull()
    task = _task_for(client, "SOFTWARE-5")
    assert (task["text"], task["due_on"], task["priority"], task["status"]) == \
        ("Share the GitHub repos with Dale", "2026-10-24", 4, "doing")
    assert task["synced"]["conflicts"] == []


def test_a_field_changed_on_both_sides_is_flagged_and_the_rest_follows(pulled, client):
    item = pulled.item("SOFTWARE-5")
    client.post("/api/plane/bring", json={"items": [item["id"]]})
    tid = _task_for(client, "SOFTWARE-5")["id"]
    client.patch(f"/api/tasks/{tid}", json={"due_on": "2026-10-31"})
    item.update(target_date="2026-10-27", name="Renamed in Plane", updated_at="2026-10-20T09:00:00Z")
    _pull()
    task = _task_for(client, "SOFTWARE-5")
    assert task["due_on"] == "2026-10-31" and task["text"] == "Renamed in Plane"
    assert task["synced"]["conflicts"] == [{"field": "due_on", "label": "Due", "theirs": {"due_on": "2026-10-27"}}]
    r = client.post(f"/api/tasks/{tid}/synced", json={"field": "due_on", "keep": "theirs"}).json()
    assert r["due_on"] == "2026-10-27" and r["synced"]["conflicts"] == []


def test_removed_in_plane_keeps_the_copy(pulled, client):
    item = pulled.item("BD-10")
    client.post("/api/plane/bring", json={"items": [item["id"]]})
    pulled.items("BD").remove(item)
    _pull()
    task = _task_for(client, "BD-10")
    assert task["synced"]["removed_at"] and task["text"] == item["name"]
    pulled.items("BD").append(item)
    _pull()
    assert _task_for(client, "BD-10")["synced"]["removed_at"] is None


def test_the_state_map_decides_what_a_state_means(pulled, client):
    item = pulled.item("SOFTWARE-5")
    item["state"] = _state("SOFTWARE", "In Progress")
    _pull()
    client.post("/api/plane/bring", json={"items": [item["id"]]})
    assert _task_for(client, "SOFTWARE-5")["status"] == "doing"
    r = client.patch(f"/api/plane/links/{PROJECTS['SOFTWARE']}",
                     json={"state_map": {"waiting": _state("SOFTWARE", "In Progress"), "doing": _state("SOFTWARE", "Todo")}})
    assert r.json()["link"]["state_map"]["waiting"] == _state("SOFTWARE", "In Progress")
    assert _task_for(client, "SOFTWARE-5")["status"] == "waiting"            # followed at once: you hadn't changed it
    bad = client.patch(f"/api/plane/links/{PROJECTS['SOFTWARE']}", json={"state_map": {"waiting": _state("BD", "Todo")}})
    assert bad.status_code == 400
    assert client.patch(f"/api/plane/links/{PROJECTS['SOFTWARE']}", json={"state_map": {"later": "x"}}).status_code == 400


def test_the_linking_page_and_nothing_sent_to_plane(pulled, client):
    pulled.requests.clear()
    client.post(f"/api/plane/links/{PROJECTS['SOFTWARE']}")
    client.post("/api/plane/bring", json={"mine": True})
    _pull()
    page = client.get("/api/plane/links").json()
    assert page["mine"] == 23 and page["mine_waiting"] == []
    software = next(p for p in page["projects"] if p["identifier"] == "SOFTWARE")
    assert software["link"]["title"] == "Software" and [s["name"] for s in software["states"]][:2] == ["Backlog", "Todo"]
    assert {r.method for r in pulled.requests} == {"GET"}


def test_plane_descriptions_read_as_markdown():
    assert html.to_markdown('<p class="editor-paragraph-block">Share GitHub repos with Dale.</p>') == \
        "Share GitHub repos with Dale."
    assert html.to_markdown("<p></p>") == "" and html.to_markdown(None) == ""
    assert html.to_markdown('<p>One <strong>bold</strong> <a href="https://x.test">link</a></p><p>Two</p>') == \
        "One **bold** [link](https://x.test)\n\nTwo"
    assert html.to_markdown("<p>Steps</p><ul><li><p>First</p></li><li><p>Then</p><ul><li><p>Inside</p></li></ul></li></ul>") \
        == "Steps\n\n- First\n- Then\n  - Inside"
    assert html.to_markdown('<ul data-type="taskList"><li data-checked="true"><p>Done</p></li>'
                            '<li data-checked="false"><p>Open</p></li></ul>') == "- [x] Done\n- [ ] Open"
    assert html.to_markdown("<h2>Plan</h2><p>a<br>b</p><pre><code>x = 1\ny = 2</code></pre>") == \
        "## Plan\n\na\nb\n\n```\nx = 1\ny = 2\n```"
    assert html.to_markdown("<p>Use <code>git push</code> &amp; wait</p>") == "Use `git push` & wait"
