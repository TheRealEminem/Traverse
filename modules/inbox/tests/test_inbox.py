"""Chunk 9: capture, the AI's reading (a fake one), the review, and filing into a project through the tasks module."""
from datetime import date

import pytest

from core.server import ai, config, contracts, events, jobs, settings
from modules.inbox.server import extract, store
from modules.inbox.server.extract import Proposal, Reading

needs_tasks = pytest.mark.skipif("tasks" not in config.enabled_modules(), reason="the tasks module is off")

THREAD = """\
#acme-launch
Elijah Park  9:12 AM
  Acme wants the revised quote before their board meets. I'll send it to them by Friday.
Mickey Ruiz  9:15 AM
  I can update the pricing sheet tomorrow so the numbers match.
Dale Morgan  9:20 AM
  Great. I'll book the kickoff call with Acme for next Tuesday. This one's urgent, the board meets Wednesday.
Mickey Ruiz  9:21 AM
  :thumbsup:
"""

READING = Reading(title="Acme quote thread", proposals=[
    Proposal(text="Send Acme the revised quote", assignee_name="Elijah Park", when_said="by Friday", due_on="2026-10-23",
             quote="I'll send it to them by Friday."),
    Proposal(text="Update the pricing sheet", assignee_name="Mickey Ruiz", when_said="tomorrow", due_on="2026-10-20",
             quote="I can update the pricing sheet tomorrow so the numbers match."),
    Proposal(text="Book the kickoff call with Acme", assignee_name="Dale Morgan", when_said="next Tuesday",
             due_on="2026-10-27", urgency_said="urgent", priority=4,
             quote="I'll book the kickoff call with Acme for next Tuesday."),
])


def _paste(client, text=THREAD, **extra) -> str:
    response = client.post("/api/inbox/paste", json={"text": text, **extra})
    assert response.status_code == 201, response.text
    jobs.drain()
    return response.json()["id"]


def _capture(client, capture_id) -> dict:
    jobs.drain()
    return client.get(f"/api/inbox/captures/{capture_id}").json()


def _project(client, name="Acme launch") -> str:
    return client.post("/api/tasks/projects", json={"name": name}).json()["id"]


def _tasks_from(client, capture_id) -> list[dict]:
    return [t for t in client.get("/api/tasks", params={"parent": "any"}).json() if t["source_ref"] == f"inbox:{capture_id}"]


# ── Capture and reading ───────────────────────────────────────────────

def test_a_pasted_thread_is_read_into_proposals_with_people_dates_and_the_sentence_each_came_from(client, fake_structured):
    fake_structured.reply = READING
    capture_id = _paste(client)
    got = _capture(client, capture_id)

    assert got["source"] == "paste" and got["status"] == "review" and got["job"]["status"] == "done"
    assert got["title"] == "Acme quote thread"                      # the AI named it, since you didn't
    assert got["read_by"] == "Claude (Anthropic)"                   # which AI wrote them, for the screen
    assert [(p["text"], p["assignee_name"], p["due_on"], p["priority"]) for p in got["proposals"]] == [
        ("Send Acme the revised quote", "Elijah Park", "2026-10-23", 0),
        ("Update the pricing sheet", "Mickey Ruiz", "2026-10-20", 0),
        ("Book the kickoff call with Acme", "Dale Morgan", "2026-10-27", 4),
    ]
    assert got["proposals"][0]["quote"] == "I'll send it to them by Friday."
    assert client.get("/api/inbox/count").json() == {"waiting": 1}

    call = fake_structured.calls[0]
    assert call["schema"] is Reading and "Elijah Park" in call["prompt"]
    assert "REFERENCE DATE: " in call["prompt"] and "\nnext Tuesday = " in call["prompt"]
    assert "RECORDED THE MEETING" not in call["prompt"]       # in a chat, "I" is whoever wrote the message


def test_the_reading_is_dated_from_the_day_it_speaks_from(client):
    capture = {"source": "trailmix", "title": "Weekly sync", "raw_text": "- Ship it", "origin_title": "Weekly sync",
               "origin_at": "2026-10-16T17:30:00.000Z", "created_at": "2026-10-19T09:00:00.000Z"}
    prompt = extract.prompt_for(capture, "Dale")
    assert prompt.startswith("REFERENCE DATE: Friday 2026-10-16")     # the meeting's day, not the day it came in
    assert '"You" in its notes means Dale' in prompt


