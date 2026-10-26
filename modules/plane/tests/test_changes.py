"""The change log (plane_changes, chunk 15) and the plane module's part of the day's briefing: a pull records what a
teammate changed, item by item and field by field, never on a project's first read; the briefing turns it into what
moved, and adds the team's past-due items, cycles ending and the Outbox. None of it reaches Plane beyond the pull's
GETs."""
import copy
import uuid
from datetime import date

from core.server import db, jobs, links, settings
from modules.plane.server import briefing, pull, store
from modules.plane.tests.fakeplane import MEMBERS, PROJECTS, WS

TODAY = date(2026, 10, 21)
ME, SAM, ALEX = MEMBERS["dale"], MEMBERS["sam"], MEMBERS["alex"]


def _pull() -> None:
    pull.pull_now()
    jobs.drain()
    assert db.one("SELECT status FROM core_jobs WHERE module = 'plane' AND kind = 'pull'")["status"] == "done"


def _state(fake, ident: str, group: str) -> str:
    states = fake.data[f"/api/v1/workspaces/{WS}/projects/{PROJECTS[ident]}/states/"]["results"]
    return next(s["id"] for s in states if s["group"] == group)


def _log() -> list[tuple]:
    return [(r["field"], r["before"], r["after"], r["by"]) for r in store.changes("2000-01-01")]


def test_a_first_pull_records_nothing_and_an_unchanged_one_neither(fake_plane):
    _pull()
    assert _log() == []
    _pull()
    assert _log() == []


def test_a_teammates_edits_are_recorded_field_by_field(fake_plane):
    _pull()
    started = _state(fake_plane, "SOFTWARE", "started")
    before = copy.deepcopy(fake_plane.item("SOFTWARE-5"))
    fake_plane.edit("SOFTWARE-5", state=started, assignees=[ALEX, SAM], target_date="2026-10-24", priority="urgent",
                    name="Share the GitHub repos with Dale", updated_by=SAM, description_html="<p>Not logged</p>")
    _pull()
    log = _log()
    assert sorted(f for f, *_ in log) == ["assignees", "due", "name", "priority", "state"]
    assert ("state", before["state"], started, SAM) in log
    assert ("assignees", [ALEX], sorted([ALEX, SAM]), SAM) in log
    assert ("due", "2026-10-13", "2026-10-24", SAM) in log
    assert ("priority", "high", "urgent", SAM) in log
    assert ("name", "Share GitHub repos with Dale", "Share the GitHub repos with Dale", SAM) in log
    item_id = fake_plane.item("SOFTWARE-5")["id"]
    assert {r["item_id"] for r in store.changes("2000-01-01")} == {item_id}
    _pull()
    assert len(_log()) == 5                              # nothing new the second time


def test_new_removed_and_returning_items_are_recorded(fake_plane):
    _pull()
    items = fake_plane.items("HARDWARE")
    new = {**copy.deepcopy(items[0]), "id": str(uuid.uuid4()), "sequence_id": 99, "name": "Order the enclosure samples",
           "updated_by": ALEX, "updated_at": fake_plane.now()}
    items.append(new)
    gone = items.pop(0)
    _pull()
    assert sorted(_log(), key=lambda r: r[0]) == [("added", None, "Order the enclosure samples", ALEX),
                                                  ("removed", gone["name"], None, None)]
    items.append(gone)
    _pull()
    assert _log()[-1] == ("added", None, gone["name"], gone.get("updated_by"))


def test_a_project_read_for_the_first_time_records_nothing(fake_plane):
    chosen = [p for p in settings.section("plane")["projects"] if p != PROJECTS["BD"]]
    settings.update({"plane.projects": chosen})
    jobs.drain()
    _pull()
    settings.update({"plane.projects": [*chosen, PROJECTS["BD"]]})
    jobs.drain()
    _pull()
    assert _log() == []


def test_changes_older_than_90_days_are_forgotten(fake_plane):
    _pull()
    db.execute("INSERT INTO plane_changes (id, item_id, project_id, field, before, after, at) "
               "VALUES ('old', 'x', 'p', 'name', '\"a\"', '\"b\"', '2026-06-01T00:00:00.000Z')")
    fake_plane.edit("BD-14", priority="urgent")
    _pull()
    assert [r["field"] for r in store.changes("2000-01-01")] == ["priority"]


