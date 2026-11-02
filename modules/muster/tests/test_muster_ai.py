"""Chunk 15b: the morning summary, and the suggested plan fitted around the day's meetings, which come through the
briefing (here from the calendar module, fed as the Mac app's window would). The AI is always the fake
(fake_structured)."""
import os
import re
import time
from datetime import datetime, timedelta

import pytest

from core.server import ai, briefing, config, db, jobs, settings
from modules.muster.server import days, meetings, suggest, summary
from modules.muster.tests.conftest import TODAY
from modules.tasks.server import items

DAY = TODAY.isoformat()
TOMORROW = (TODAY + timedelta(days=1)).isoformat()
needs_calendar = pytest.mark.skipif("calendar" not in config.enabled_modules(), reason="needs the calendar module")


@pytest.fixture
def melbourne():
    """This computer's clock in Melbourne (UTC+11 in October), so moments with other offsets have to be converted."""
    old = os.environ.get("TZ")
    os.environ["TZ"] = "Australia/Melbourne"
    time.tzset()
    yield
    if old is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = old
    time.tzset()


@pytest.fixture
def tasks():
    made = []

    def make(text: str, **fields) -> str:
        made.append(items.create(text, **fields))
        return made[-1]

    yield make
    for item_id in made:
        items.delete(item_id)


@pytest.fixture
def calendar(monkeypatch, clock):
    """This Mac's Calendar as a calendar source on Muster's day; send(events) is the app's window sending them."""
    from modules.calendar.server import mac, store as calendar_store
    monkeypatch.setattr(calendar_store, "today", lambda: clock.day)
    source = calendar_store.add("mac")

    class Calendar:
        id = source["id"]

        @staticmethod
        def send(events):
            return mac.take(source["id"], events)
    yield Calendar
    db.execute("DELETE FROM calendar_sources")


def event(title, start, end, **more):
    return {"id": f"{title}@1", "title": title, "start": start, "end": end, "all_day": False, "calendar": "Work",
            "free": False, **more}


EVENTS = [
    event("Standup", "2026-10-21T10:00:00+11:00", "2026-10-21T10:15:00+11:00"),
    event("Design review", "2026-10-21T03:00:00Z", "2026-10-21T04:00:00Z"),                 # 2 to 3 pm in Melbourne
    event("Offsite", "2026-10-21T00:00:00+11:00", "2026-10-22T00:00:00+11:00", all_day=True),
    event("Focus time", "2026-10-21T11:00:00+11:00", "2026-10-21T12:00:00+11:00", free=True),
    event("Planning", "2026-10-22T09:00:00+11:00", "2026-10-22T10:00:00+11:00"),            # tomorrow
    event("  ", "2026-10-21T16:00:00+11:00", "2026-10-21T16:30:00+11:00"),                   # a busy block with no title
    event("Late call", "2026-10-21T23:30:00+11:00", "2026-10-22T01:00:00+11:00"),
]


# ── The day's meetings, from the briefing ─────────────────────────────

def line(title, when, minutes=None, kind="meeting"):
    return {"title": title, "when": when, "minutes": minutes, "kind": kind}


def test_meetings_in_the_briefing_leave_free_time_in_the_working_day():
    today = [line("Offsite", DAY, kind="event"), line("Standup", f"{DAY}T10:00", 15),
             line("Focus time", f"{DAY}T11:00", 60, kind="event"),            # shown as free: doesn't take time
             line("Design review", f"{DAY}T14:00", 60), line("Busy", f"{DAY}T16:00", 30),
             line("Late call", f"{DAY}T23:30", 90),                           # runs past midnight: cut to the day
             line("Kick-off call", f"{DAY}T08:00"),                           # Trailmix recorded it: no length
             line("Yesterday's", "2026-10-20T23:00", 90),                     # began before midnight
             line("Send the outline", DAY, kind="due")]
    assert [(a, b, e["title"]) for a, b, e in meetings.busy(today, DAY)] == [
        (0, 30, "Yesterday's"), (600, 615, "Standup"), (840, 900, "Design review"), (960, 990, "Busy"), (1410, 1440, "Late call")]
    assert [e["title"] for e in meetings.all_day(today)] == ["Offsite"]
    hours = ("09:00", "17:00")
    assert meetings.free_blocks(today, DAY, hours) == [(540, 600), (615, 840), (900, 960), (990, 1020)]
    assert meetings.free_blocks(today, DAY, hours, datetime(2026, 10, 21, 9, 40)) == [(580, 600), (615, 840), (900, 960), (990, 1020)]
    assert meetings.free_blocks(today, DAY, hours, datetime(2026, 10, 21, 16, 58)) == []          # under 5 minutes
    assert meetings.free_blocks(today, DAY, hours, datetime(2026, 10, 20, 12, 0)) == meetings.free_blocks(today, DAY, hours)
    assert meetings.free_blocks([], DAY, ("08:30", "12:00")) == [(510, 720)]