def test_when_words_are_worked_out_for_the_model():
    said_on_monday = dict(extract.when_words(date(2026, 10, 19)))
    assert {w: said_on_monday[w].isoformat() for w in ("today", "tomorrow", "Monday", "Friday", "next Tuesday",
                                                       "end of the week", "end of next week")} == {
        "today": "2026-10-19", "tomorrow": "2026-10-20", "Monday": "2026-10-26", "Friday": "2026-10-23",
        "next Tuesday": "2026-10-27", "end of the week": "2026-10-23", "end of next week": "2026-10-30"}
    said_on_saturday = dict(extract.when_words(date(2026, 10, 24)))
    assert said_on_saturday["Friday"].isoformat() == "2026-10-30" and said_on_saturday["end of the week"].isoformat() == "2026-10-30"
    assert extract.reference_day({"created_at": "2026-10-19T09:00:00.000Z", "origin_at": "2026-10-02"}).isoformat() == "2026-10-02"


def test_a_title_you_give_is_kept(client, fake_structured):
    fake_structured.reply = READING
    capture_id = _paste(client, title="Acme, Monday")
    assert _capture(client, capture_id)["title"] == "Acme, Monday"


def test_odd_answers_are_tidied_not_guessed(fake_structured):
    said = "Call Sam ASAP, by Friday at the latest. Ship it Feb 30."
    assert extract.tidy(Proposal(text="  Call   Sam. ", assignee_name="nobody", due_on="Friday", urgency_said="ASAP",
                                 priority=9, quote=" x "), said) == {
        "text": "Call Sam", "assignee_name": None, "due_on": None, "priority": 4, "quote": "x"}
    assert extract.tidy(Proposal(text="Call Sam", priority=3, quote="x"), said)["priority"] == 0   # no urgency words: a guess
    assert extract.tidy(Proposal(text="Call Sam", due_on="2026-10-19", quote="x"), said)["due_on"] is None  # nor when-words
    made_up = Proposal(text="Call Sam", when_said="today", due_on="2026-10-19", urgency_said="urgent", priority=4, quote="x")
    assert extract.tidy(made_up, said)["due_on"] is None and extract.tidy(made_up, said)["priority"] == 0  # not in the text
    assert extract.tidy(Proposal(text="Call Sam", when_said="By  friday", due_on="2026-10-23", quote="x"), said)["due_on"] == "2026-10-23"
    assert extract.tidy(Proposal(text="Call Sam", quote="- Call Sam."), said)["quote"] == "Call Sam."
    assert extract.tidy(Proposal(text="  ", quote=""), said) is None
    assert extract.tidy(Proposal(text="Ship", when_said="Feb 30", due_on="2026-02-30", quote=""), said)["due_on"] is None


def test_nothing_found_means_nothing_waits(client, fake_structured):
    fake_structured.reply = Reading(title="Lunch chat", proposals=[])
    capture_id = _paste(client, "Anyone up for tacos?")
    got = _capture(client, capture_id)
    assert got["status"] == "done" and got["proposals"] == [] and got["read_by"]
    assert client.get("/api/inbox/count").json() == {"waiting": 0}


def test_when_the_ai_fails_the_capture_keeps_its_text_and_offers_to_try_again(client, fake_structured):
    fake_structured.reply = ai.AIError("Ollama isn't reachable", provider_down=True)
    capture_id = _paste(client)
    got = _capture(client, capture_id)
    assert got["status"] == "new" and got["job"]["status"] == "error" and "Ollama" in got["job"]["error"]
    assert got["raw_text"].startswith("#acme-launch")

    fake_structured.reply = READING
    client.post(f"/api/jobs/{got['job']['id']}/retry")
    assert len(_capture(client, capture_id)["proposals"]) == 3


