"""plane/pull: it mirrors the chosen projects, running it twice changes nothing, and it never writes to Plane."""
from core.server import db, events, jobs, settings
from modules.plane.server import pull, store
from modules.plane.tests.fakeplane import PROJECTS, REAL_PROJECTS, mirror_rows


def _pull() -> dict:
    pull.pull_now()
    jobs.drain()
    return db.one("SELECT status, error FROM core_jobs WHERE module = 'plane' AND kind = 'pull'")


def test_a_pull_mirrors_the_chosen_projects_and_the_workspace(fake_plane):
    assert _pull()["status"] == "done"
    counts = store.counts()
    assert counts["projects"] == 8                    # every project, so Settings can offer them
    assert counts["members"] == 5                     # bots too; the directory and the Team view leave them out
    assert counts["states"] == 7 * 5                  # only the 7 mirrored projects' states...
    assert counts["items"] == 49                      # ...and items: not the demo project's 7
    assert (counts["labels"], counts["cycles"]) == (3, 1)
    assert not db.query("SELECT 1 FROM plane_items WHERE project_id = ?", (PROJECTS["COLDC"],))
    item = db.one("SELECT * FROM plane_items i JOIN plane_projects p ON p.id = i.project_id "
                  "WHERE p.identifier = 'BD' AND i.sequence_id = 14")
    assert item["name"] == "Send the grant letter of intent" and item["target_date"] == "2026-10-07"
    assert item["cycle_id"] and item["labels"].startswith('["')
    assert store.meta("me") == fake_plane.data["/api/v1/users/me/"]["id"]


def test_running_it_twice_changes_nothing(fake_plane):
    heard = []
    events.subscribe("plane.mirror.changed", heard.append)
    _pull()
    first = mirror_rows()
    assert store.meta("last_pull")["changed"] == 8 + 5 + 35 + 3 + 1 + 49
    assert len(heard) == 1
    _pull()
    assert mirror_rows() == first
    assert store.meta("last_pull")["changed"] == 0
    assert len(heard) == 1                              # nothing changed, so nothing was announced


def test_a_change_in_plane_changes_just_that_row(fake_plane):
    _pull()
    before = mirror_rows()
    fake_plane.item("SOFTWARE-5")["name"] = "Share the GitHub repos with Mark"
    fake_plane.item("SOFTWARE-5")["updated_at"] = "2026-10-19T08:00:00Z"
    _pull()
    after = mirror_rows()
    assert store.meta("last_pull")["changed"] == 1
    changed = [r for r in after["plane_items"] if r not in before["plane_items"]]
    assert [r["name"] for r in changed] == ["Share the GitHub repos with Mark"]
    assert {t: v for t, v in after.items() if t != "plane_items"} == {t: v for t, v in before.items() if t != "plane_items"}


def test_something_gone_from_plane_is_marked_not_deleted_and_comes_back(fake_plane):
    _pull()
    gone = fake_plane.item("BD-10")
    fake_plane.items("BD").remove(gone)
    _pull()
    row = db.one("SELECT removed_at FROM plane_items WHERE id = ?", (gone["id"],))
    assert row and row["removed_at"]                    # kept, so a linked task can say "Removed in Plane" later
    assert store.counts()["items"] == 48
    _pull()
    assert store.meta("last_pull")["changed"] == 0      # marking it gone happens once
    fake_plane.items("BD").append(gone)
    _pull()
    assert db.one("SELECT removed_at FROM plane_items WHERE id = ?", (gone["id"],))["removed_at"] is None


def test_a_pull_that_fails_half_way_writes_nothing_and_says_why(fake_plane):
    path = f"/api/v1/workspaces/cold-connect/projects/{PROJECTS['BD']}/work-items/"
    fake_plane.fail(path, *[502] * 5)
    job = _pull()
    assert job["status"] == "error" and "Plane had a problem (502)" in job["error"]
    assert store.counts() == {t: 0 for t in store.counts()}
    assert store.meta("last_pull") is None


