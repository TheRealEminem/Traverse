"""Reading a capture: the inbox/extract job asks the AI (Settings → AI) for the work items in it.

It runs only as a job, never inside a request. A capture is read against the day it was written (the day you pasted
it, the meeting's day, the email's date), with a table of what "Friday" or "next Tuesday" means that day, because small
local models get dates wrong when they count. Running it twice is harmless: a new reading replaces only the
proposals still waiting for you.
"""
from datetime import date, datetime, timedelta

from pydantic import BaseModel, Field

from core.server import ai, db, events, settings
from core.server.jobs import Job

from . import store

SYSTEM = """You read something a person brought into their work inbox (a chat thread, an email, notes, or the action
items from a meeting) and propose the work items in it: things someone has agreed to do, been asked to do, or must do.

- One proposal per piece of work. Leave out small talk, things already done, and wishes nobody took on.
- text: the work as a short imperative, under 12 words ("Send Acme the revised quote"). Leave the person and the day
  out of it.
- assignee_name: who will do it, by the name the text uses. In a chat or email, "I" and "me" are whoever wrote that
  message, named on the line above it. Empty when nobody is named.
- when_said: the words that say when this piece of work is due, copied ("by Friday", "tomorrow", "next Tuesday").
  Empty when none do.
- due_on: the day those words mean, as YYYY-MM-DD, copied from the table of when-words (a date written out, like
  "Oct 30", is that date). Empty when when_said is.
- urgency_said: words about this piece of work that say how urgent it is, copied ("urgent", "ASAP", "important",
  "no rush"). Empty when none do. A due day alone is not urgency.
- priority: from urgency_said: "urgent", "ASAP", "critical", "blocking" 4; "important", "high priority" 3; "soon" 2;
  "no rush", "whenever" 1. 0 when urgency_said is empty.
- quote: the sentence it came from, copied word for word.
- title: a short plain name for the whole thing, under 8 words ("Acme quote and kickoff").
Use only what the text says."""

SOURCE_WORDS = {"paste": "Pasted text", "file": "A file", "claude": "Sent from Claude", "trailmix": "A meeting's action items"}


class Proposal(BaseModel):
    """Field order matters to small local models, which fill a schema in order: the words that say when and how
    urgent come before the values read from them (tried on qwen2.5:7b; see PLAN.md chunk 9's result)."""
    text: str
    assignee_name: str | None = None
    when_said: str | None = None
    due_on: str | None = Field(None, description="YYYY-MM-DD")
    urgency_said: str | None = None
    priority: int = Field(0, description="0 none, 1 low, 2 medium, 3 high, 4 urgent")
    quote: str


class Reading(BaseModel):
    proposals: list[Proposal]
    title: str


def reference_day(capture: dict) -> date:
    """The day the capture speaks from, on this Mac's calendar."""
    when = capture.get("origin_at") or capture["created_at"]
    if len(when) == 10:
        return date.fromisoformat(when)
    return datetime.fromisoformat(when.replace("Z", "+00:00")).astimezone().date()


def when_words(day: date) -> list[tuple[str, date]]:
    """What "Friday", "next Tuesday" or "end of the week" mean, said on `day`, so the model copies a date rather
    than counting (which small models get wrong by a day or two)."""
    rows = [("today", day), ("tomorrow", day + timedelta(days=1))]
    ahead = {(day + timedelta(days=i)).weekday(): day + timedelta(days=i) for i in range(1, 8)}
    rows += [(f"{ahead[wd]:%A}", ahead[wd]) for wd in range(7)]
    next_monday = day - timedelta(days=day.weekday()) + timedelta(days=7)
    rows += [(f"next {next_monday + timedelta(days=wd):%A}", next_monday + timedelta(days=wd)) for wd in range(7)]
    return rows + [("end of the week", day + timedelta(days=(4 - day.weekday()) % 7)),
                   ("end of next week", next_monday + timedelta(days=4)), ("in two weeks", day + timedelta(days=14))]


def prompt_for(capture: dict, your_name: str) -> str:
    day = reference_day(capture)
    lines = [f"REFERENCE DATE: {day:%A} {day.isoformat()}", "WHEN-WORDS AND THE DAY EACH MEANS:"]
    lines += [f"{words} = {d.isoformat()} ({d:%A})" for words, d in when_words(day)]
    if your_name and capture["source"] == "trailmix":
        # Only for meetings, where Trailmix writes "You" for whoever recorded it. In a chat or an email the names are
        # in the text, and naming the reader there pulls every "I" towards them (seen with qwen2.5:7b).
        lines.append(f'THE PERSON WHO RECORDED THE MEETING: {your_name}. "You" in its notes means {your_name}.')
    lines.append(f"WHAT IT IS: {SOURCE_WORDS.get(capture['source'], 'Text')}"
                 + (f" ({capture['origin_title']})" if capture.get("origin_title") else ""))
    if not capture.get("title_auto", True):
        lines.append(f"TITLE: {capture['title']}")      # one you gave; an automatic one is just the first line
    lines += ["", "TEXT:", capture["raw_text"]]
    return "\n".join(lines)


def tidy(found: Proposal) -> dict | None:
    """One proposal as the inbox keeps it, or None when there's no work in it. Odd values are dropped, not guessed."""
    text = " ".join((found.text or "").split()).rstrip(".")
    if not text:
        return None
    due = (found.due_on or "").strip()
    try:
        due = date.fromisoformat(due).isoformat() if len(due) == 10 else None
    except ValueError:
        due = None
    name = " ".join((found.assignee_name or "").split()) or None
    if name and name.casefold() in ("nobody", "none", "unknown", "n/a", "unassigned"):
        name = None
    # A priority with no words saying how urgent is a guess (small models make them): it stays at none.
    priority = min(4, max(0, int(found.priority or 0))) if (found.urgency_said or "").strip() else 0
    return {"text": text[:300], "assignee_name": name[:80] if name else None, "due_on": due, "priority": priority,
            "quote": " ".join((found.quote or "").split())[:500]}


def provider_words(pid: str) -> str:
    """"Ollama · qwen2.5:7b": which AI wrote the proposals, as the screen shows it."""
    about = ai.describe(pid)
    return f"{about['label']} · {about['model']}" if about.get("model") else about["label"]


def extract(job: Job) -> None:
    capture = store.get(job.target)
    if not capture:
        return  # deleted meanwhile
    job.stage("Reading")
    reading, pid = ai.structured(prompt_for(capture, settings.section("core")["your_name"].strip()), SYSTEM, Reading)
    found = [p for p in (tidy(p) for p in reading.proposals[: store.MAX_PROPOSALS]) if p]
    store.replace_proposed(capture["id"], found)
    changes = {"read_by": provider_words(pid), "read_at": db.now(), "status": "review"}
    title = " ".join((reading.title or "").split())
    if capture["title_auto"] and title:
        changes["title"] = title[:120]
    store.update(capture["id"], **changes)
    store.settle(capture["id"])
    events.publish("inbox.capture.read", {"id": capture["id"]})