def test_what_moved_reads_as_one_line_per_item(fake_plane):
    _pull()
    since = db.now()
    done = _state(fake_plane, "SOFTWARE", "completed")
    fake_plane.edit("SOFTWARE-5", state=done, updated_by=ALEX)
    fake_plane.edit("BD-14", assignees=[SAM], updated_by=ME)
    fake_plane.edit("OPERATIONS-2", target_date="2026-10-30", priority="urgent", updated_by=SAM)
    _pull()
    moved = {e["title"].split(" ")[0]: e for e in briefing.brief(since, TODAY)["moved"]}
    assert set(moved) == {"SOFTWARE-5", "BD-14", "OPERATIONS-2"}
    software = moved["SOFTWARE-5"]
    assert software["what"] == "Todo → Done"                        # Alex has it: "who" says so, not "by Alex" too
    assert (software["kind"], software["tone"], software["who"]) == ("done", "forest", "Alex Rivera")
    bd = moved["BD-14"]
    assert (bd["what"], bd["kind"], bd["tone"], bd["who"]) == ("Now with Sam (was you) · by you", "assigned", "neutral",
                                                               "Sam")
    ops = moved["OPERATIONS-2"]
    assert ops["what"] == "Due Fri 30 Oct (was Sun 11 Oct) · Urgent priority (was Medium)"
    assert (ops["kind"], ops["project"]) == ("due", "Operations")
    assert ops["url"].endswith("/browse/OPERATIONS-2/")
    assert ops["href"] == f"#/plane/team?item={fake_plane.item('OPERATIONS-2')['id']}"
    assert briefing.brief(db.now(), TODAY)["moved"] == []              # nothing since now
    later = db.now()
    fake_plane.edit("BD-14", assignees=[ME, SAM], updated_by=SAM)
    _pull()
    back = briefing.brief(later, TODAY)["moved"]
    assert [(e["what"], e["tone"]) for e in back] == [("Now with you, Sam (was Sam)", "sun")]
    whole = briefing.brief(since, TODAY)["moved"]              # both edits: from you, to you and Sam
    assert [e["what"] for e in whole if e["title"].startswith("BD-14")] == ["Now with you, Sam (was you)"]


def test_the_briefing_has_the_teams_past_due_cycles_and_the_outbox(fake_plane):
    _pull()
    found = briefing.brief(db.now(), TODAY)
    late = found["today"]
    assert late and all(e["kind"] == "past_due" and e["when"] < "2026-10-21" for e in late)
    assert [e["when"] for e in late] == sorted(e["when"] for e in late)
    bd14 = fake_plane.item("BD-14")["id"]
    assert any(e["id"] == bd14 for e in late)                  # yours, but not a task in Traverse: shown
    links.add("tasks:t1", f"plane:{bd14}", "synced")
    try:
        assert not any(e["id"] == bd14 for e in briefing.brief(db.now(), TODAY)["today"])   # the tasks module has it
    finally:
        links.remove("tasks:t1", f"plane:{bd14}", "synced")
    cycles = found["ahead"]
    assert [(c["title"], c["when"], c["project"]) for c in cycles] == [("October push", "2026-10-24", "Business Development")]
    assert found["waiting"] == []
    stamp = db.now()
    db.execute("INSERT INTO plane_pushes (id, kind, local_ref, project_id, item_id, changes, status, created_at, updated_at) "
               "VALUES ('p1', 'update', 'tasks:gone', ?, ?, '[]', 'stopped', ?, ?)", (PROJECTS["BD"], bd14, stamp, stamp))
    waiting = briefing.brief(db.now(), TODAY)["waiting"]
    assert [(w["what"], w["href"], w["tone"]) for w in waiting] == [
        ("Stopped: changed in Plane meanwhile", "#/plane/outbox?push=p1", "sun")]


def test_an_item_gone_past_due_since_moved(fake_plane):
    _pull()
    since = "2026-10-12T12:00:00.000Z"
    moved = briefing.brief(since, TODAY)["moved"]
    keys = {e["title"].split(" ")[0]: e for e in moved}
    assert keys["SOFTWARE-5"]["what"] == "Went past due (Tue 13 Oct)"
    assert (keys["SOFTWARE-5"]["kind"], keys["SOFTWARE-5"]["tone"]) == ("past_due", "trail")


def test_the_briefing_never_reaches_plane(fake_plane):
    _pull()
    fake_plane.requests.clear()
    briefing.brief("2000-01-01T00:00:00.000Z", TODAY)
    assert fake_plane.requests == [] and fake_plane.writes == []


def test_not_set_up_says_only_what_waits(fake_plane):
    settings.update({"plane.personal_api_key": ""})
    try:
        assert briefing.brief(db.now(), TODAY) == {"waiting": []}
    finally:
        settings.update({"plane.personal_api_key": "plane_api_test"})
        jobs.drain()