# ── The morning summary ───────────────────────────────────────────────

def test_the_first_look_has_the_ai_sum_up_what_moved(client, clock, tasks, fake_structured):
    settings.update({"muster.ai": True})
    fake_structured.reply = summary.Summary(summary="  Two tasks came in for you.\n  Nothing went past due. ")
    tasks("Book the venue for the retreat")                                    # added since: it moved
    opened = client.post(f"/api/muster/days/{DAY}/open").json()
    assert opened["ai"] is True and opened["summary"]["job"]["status"] in ("queued", "running", "done")
    jobs.drain()
    shown = client.get("/api/muster/today").json()["summary"]
    assert shown["text"] == "Two tasks came in for you. Nothing went past due."
    assert shown["by"].startswith("Claude") and shown["at"] and shown["moved"] >= 1
    asked = fake_structured.calls[0]
    assert asked["schema"] is summary.Summary and "no guess" in asked["system"]
    assert not re.search(r"\(\"|“", summary.SYSTEM + suggest.SYSTEM)       # no examples a small model could copy as facts
    assert "SINCE: the last day" in asked["prompt"] and "- Book the venue for the retreat: Added · yours" in asked["prompt"]

    client.post(f"/api/muster/days/{DAY}/open")                                # a later look doesn't write it again
    jobs.drain()
    assert len(fake_structured.calls) == 1

    fake_structured.reply = ai.AIError("Ollama isn't reachable at http://localhost:11434")
    assert client.post(f"/api/muster/days/{DAY}/summary").status_code == 202  # "Write it again", which fails
    jobs.drain()
    shown = client.get("/api/muster/today").json()["summary"]
    assert shown["job"]["status"] == "error" and "isn't reachable" in shown["job"]["error"]
    assert shown["text"] == "Two tasks came in for you. Nothing went past due."    # the last one stays

    fake_structured.reply = summary.Summary(summary="The retreat venue is the one new thing.")
    client.post(f"/api/jobs/{shown['job']['id']}/retry")                        # Try again
    jobs.drain()
    shown = client.get("/api/muster/today").json()["summary"]
    assert shown["text"] == "The retreat venue is the one new thing." and shown["job"]["status"] == "done"


def quiet(monkeypatch):
    """A briefing with nothing in it, whatever other tests left behind."""
    def gather(since=None, today=None):
        return {"today": (today or TODAY).isoformat(), "since": since, "failed": [],
                "sections": {s: [] for s in briefing.SECTIONS}}
    monkeypatch.setattr(briefing, "gather", gather)


def test_no_summary_with_ai_off_or_nothing_moved(client, clock, tasks, fake_structured, monkeypatch):
    tasks("Book the venue for the retreat")
    opened = client.post(f"/api/muster/days/{DAY}/open").json()                 # AI in Muster is off
    jobs.drain()
    assert opened["ai"] is False and opened["summary"]["job"] is None and not fake_structured.calls
    assert client.post(f"/api/muster/days/{DAY}/summary").status_code == 400
    assert client.post(f"/api/muster/days/{DAY}/plan").json()["detail"].startswith("AI in Muster is off")

    settings.update({"muster.ai": True})
    clock.day = TODAY + timedelta(days=1)
    quiet(monkeypatch)
    opened = client.post(f"/api/muster/days/{TOMORROW}/open").json()          # nothing moved since the last look
    assert opened["summary"]["job"] is None
    client.post(f"/api/muster/days/{TOMORROW}/summary")                         # asked anyway: no AI, no summary
    jobs.drain()
    shown = client.get("/api/muster/today").json()["summary"]
    assert shown["text"] is None and shown["moved"] == 0 and shown["at"] and not fake_structured.calls


# ── The suggested plan ────────────────────────────────────────────────

def _keys(prompt: str) -> dict[str, str]:
    return {title: key for key, title in re.findall(r"^- (C\d+): (.+?) · ", prompt, re.M)}