def test_a_pull_only_ever_reads(fake_plane):
    _pull()
    assert fake_plane.requests and {r.method for r in fake_plane.requests} == {"GET"}


def test_a_workspace_key_without_the_members_list_gathers_project_members(fake_plane):
    fake_plane.fail("/api/v1/workspaces/cold-connect/members/", 403)
    for pid in REAL_PROJECTS:
        fake_plane.data[f"/api/v1/workspaces/cold-connect/projects/{pid}/members/"] = [
            {"id": f"pm-{pid[:4]}-{m['id'][:4]}", "member": m, "role": 15} for m in fake_plane.data["/api/v1/workspaces/cold-connect/members/"][1:3]]
    assert _pull()["status"] == "done"
    assert {m["display_name"] for m in store.members(include_bots=True)} == {"eli", "mickey"}


def test_without_a_key_it_waits_for_settings(fake_plane, client):
    settings.update({"plane.personal_api_key": ""})
    assert pull.every() == 0                            # the schedule leaves it alone
    r = client.post("/api/plane/pull")
    assert r.status_code == 400 and "Settings → Plane" in r.json()["detail"]
    settings.update({"plane.personal_api_key": "plane_api_test", "plane.pull_minutes": 15})
    assert pull.every() == 15 * 60
    settings.update({"plane.pull_minutes": 0})
    assert pull.every() == 0                            # only when you press "Pull now"


def test_the_key_is_never_sent_back_to_the_page(fake_plane, client):
    r = client.put("/api/settings", json={"plane.personal_api_key": "plane_api_test"})
    assert r.json()["values"]["plane.personal_api_key"] == ""
    assert r.json()["secret_hints"]["plane.personal_api_key"] == "…test"
    assert "plane_api_test" not in client.get("/api/settings").text
    assert "plane_api_test" not in client.get("/api/plane/status").text


def test_saving_the_projects_pulls_again_and_pull_now_never_doubles_up(fake_plane, client):
    client.put("/api/settings", json={"plane.projects": REAL_PROJECTS[:2]})
    jobs.drain()
    assert store.counts()["items"] == sum(len(fake_plane.items(i)) for i in ("OPERATIONS", "CUSTO"))
    parked = jobs.enqueue("plane", "pull", pull.TARGET, approve=True)        # one already waiting
    assert client.post("/api/plane/pull").json()["job"] == parked            # is started, not doubled
    jobs.drain()
    assert len(db.query("SELECT 1 FROM core_jobs WHERE module = 'plane' AND kind = 'pull'")) == 1


def test_the_connection_test_says_who_and_where(fake_plane, client):
    r = client.post("/api/plane/test")
    assert r.status_code == 200
    assert r.json()["message"] == "Connected to cold-connect as Mark Morrison. 8 projects to choose from."
    jobs.drain()
    assert store.counts()["projects"] == 8               # it queued a pull, so Settings can list the projects
    settings.update({"plane.workspace_slug": "cold-conect"})
    r = client.post("/api/plane/test")
    assert r.status_code == 502 and "no workspace called “cold-conect”" in r.json()["detail"]
    settings.update({"plane.workspace_slug": "cold-connect", "plane.personal_api_key": "an-old-key"})
    r = client.post("/api/plane/test")
    assert r.status_code == 502 and "didn't accept the API key" in r.json()["detail"]


def test_search_and_links_describe_plane_items_and_people(pulled, client):
    groups = client.get("/api/search", params={"q": "BD-14"}).json()
    hits = next(g for g in groups if g["module"] == "plane")["hits"]
    assert hits[0]["title"] == "BD-14 Send the grant letter of intent"
    from core.server import module
    eli = next(m for m in store.members() if m["display_name"] == "eli")
    assert module.describe(f"plane:{eli['id']}")["title"] == "Elijah Anderson-Justis"
