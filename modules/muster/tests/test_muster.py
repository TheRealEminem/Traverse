"""Muster's own part: the start page, a day's "since", picks (adding, ordering, minutes, ticking), carrying them over,
and the wrap-up. Picks here are tasks and lines of your own; the plane module's part is in test_muster_day.py."""
from datetime import timedelta

import pytest

from core.server import db, settings
from modules.muster.server import days, store
from modules.muster.tests.conftest import TODAY
from modules.tasks.server import items

DAY = TODAY.isoformat()
TOMORROW = (TODAY + timedelta(days=1)).isoformat()


@pytest.fixture
def tasks():
    made = []

    def make(text: str, **fields) -> str:
        made.append(items.create(text, **fields))
        return made[-1]

    yield make
    for item_id in made:
        items.delete(item_id)


def _titles(view: dict) -> list[str]:
    return [p["title"] for p in view["picks"]]


def test_muster_is_the_first_page_until_you_have_looked_today(client, clock):
    assert client.get("/api/muster/start").json() == {"path": "muster"}
    client.get("/api/muster/today")                                   # a look from a page that isn't Muster's own
    assert client.get("/api/muster/start").json() == {"path": "muster"}
    client.post(f"/api/muster/days/{DAY}/open")
    assert client.get("/api/muster/start").json() == {"path": None}
    clock.day = TODAY + timedelta(days=1)
    assert client.get("/api/muster/start").json() == {"path": "muster"}
    settings.update({"muster.open_first": False})
    assert client.get("/api/muster/start").json() == {"path": None}


def test_since_is_your_last_look_on_an_earlier_day_and_stays_put(clock):
    first = days.open_day(DAY)
    assert first["first"] and first["since"] < first["opened_at"]          # the very first time: a day ago
    later = days.open_day(DAY)
    assert later["since"] == first["since"] and later["opened_at"] == first["opened_at"]
    last_look = store.row(DAY)["seen_at"]
    clock.day = TODAY + timedelta(days=1)
    nxt = days.open_day(TOMORROW)
    assert nxt["since"] == last_look and not nxt["first"]
    assert nxt["briefing"]["since"] == last_look and nxt["briefing"]["today"] == TOMORROW


def test_picks_are_refs_or_lines_in_your_order_with_minutes(tasks):
    task = tasks("Ring the hut", estimate_min=20)
    a = days.add_pick(DAY, ref=f"tasks:{task}", minutes=20)
    assert (a["title"], a["href"], a["minutes"], a["done"], a["first_day"]) == ("Ring the hut", f"#/tasks/t/{task}", 20, False, DAY)
    b = days.add_pick(DAY, title="  Prep the 2pm call ")
    c = days.add_pick(DAY, title="Lunch with Ana")
    for bad, message in [({"ref": f"tasks:{task}"}, "in the plan already"), ({"ref": "Ring the hut"}, "reference like"),
                         ({"ref": "tasks:gone"}, "isn't here any more"), ({"title": "  "}, "needs some text"),
                         ({"title": "x", "minutes": -5}, "whole number"), ({"title": "x", "minutes": 2000}, "whole number")]:
        with pytest.raises(ValueError, match=message):
            days.add_pick(DAY, **bad)
    days.move_pick(DAY, c["id"], None)
    days.move_pick(DAY, a["id"], b["id"])
    assert _titles(days.view(DAY)) == ["Lunch with Ana", "Prep the 2pm call", "Ring the hut"]
    days.update_pick(DAY, b["id"], {"minutes": 45, "title": "Prep the 3pm call"})
    with pytest.raises(ValueError, match="rename it there"):
        days.update_pick(DAY, a["id"], {"title": "Ring"})
    items.update(task, {"text": "Ring the hut warden"})
    assert _titles(days.view(DAY)) == ["Lunch with Ana", "Prep the 3pm call", "Ring the hut warden"]   # named by tasks now
    days.remove_pick(DAY, c["id"])
    with pytest.raises(KeyError):
        days.remove_pick(DAY, c["id"])
    assert [p["minutes"] for p in days.view(DAY)["picks"]] == [45, 20]


def test_ticking_a_task_pick_ticks_the_task(tasks):
    task = tasks("Send the outline", status="doing")
    pick = days.add_pick(DAY, ref=f"tasks:{task}")
    days.update_pick(DAY, pick["id"], {"done": True})
    assert items.get(task)["status"] == "done"
    days.update_pick(DAY, pick["id"], {"done": False})
    assert items.get(task)["status"] == "todo"
    items.set_status(task, "done")                                     # done in My tasks: the pick shows it
    shown = days.view(DAY)["picks"][0]
    assert shown["done"] and shown["done_there"]