def _titles(view: dict) -> list[str]:
    return [p["title"] for p in view["picks"] if not p["rolled_to"] and not p["let_go"]]


@needs_calendar
def test_a_suggested_plan_fits_around_the_meetings_and_waits_for_you(client, clock, tasks, fake_structured, melbourne, calendar):
    settings.update({"muster.ai": True})
    calendar.send(EVENTS)
    clock.time = datetime(2026, 10, 21, 8, 40).time()
    tasks("Send Ana the outline", due_on=(TODAY - timedelta(days=2)).isoformat(), estimate_min=30)
    tasks("File the grant report", due_on=DAY)
    tasks("Book the venue", due_on=(TODAY + timedelta(days=3)).isoformat())
    hut = tasks("Ring the hut", status="doing")
    days.add_pick(DAY, ref=f"tasks:{hut}", minutes=45)

    def reply(prompt, system, schema):
        keys = _keys(prompt)
        return suggest.DayPlan(note="A tight morning, then room after the review.", picks=[
            suggest.Pick(key=keys["File the grant report"], reason="Due today.", minutes=50),
            suggest.Pick(key=keys["Send Ana the outline"].lower(), reason="Late since Monday.", minutes=90),
            suggest.Pick(key="C99", reason="Not on the list.", minutes=10),
            suggest.Pick(key=keys["File the grant report"], reason="Twice.", minutes=10),
            suggest.Pick(key=keys["Book the venue"], reason="Due Saturday; 20 minutes before the review.", minutes=22),
        ])
    fake_structured.reply = reply

    asked = client.post(f"/api/muster/days/{DAY}/plan")
    assert asked.status_code == 202 and asked.json()["status"] == "suggesting"
    jobs.drain()
    prompt = fake_structured.calls[-1]["prompt"]
    assert "TODAY: Wednesday 2026-10-21, now 08:40" in prompt and "WORKING HOURS: 09:00 to 17:00" in prompt
    assert ("MEETINGS TODAY (from their calendars):\n- all day: Offsite\n- 10:00–10:15 Standup\n"
            "- 14:00–15:00 Design review\n- 16:00–16:30 Busy\n- 23:30–24:00 Late call\n") in prompt    # its part of today
    assert "Focus time" not in prompt and "Planning" not in prompt              # free, and tomorrow's
    assert ("FREE TIME LEFT TODAY: 09:00–10:00 (60 min), 10:15–14:00 (225 min), 15:00–16:00 (60 min), "
            "16:30–17:00 (30 min); 375 minutes in all.") in prompt
    assert "ALREADY IN TODAY'S PLAN (they come first; 45 minutes estimated):\n- Ring the hut (45 min)" in prompt
    assert "FREE TIME AFTER THAT: about 330 minutes." in prompt
    assert "Ring the hut" not in _keys(prompt)                                 # planned already: not a candidate
    assert re.search(r"C\d+: Send Ana the outline · Late · due 2026-10-19 · estimate 30 min \(theirs\)", prompt)

    plan = client.get("/api/muster/today").json()["plan"]
    assert plan["status"] == "ready" and plan["written_by"].startswith("Claude") and plan["meetings"] == 3
    assert plan["free_minutes"] == 375 and plan["note"] == "A tight morning, then room after the review."
    assert [(p["title"], p["minutes"], p["state"]) for p in plan["proposals"]] == [
        ("File the grant report", 50, "proposed"),
        ("Send Ana the outline", 30, "proposed"),                              # its own estimate, not the AI's
        ("Book the venue", 20, "proposed"),                                    # rounded to 5 minutes
    ]
    assert plan["proposals"][2]["reason"] == "Due Saturday; 20 minutes before the review."
    assert _titles(client.get("/api/muster/today").json()) == ["Ring the hut"]  # nothing applied by itself

    grant, ana, venue = (p["id"] for p in plan["proposals"])
    base = f"/api/muster/days/{DAY}/plan"
    assert client.post(f"{base}/{ana}/accept").json()["state"] == "accepted"
    assert client.post(f"{base}/{ana}/accept").status_code == 400
    assert client.post(f"{base}/{grant}/accept").status_code == 200           # goes before Ana's, as suggested
    assert _titles(client.get("/api/muster/today").json()) == ["Ring the hut", "File the grant report", "Send Ana the outline"]

    client.post(f"{base}/{venue}/move", json={"after": None})                  # you move it first,
    client.patch(f"{base}/{venue}", json={"state": "dropped"})                 # drop it,
    assert client.patch(f"{base}/{ana}", json={"state": "dropped"}).status_code == 400   # (accepted: change it there)
    client.patch(f"{base}/{venue}", json={"state": "proposed", "minutes": 25})  # bring it back with your minutes,
    assert client.post(f"{base}/accept").json() == {"accepted": 1}             # and accept the rest
    view = client.get("/api/muster/today").json()
    assert _titles(view) == ["Ring the hut", "Book the venue", "File the grant report", "Send Ana the outline"]
    assert [p["minutes"] for p in view["picks"]] == [45, 25, 50, 30]
    assert [p["state"] for p in view["plan"]["proposals"]] == ["accepted"] * 3
    assert client.post(f"{base}/nope/accept").status_code == 404
    assert client.post(f"{base}/{venue}/move", json={"after": "nope"}).status_code == 404