def test_reading_again_replaces_only_what_still_waits(client, fake_structured):
    fake_structured.reply = READING
    capture_id = _paste(client)
    first, second, third = _capture(client, capture_id)["proposals"]
    client.post(f"/api/inbox/proposals/{first['id']}/drop")
    client.patch(f"/api/inbox/proposals/{third['id']}", json={"text": "Book the Acme kickoff"})

    fake_structured.reply = Reading(title="Acme", proposals=[
        Proposal(text="Send Acme the revised quote", quote="again"),          # dropped already: not proposed twice
        Proposal(text="Write the board memo", quote="new"),
    ])
    client.post(f"/api/inbox/captures/{capture_id}/read")
    got = _capture(client, capture_id)
    assert [(p["text"], p["status"]) for p in got["proposals"]] == [
        ("Send Acme the revised quote", "dropped"), ("Write the board memo", "proposed")]
    assert got["title"] == "Acme"


def test_files_txt_md_and_eml_become_captures(client, fake_structured):
    fake_structured.reply = READING
    md = client.post("/api/inbox/file", json={"name": "notes.md", "text": "# Ops review\n\n- Mickey: renew the domain"})
    assert md.status_code == 201
    eml = ("From: Elijah Park <elijah@cinderlabs.co>\r\nTo: Dale <dale@cinderlabs.co>\r\n"
           "Subject: Acme quote\r\nDate: Fri, 16 Oct 2026 10:00:00 -0700\r\nContent-Type: text/plain\r\n\r\n"
           "Dale, can you send Acme the quote by Monday?\r\n")
    mail = client.post("/api/inbox/file", json={"name": "Acme quote.eml", "text": eml})
    assert mail.status_code == 201
    jobs.drain()

    md_capture = store.get(md.json()["id"])
    assert (md_capture["source"], md_capture["origin_title"]) == ("file", "notes.md")
    mail_capture = store.get(mail.json()["id"])
    assert mail_capture["title"] == "Acme quote" and mail_capture["origin_at"] == "2026-10-16"
    assert mail_capture["raw_text"].startswith("From: Elijah Park <elijah@cinderlabs.co>\nTo: Dale")
    assert "send Acme the quote by Monday" in mail_capture["raw_text"]

    html_mail = ("From: a@b.co\r\nSubject: Hi\r\nContent-Type: text/html\r\n\r\n"
                 "<p>Please <b>renew</b> the domain.</p><style>p{}</style>")
    got = store.get(client.post("/api/inbox/file", json={"name": "hi.eml", "text": html_mail}).json()["id"])
    assert got["raw_text"].endswith("Please renew the domain.")


@pytest.mark.parametrize("body, says", [
    ({"name": "deck.pdf", "text": "x"}, ".txt, .md and .eml"),
    ({"name": "a.txt", "text": "   "}, "nothing to read"),
    ({"name": "a.txt", "text": "x" * (store.MAX_CHARS + 1)}, "longer than the inbox reads"),
])
def test_what_it_cant_read_is_refused_with_a_reason(client, body, says):
    response = client.post("/api/inbox/file", json=body)
    assert response.status_code == 400 and says in response.json()["detail"]
    assert client.post("/api/inbox/paste", json={"text": ""}).status_code == 400


# ── Review ────────────────────────────────────────────────────────────

def test_edit_drop_and_bring_back(client, fake_structured):
    fake_structured.reply = READING
    capture_id = _paste(client)
    first, second, _ = _capture(client, capture_id)["proposals"]

    edited = client.patch(f"/api/inbox/proposals/{first['id']}",
                          json={"text": "Send Acme the v2 quote", "assignee_name": " Elijah ", "due_on": "2026-10-22",
                                "priority": 3}).json()
    assert (edited["text"], edited["assignee_name"], edited["due_on"], edited["priority"]) == (
        "Send Acme the v2 quote", "Elijah", "2026-10-22", 3)
    assert client.patch(f"/api/inbox/proposals/{first['id']}", json={"due_on": ""}).json()["due_on"] is None
    assert client.patch(f"/api/inbox/proposals/{first['id']}", json={"due_on": "Friday"}).status_code == 400
    assert client.patch(f"/api/inbox/proposals/{first['id']}", json={"priority": 7}).status_code == 400
    assert client.patch(f"/api/inbox/proposals/{first['id']}", json={"text": " "}).status_code == 400

    client.post(f"/api/inbox/proposals/{second['id']}/drop")
    assert _capture(client, capture_id)["proposals"][1]["status"] == "dropped"
    client.post(f"/api/inbox/proposals/{second['id']}/restore")
    assert _capture(client, capture_id)["proposals"][1]["status"] == "proposed"