def test_open_picks_carry_over_to_the_next_day_once(clock, tasks):
    finished_there = tasks("Done in My tasks")
    still = tasks("Still to do")
    days.open_day(DAY)
    done_here = days.add_pick(DAY, title="Done here")
    days.update_pick(DAY, done_here["id"], {"done": True})
    days.add_pick(DAY, ref=f"tasks:{finished_there}")
    days.add_pick(DAY, ref=f"tasks:{still}", minutes=30)
    days.add_pick(DAY, title="A line of my own")
    items.set_status(finished_there, "done")

    clock.day = TODAY + timedelta(days=1)
    nxt = days.open_day(TOMORROW)
    assert _titles(nxt) == ["Still to do", "A line of my own"]
    assert [(p["first_day"], p["minutes"], p["done"]) for p in nxt["picks"]] == [(DAY, 30, False), (DAY, None, False)]
    left = {p["title"]: p.get("rolled_to") for p in store.row(DAY)["picks"]}
    assert left == {"Done here": None, "Done in My tasks": None, "Still to do": TOMORROW, "A line of my own": TOMORROW}
    assert _titles(days.open_day(TOMORROW)) == ["Still to do", "A line of my own"]          # only once

    later = (TODAY + timedelta(days=4)).isoformat()                   # skipped two days: still the same picks, once
    clock.day = TODAY + timedelta(days=4)
    assert _titles(days.open_day(later)) == ["Still to do", "A line of my own"]
    assert [p["first_day"] for p in days.view(later)["picks"]] == [DAY, DAY]


def test_the_wrap_up_rolls_open_picks_to_tomorrow_and_lets_go_of_the_rest(clock, tasks):
    days.open_day(DAY)
    a = days.add_pick(DAY, title="Done today")
    b = days.add_pick(DAY, title="Roll me")
    c = days.add_pick(DAY, title="Let me go")
    days.update_pick(DAY, a["id"], {"done": True})
    result = days.wrap_up(DAY, let_go=[c["id"]], note="Start with the grant letter")
    assert result == {"to": TOMORROW, "done": 1, "rolled": 1, "let_go": 1}
    assert store.row(DAY)["wrapped_up_at"]
    assert _titles(days.view(TOMORROW)) == ["Roll me"]
    with pytest.raises(ValueError, match="another day"):
        days.update_pick(DAY, b["id"], {"done": True})
    late = days.add_pick(DAY, title="Added after the wrap-up")
    assert days.wrap_up(DAY, note="Start with the grant letter")["rolled"] == 2      # again: takes it along too
    clock.day = TODAY + timedelta(days=1)
    nxt = days.open_day(TOMORROW)
    assert _titles(nxt) == ["Roll me", "Added after the wrap-up"]
    assert nxt["note"] == {"day": DAY, "text": "Start with the grant letter"}
    assert late["first_day"] == DAY


def test_the_day_keeps_an_intention_and_when_you_kicked_off(client):
    assert client.patch(f"/api/muster/days/{DAY}", json={"intention": " Ship the grant letter "}).status_code == 200
    assert client.post(f"/api/muster/days/{DAY}/kickoff").status_code == 200
    view = client.get("/api/muster/today").json()
    assert view["intention"] == "Ship the grant letter" and view["kicked_off_at"]
    assert view["hours"] == {"start": "09:00", "end": "17:00"}
    assert set(view["briefing"]["sections"]) == {"today", "waiting", "moved", "ahead"}


def test_the_api_answers_in_sentences(client):
    assert client.get("/api/muster/days/Wednesday").status_code == 400
    assert client.post(f"/api/muster/days/{DAY}/picks", json={"title": ""}).json()["detail"] == "A pick needs some text"
    assert client.patch(f"/api/muster/days/{DAY}/picks/nope", json={"done": True}).status_code == 404
    made = client.post(f"/api/muster/days/{DAY}/picks", json={"title": "Write it down", "minutes": 15})
    assert made.status_code == 201
    pick = made.json()["id"]
    assert client.patch(f"/api/muster/days/{DAY}/picks/{pick}", json={"minutes": 25}).json()["minutes"] == 25
    assert client.post(f"/api/muster/days/{DAY}/picks/{pick}/move", json={"after": pick}).status_code == 400
    assert client.delete(f"/api/muster/days/{DAY}/picks/{pick}").status_code == 204
    assert client.post(f"/api/muster/days/{DAY}/wrapup", json={"note": "Tomorrow: the deck"}).json()["to"] == TOMORROW
    assert db.one("SELECT tomorrow_note FROM muster_days WHERE day = ?", (DAY,))["tomorrow_note"] == "Tomorrow: the deck"