@needs_calendar
def test_asking_again_leaves_out_what_you_dropped_and_plans_without_meetings_when_there_are_none(
        client, clock, tasks, fake_structured, melbourne, calendar):
    settings.update({"muster.ai": True})
    calendar.send(EVENTS)
    tasks("File the grant report", due_on=DAY)
    tasks("Book the venue", due_on=(TODAY + timedelta(days=3)).isoformat())

    def everything(prompt, system, schema):
        return suggest.DayPlan(note="", picks=[suggest.Pick(key=k, reason="Why not.", minutes=30) for k in _keys(prompt).values()])
    fake_structured.reply = everything
    base = f"/api/muster/days/{DAY}/plan"
    client.post(base)
    jobs.drain()
    plan = client.get("/api/muster/today").json()["plan"]
    assert plan["meetings"] == 3
    assert not {"Standup", "Offsite", "Planning"} & set(_keys(fake_structured.calls[-1]["prompt"]))   # never candidates
    venue = next(p for p in plan["proposals"] if p["title"] == "Book the venue")
    client.patch(f"{base}/{venue['id']}", json={"state": "dropped"})

    db.execute("DELETE FROM calendar_sources")                                 # no calendar any more
    client.post(base)
    jobs.drain()
    prompt = fake_structured.calls[-1]["prompt"]
    assert "MEETINGS TODAY: none in their calendars" in prompt
    assert "FREE TIME LEFT TODAY: 09:00–17:00 (480 min); 480 minutes in all." in prompt
    assert "Book the venue" not in _keys(prompt) and "File the grant report" in _keys(prompt)
    plan = client.get("/api/muster/today").json()["plan"]
    assert plan["meetings"] == 0 and plan["left_out"] == [venue["ref"]] and plan["note"] is None
    assert client.delete(base).status_code == 204
    assert client.get("/api/muster/today").json()["plan"] is None


def test_nothing_to_suggest_asks_no_ai(client, clock, fake_structured, monkeypatch):
    settings.update({"muster.ai": True})
    quiet(monkeypatch)
    client.post(f"/api/muster/days/{DAY}/plan")
    jobs.drain()
    plan = client.get("/api/muster/today").json()["plan"]
    assert plan["status"] == "ready" and plan["proposals"] == [] and plan["note"].startswith("Nothing to suggest")
    assert not fake_structured.calls


def test_candidates_are_yours_to_do_and_each_comes_once():
    def line(ref, title, kind):
        return {"ref": ref, "title": title, "kind": kind, "what": "", "module": ref.split(":")[0], "module_name": ""}
    gathered = {"sections": {
        "today": [line("tasks:a", "Draft the deck", "late"), line("inbox:m", "Standup notes", "meeting"),
                  line("plane:p", "SOFTWARE-1 Fix the build", "past_due")],                    # the team's, not yours
        "waiting": [line("plane:q", "Draft  the DECK", "outbox"), line("inbox:c", "Review 3 proposals", "proposals")],
        "ahead": [line("tasks:b", "Book the venue", "due"), line("tasks:m", "Beta", "milestone"),
                  line("tasks:p", "Operations", "at_risk"), line("tasks:a", "Draft the deck", "due")],
        "moved": []}}
    planned = [{"ref": "tasks:x", "title": "Ring the hut"}, {"ref": None, "title": "Review 3 proposals"}]
    assert [c["ref"] for c in suggest.candidates(gathered, planned, left_out=["tasks:b"])] == ["tasks:a"]
