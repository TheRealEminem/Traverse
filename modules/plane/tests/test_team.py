"""The Team view's rollups, checked against what Plane showed on 2026-10-18: 34 open items, Mark 23, Sam 5,
Alex 2 and 4 with no one, leaving out the "Acme Team" demo project."""
from datetime import date

from core.server import db, jobs, settings
from modules.plane.server import team
from modules.plane.tests.fakeplane import MEMBERS, PROJECTS, REAL_PROJECTS

DAY = date(2026, 10, 18)


def _people(r):
    return {p["name"]: p for p in r["people"]}


def test_open_items_by_person_match_plane(pulled):
    r = team.rollup(DAY)
    assert r["totals"]["open"] == 34
    people = _people(r)
    assert {name: p["open"] for name, p in people.items()} == {
        "Mark Morrison": 23, "Sam": 5, "Alex Rivera": 2, "No one": 4}
    assert [p["name"] for p in r["people"]] == ["Mark Morrison", "Sam", "Alex Rivera", "No one"]
    assert r["totals"]["unassigned"] == 4 and people["No one"]["ref"] is None


def test_each_persons_split_by_state(pulled):
    people = _people(team.rollup(DAY))
    split = {name: {g: n for g, n in p["by_group"].items() if g != "triage"} for name, p in people.items()}
    assert split == {
        "Mark Morrison": {"backlog": 5, "unstarted": 6, "started": 12},
        "Sam": {"backlog": 2, "unstarted": 3, "started": 0},
        "Alex Rivera": {"backlog": 0, "unstarted": 2, "started": 0},
        "No one": {"backlog": 4, "unstarted": 0, "started": 0},
    }


def test_by_state_and_by_project(pulled):
    r = team.rollup(DAY)
    assert {s["label"]: s["open"] for s in r["states"]} == {"Backlog": 11, "To do": 11, "In progress": 12}
    by_project = {p["identifier"]: (p["open"], p["by_group"]["backlog"], p["by_group"]["unstarted"],
                                    p["by_group"]["started"]) for p in r["projects"]}
    assert by_project == {"BD": (10, 2, 1, 7), "OPERATIONS": (5, 1, 3, 1), "MARKETING": (5, 1, 4, 0),
                          "HARDWARE": (4, 4, 0, 0), "INFRA": (4, 1, 1, 2), "CUSTO": (3, 2, 0, 1),
                          "SOFTWARE": (3, 0, 2, 1)}
    assert [p["identifier"] for p in r["projects"]][:1] == ["BD"]          # the busiest first
    bd = next(p for p in r["projects"] if p["identifier"] == "BD")
    assert bd["people"] == {MEMBERS["mark"]: 9, "none": 1} and bd["unassigned"] == 1
    mark = _people(r)["Mark Morrison"]
    assert mark["projects"][PROJECTS["BD"]] == 9 and sum(mark["projects"].values()) == 23


def test_past_due_and_due_soon(pulled):
    r = team.rollup(DAY)
    assert r["totals"]["past_due"] == 6
    people = _people(r)
    assert {name: p["past_due"] for name, p in people.items()} == {
        "Mark Morrison": 2, "Sam": 2, "Alex Rivera": 2, "No one": 0}
    late = [i["key"] for i in r["items"] if i["past_due"]]
    assert late == ["BD-14", "OPERATIONS-2", "MARKETING-4", "SOFTWARE-5", "SOFTWARE-4", "OPERATIONS-10"]
    assert [i["key"] for i in r["items"][:6]] == late                         # past due comes first, oldest first
    # A week earlier nothing was late yet, and those due within the week were "due soon".
    earlier = team.rollup(date(2026, 10, 6))["totals"]
    assert earlier["past_due"] == 0 and earlier["due_soon"] == 4


def test_items_open_in_plane_with_their_state_people_cycle_and_labels(pulled):
    r = team.rollup(DAY)
    assert len(r["items"]) == 34 and len({i["id"] for i in r["items"]}) == 34
    bd14 = next(i for i in r["items"] if i["key"] == "BD-14")
    assert bd14["url"] == "https://app.plane.so/acme-team/browse/BD-14/"
    assert bd14["state"] == {"id": bd14["state"]["id"], "name": "In Progress", "group": "started"}
    assert bd14["assignees"] == [{"id": MEMBERS["mark"], "name": "Mark Morrison", "is_me": True}]
    assert (bd14["cycle"], bd14["labels"], bd14["project"]) == ("October push", ["Grant"], "Business Development")
    assert all(i["state"]["group"] not in ("completed", "cancelled") for i in r["items"])


def test_you_are_the_keys_owner_unless_settings_say_otherwise(pulled):
    people = _people(team.rollup(DAY))
    assert people["Mark Morrison"]["is_me"] and people["Mark Morrison"]["ref"] == "core:me"
    assert people["Sam"]["ref"] == f"plane:{MEMBERS['sam']}"
    settings.update({"plane.me": MEMBERS["sam"]})
    r = team.rollup(DAY)
    assert [p["name"] for p in r["people"]][0] == "Sam"                    # you come first
    assert _people(r)["Sam"]["ref"] == "core:me" and not _people(r)["Mark Morrison"]["is_me"]


def test_the_demo_project_counts_only_when_chosen(pulled):
    settings.update({"plane.projects": [*REAL_PROJECTS, PROJECTS["ACME"]]})
    from modules.plane.server import pull
    pull.pull_now()
    jobs.drain()
    r = team.rollup(DAY)
    assert r["totals"]["open"] == 39 and _people(r)["Mark Morrison"]["open"] == 25


def test_done_archived_drafts_and_removed_items_dont_count(pulled):
    some = db.query("SELECT id FROM plane_items i WHERE project_id = ? ORDER BY sequence_id", (PROJECTS["BD"],))
    db.execute("UPDATE plane_items SET archived_at = '2026-10-17T00:00:00Z' WHERE id = ?", (some[0]["id"],))
    db.execute("UPDATE plane_items SET is_draft = 1 WHERE id = ?", (some[1]["id"],))
    db.execute("UPDATE plane_items SET removed_at = '2026-10-17T00:00:00Z' WHERE id = ?", (some[3]["id"],))
    assert team.rollup(DAY)["totals"]["open"] == 31


def test_teammates_with_nothing_open_still_get_a_card(pulled):
    with db.connect() as conn:
        conn.execute("INSERT INTO plane_members (id, display_name, first_name, last_name, email, role) "
                     "VALUES ('new-member', 'ana', 'Ana', 'Ruiz', 'ana@acme-team.example', 'member')")
    people = _people(team.rollup(DAY))
    assert people["Ana Ruiz"]["open"] == 0
    assert list(people)[-2:] == ["Ana Ruiz", "No one"]


def test_nothing_chosen_means_nothing_counted(fake_plane):
    settings.update({"plane.projects": []})
    r = team.rollup(DAY)
    assert r["totals"]["open"] == 0 and r["projects_chosen"] == 0 and r["configured"]


def test_the_team_endpoint(pulled, client):
    r = client.get("/api/plane/team").json()
    assert r["totals"]["open"] == 34 and r["job"]["status"] == "done" and r["pulled_at"]
    assert r["workspace"] == "acme-team" and r["web_url"] == "https://app.plane.so"
