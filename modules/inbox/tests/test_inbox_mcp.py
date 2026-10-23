"""Chunk 11: Claude puts a thread in the inbox (tools.py), with its own proposals or for the app's AI to read. Either way
they wait for you on the review screen, and only what you accept becomes a task."""
import json

import pytest

from core.server import config, jobs, mcp
from modules.inbox.tests.test_inbox import READING, THREAD

needs_tasks = pytest.mark.skipif("tasks" not in config.enabled_modules(), reason="the tasks module is off")

ITEMS = [
    {"text": "Send Acme the revised quote", "assignee": "Alex Park", "due_on": "2026-10-23",
     "quote": "I'll send it to them by Friday."},
    {"text": "Update the pricing sheet", "assignee": "Sam Ruiz", "due_on": "2026-10-20"},
    {"text": "Book the kickoff call with Acme.", "assignee": "me", "due_on": "2026-10-27", "priority": "urgent"},
]


def call(**args) -> dict:
    result = mcp.call_tool("inbox_capture", args)
    text = result["content"][0]["text"]
    return {"error": text} if result["isError"] else json.loads(text)


def _capture(client, found: dict) -> dict:
    jobs.drain()
    return client.get(f"/api/inbox/captures/{found['capture']['ref'].split(':', 1)[1]}").json()


@needs_tasks
def test_claudes_proposals_wait_for_you_and_accepting_files_them(client):
    project = client.post("/api/tasks/projects", json={"name": "Acme launch"}).json()["id"]
    found = call(text=THREAD, title="Acme quote thread", items=ITEMS, project=f"tasks:{project}")
    assert found["capture"]["title"] == "Acme quote thread" and found["files_into"] == "Acme launch"
    assert [(p["text"], p["assignee"], p["due_on"], p["priority"]) for p in found["proposals"]] == [
        ("Send Acme the revised quote", "Alex Park", "2026-10-23", "none"),
        ("Update the pricing sheet", "Sam Ruiz", "2026-10-20", "none"),
        ("Book the kickoff call with Acme", "me", "2026-10-27", "urgent")]
    assert "Nothing is a task yet" in found["note"]
    got = _capture(client, found)
    assert (got["source"], got["status"], got["read_by"], got["title_auto"]) == ("claude", "review", "Claude", False)
    assert got["job"] is None                                         # the app's AI wasn't asked: Claude read it
    assert got["proposals"][0]["quote"] == "I'll send it to them by Friday."
    assert client.get("/api/inbox/count").json() == {"waiting": 1}
    assert [t for t in client.get("/api/tasks").json() if t["source_ref"] == f"inbox:{got['id']}"] == []

    client.post(f"/api/inbox/captures/{got['id']}/accept", json={})
    filed = [t for t in client.get("/api/tasks").json() if t["source_ref"] == f"inbox:{got['id']}"]
    assert sorted((t["text"], t["project_id"]) for t in filed) == [
        ("Book the kickoff call with Acme", project), ("Send Acme the revised quote", project),
        ("Update the pricing sheet", project)]
    assert next(t for t in filed if t["text"].startswith("Book"))["assignee_ref"] == "core:me"


def test_without_items_the_apps_ai_reads_it(client, fake_structured):
    fake_structured.reply = READING
    found = call(text=THREAD)
    assert "The app's own AI is reading it now" in found["note"]     # (a fake AI may have finished already)
    got = _capture(client, found)
    assert got["source"] == "claude" and got["status"] == "review" and len(got["proposals"]) == 3
    assert "WHAT IT IS: Sent from Claude" in fake_structured.calls[0]["prompt"]


@pytest.mark.parametrize("args, says", [
    ({"text": THREAD, "items": []}, "Give at least one item"),
    ({"text": THREAD, "items": [{"text": " "}]}, "Item 1 needs its text"),
    ({"text": THREAD, "items": [{"text": "Go", "due_on": "Friday"}]}, "Item 1's due_on, 'Friday', isn't a date"),
    ({"text": THREAD, "items": [{"text": "Go", "priority": "asap"}]}, "Item 1's priority must be one of"),
    ({"text": THREAD, "items": [{"text": "Go", "who": "Eli"}]}, "Item 1 has who; an item takes"),
    ({"text": THREAD, "items": ["Go"]}, "Item 1 must be an object"),
    ({"text": THREAD, "project": "Acme"}, "There's no project Acme"),
    ({"text": "   "}, "There's nothing to read in that."),
    ({"text": "x" * 60_001}, "That's longer than the inbox reads at once"),
])
def test_what_it_cant_take_is_refused_with_a_reason_and_nothing_is_kept(client, args, says):
    assert says in call(**args)["error"]
    assert client.get("/api/inbox/captures").json() == []