def test_dropping_everything_closes_the_capture_and_bringing_one_back_reopens_it(client, fake_structured):
    fake_structured.reply = READING
    capture_id = _paste(client)
    proposals = _capture(client, capture_id)["proposals"]
    for p in proposals:
        client.post(f"/api/inbox/proposals/{p['id']}/drop")
    assert _capture(client, capture_id)["status"] == "done"
    assert client.get("/api/inbox/count").json() == {"waiting": 0}
    client.post(f"/api/inbox/proposals/{proposals[0]['id']}/restore")
    assert _capture(client, capture_id)["status"] == "review"


def test_accepting_announces_the_items_as_dicts_for_the_capture(client, fake_structured):
    fake_structured.reply = READING
    settings.update({"core.your_name": "Dale Morgan"})
    heard = []
    events.subscribe(contracts.ACTIONS_FOUND, heard.append)
    capture_id = _paste(client)
    third = _capture(client, capture_id)["proposals"][2]
    assert client.post(f"/api/inbox/proposals/{third['id']}/accept").json() == {"accepted": 1}
    assert {"source_ref": f"inbox:{capture_id}", "items": [{
        "text": "Book the kickoff call with Acme", "due_on": "2026-10-27", "priority": 4,
        "assignee_ref": "core:me", "assignee_name": "Dale Morgan"}]} in heard     # you, by your name, are core:me
    response = client.patch(f"/api/inbox/proposals/{third['id']}", json={"text": "Too late"})
    assert response.status_code == 400 and "Tasks" in response.json()["detail"]


@needs_tasks
def test_accepting_files_them_into_the_chosen_project_with_their_people_and_dates(client, fake_structured):
    """Chunk 9's "done when": a pasted thread becomes proposals with the right people, and accepting them files them
    into the project you chose."""
    fake_structured.reply = READING
    project_id = _project(client, "Acme launch Kestrel")
    other_id = _project(client, "Acme renewal Kestrel")
    capture_id = _paste(client)

    # The picker finds projects through the host's search, which the tasks module answers.
    hits = next(g for g in client.get("/api/search", params={"q": "kestrel lau"}).json() if g["module"] == "tasks")["hits"]
    assert (f"tasks:{project_id}", "Project") in [(h["ref"], h["snippet"]) for h in hits]
    assert f"tasks:{other_id}" not in [h["ref"] for h in hits]

    chosen = client.put(f"/api/inbox/captures/{capture_id}/project", json={"ref": f"tasks:{project_id}"}).json()
    assert chosen["project"]["title"] == "Acme launch Kestrel"
    assert client.post(f"/api/inbox/captures/{capture_id}/accept", json={}).json() == {"accepted": 3}

    filed = sorted(_tasks_from(client, capture_id), key=lambda t: t["text"])
    assert [(t["text"], t["project_id"], t["assignee_name"], t["due_on"], t["priority"]) for t in filed] == [
        ("Book the kickoff call with Acme", project_id, "Dale Morgan", "2026-10-27", 4),
        ("Send Acme the revised quote", project_id, "Elijah Park", "2026-10-23", 0),
        ("Update the pricing sheet", project_id, "Mickey Ruiz", "2026-10-20", 0),
    ]
    assert filed[0]["came_from"]["href"] == f"#/inbox/{capture_id}"
    got = _capture(client, capture_id)
    assert got["status"] == "done" and all(p["status"] == "accepted" for p in got["proposals"])
    linked = {(l["title"], l["kind"]) for l in client.get("/api/links", params={"ref": f"inbox:{capture_id}"}).json()}
    assert ("Acme launch Kestrel", "about") in linked and ("Update the pricing sheet", "action-item") in linked


