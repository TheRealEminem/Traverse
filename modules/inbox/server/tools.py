"""What Claude may do with the inbox, through the host's MCP server (core/server/mcp.py): bring in a thread, an email or
notes, as a capture from Claude.

Claude has usually read the text already, so it can bring its own proposals; they wait for you like the AI's do
(read_by "Claude"). Without them, the inbox/extract job reads it with the app's AI, as it does a paste. Either way
nothing becomes a task until you accept it on the review screen.
"""
from datetime import date

from core.server import db, events, jobs, module
from core.server.mcp import Tool

from . import capture as captures, review, store

PRIORITY = {"none": 0, "low": 1, "medium": 2, "high": 3, "urgent": 4}
ITEM_KEYS = ("text", "assignee", "due_on", "priority", "quote")


def _proposal(found, n: int) -> dict:
    """One of Claude's proposals, checked the way an edit on the review screen is."""
    if not isinstance(found, dict):
        raise ValueError(f"Item {n} must be an object with at least its text.")
    unknown = set(found) - set(ITEM_KEYS)
    if unknown:
        raise ValueError(f"Item {n} has {', '.join(sorted(unknown))}; an item takes {', '.join(ITEM_KEYS)}.")
    text = " ".join(str(found.get("text") or "").split()).rstrip(".")
    if not text:
        raise ValueError(f"Item {n} needs its text: the work, as a short imperative.")
    due = found.get("due_on") or None
    if due is not None:
        try:
            due = date.fromisoformat(str(due)).isoformat() if len(str(due)) == 10 else ""
        except ValueError:
            due = ""
        if not due:
            raise ValueError(f"Item {n}'s due_on, {found['due_on']!r}, isn't a date like 2026-10-31.")
    priority = found.get("priority") or "none"
    if priority not in PRIORITY:
        raise ValueError(f"Item {n}'s priority must be one of {', '.join(PRIORITY)}.")
    who = " ".join(str(found.get("assignee") or "").split())
    return {"text": text[:300], "assignee_name": who[:80] or None, "due_on": due, "priority": PRIORITY[priority],
            "quote": " ".join(str(found.get("quote") or "").split())[:500]}


def capture(args: dict) -> dict:
    fields = {**captures.pasted(args["text"], args.get("title") or ""), "source": "claude"}
    given = args.get("items")
    found = [_proposal(p, n) for n, p in enumerate(given, 1)][: store.MAX_PROPOSALS] if given is not None else None
    if given is not None and not found:
        raise ValueError("Give at least one item, or leave items out to let the app's AI read it.")
    project = (args.get("project") or "").strip() or None
    if project and (not project.startswith("tasks:") or module.describe(project) is None):
        raise ValueError(f"There's no project {project}. Give a project's ref, like tasks:…, from tasks_find.")
    capture_id = store.create(**fields)
    if project:
        review.set_project(capture_id, project)
    if found is None:
        jobs.enqueue("inbox", "extract", capture_id)
    else:
        store.replace_proposed(capture_id, found)
        store.update(capture_id, read_by="Claude", read_at=db.now(), status="review")
        store.settle(capture_id)
    events.publish("inbox.capture.added", {"id": capture_id, "source": "claude"})
    row = store.get(capture_id)
    out = {"capture": {"ref": review.ref(capture_id), "title": row["title"], "href": f"#/inbox/{capture_id}"},
           "proposals": [{"text": p["text"], "assignee": p["assignee_name"], "due_on": p["due_on"],
                          "priority": [k for k, v in PRIORITY.items() if v == p["priority"]][0]}
                         for p in store.proposals(capture_id)]}
    where = review.project_of(capture_id)
    if where:
        out["files_into"] = where["title"]
    out["note"] = ("Nothing is a task yet: the user accepts, edits or drops each proposal in the inbox."
                   if found is not None else
                   "The app's own AI is reading it now. Its proposals wait in the inbox for the user to review.")
    return out


TOOLS = [
    Tool(
        name="capture", title="Put it in the inbox", handler=capture, writes=True,
        description="Puts a thread, an email or notes in the user's Traverse inbox, with the follow-ups in it as "
                    "proposals for the user to review: they accept, edit or drop each one, and only what they accept "
                    "becomes a task. Use it to file follow-ups from a conversation. Give items when you've read the "
                    "text (one per piece of work someone agreed to do or was asked to do); leave items out to let the "
                    "app's own AI read it. Nothing is sent anywhere.",
        params={
            "text": {"type": "string", "description": "The thread, email or notes, as written (who said what, and "
                                                      "when, if the text has it)."},
            "title": {"type": "string", "description": "A short name for it (under 8 words)."},
            "items": {"type": "array", "description": "Your proposals.", "items": {
                "type": "object", "required": ["text"], "additionalProperties": False, "properties": {
                    "text": {"type": "string", "description": "The work as a short imperative, under 12 words, "
                                                              "without the person or the day."},
                    "assignee": {"type": "string", "description": "Who will do it, by the name the text uses; "
                                                                  "me for the user."},
                    "due_on": {"type": "string", "description": "YYYY-MM-DD, only when the text says when."},
                    "priority": {"type": "string", "enum": list(PRIORITY),
                                 "description": "Only when the text says how urgent."},
                    "quote": {"type": "string", "description": "The sentence it came from, word for word."}}}},
            "project": {"type": "string", "description": "A project's ref (tasks:…, from tasks_find) to file what's "
                                                         "accepted into."},
        },
        required=("text",),
    ),
]