@needs_tasks
def test_accepting_one_at_a_time_keeps_earlier_ones_and_never_brings_back_a_deleted_task(client, fake_structured):
    fake_structured.reply = READING
    capture_id = _paste(client)
    first, second, third = _capture(client, capture_id)["proposals"]
    client.post(f"/api/inbox/proposals/{first['id']}/accept")
    client.post(f"/api/inbox/proposals/{second['id']}/accept")
    assert sorted(t["text"] for t in _tasks_from(client, capture_id)) == ["Send Acme the revised quote", "Update the pricing sheet"]

    gone = next(t for t in _tasks_from(client, capture_id) if t["text"] == "Update the pricing sheet")
    client.delete(f"/api/tasks/{gone['id']}")
    client.post(f"/api/inbox/proposals/{third['id']}/accept")
    assert sorted(t["text"] for t in _tasks_from(client, capture_id)) == ["Book the kickoff call with Acme",
                                                                          "Send Acme the revised quote"]


@needs_tasks
def test_without_a_project_they_wait_in_no_project_and_a_project_chosen_later_takes_the_next_ones(client, fake_structured):
    fake_structured.reply = READING
    capture_id = _paste(client)
    first, second, _ = _capture(client, capture_id)["proposals"]
    client.post(f"/api/inbox/proposals/{first['id']}/accept")
    assert [t["project_id"] for t in _tasks_from(client, capture_id)] == [None]

    project_id = _project(client)
    client.put(f"/api/inbox/captures/{capture_id}/project", json={"ref": f"tasks:{project_id}"})
    client.post(f"/api/inbox/proposals/{second['id']}/accept")
    assert {t["project_id"] for t in _tasks_from(client, capture_id)} == {project_id}   # untouched ones follow it

    client.put(f"/api/inbox/captures/{capture_id}/project", json={"ref": None})
    assert _capture(client, capture_id)["project"] is None


def test_a_project_must_be_one_the_host_can_name(client, fake_structured):
    fake_structured.reply = READING
    capture_id = _paste(client)
    for bad in ("tasks:nope", "notes:abc"):
        response = client.put(f"/api/inbox/captures/{capture_id}/project", json={"ref": bad})
        assert response.status_code == 400


# ── Found elsewhere ───────────────────────────────────────────────────

def test_search_describe_rename_and_export(client, fake_structured):
    fake_structured.reply = READING
    capture_id = _paste(client)
    hits = next(g for g in client.get("/api/search", params={"q": "pricing"}).json() if g["module"] == "inbox")["hits"]
    assert hits[0]["id"] == capture_id and hits[0]["href"] == f"#/inbox/{capture_id}" and "pricing" in hits[0]["snippet"]

    client.patch(f"/api/inbox/captures/{capture_id}", json={"title": "Acme, the quote"})
    assert next(g for g in client.get("/api/search", params={"q": "quote"}).json()
                if g["module"] == "inbox")["hits"][0]["title"] == "Acme, the quote"
    client.post(f"/api/inbox/captures/{capture_id}/read")
    assert _capture(client, capture_id)["title"] == "Acme, the quote"       # a name you gave isn't replaced

    held = store.export()
    assert len(held["captures"]) == 1 and len(held["proposals"]) == 3
    listed = client.get("/api/inbox/captures").json()
    assert listed[0]["waiting"] == 3 and listed[0]["job"]["status"] == "done" and "raw_text" not in listed[0]


@needs_tasks
def test_deleting_a_capture_keeps_its_tasks_but_unlinks_them(client, fake_structured):
    fake_structured.reply = READING
    capture_id = _paste(client)
    client.post(f"/api/inbox/captures/{capture_id}/accept", json={})
    filed = {t["id"] for t in _tasks_from(client, capture_id)}
    assert len(filed) == 3
    assert client.delete(f"/api/inbox/captures/{capture_id}").status_code == 204
    assert client.get(f"/api/inbox/captures/{capture_id}").status_code == 404
    left = [t for t in client.get("/api/tasks", params={"parent": "any"}).json() if t["id"] in filed]
    assert len(left) == 3 and all(t["source_ref"] is None for t in left)
    assert client.get("/api/links", params={"ref": f"inbox:{capture_id}"}).json() == []
