"""The morning summary (PLAN.md chunk 15b): a few sentences on what moved since your last Muster, written by the AI
(Settings → AI) in the muster/summary job, and always shown with which AI wrote it.

It's written on the day's first look at Muster, when something moved and "AI in Muster" is on, and again when you
ask. It reads only the host's briefing, the same lines "What moved" lists, so it can't say more than they do. Running
the job twice just writes it again.
"""
from datetime import date, datetime

from pydantic import BaseModel

from core.server import ai, briefing, db, events, jobs
from core.server.jobs import Job

from . import store

KIND = "summary"
MOST_LINES = 60                  # lines of "what moved" in the prompt; the rest are counted


def target(day: str) -> str:
    return f"{KIND}:{day}"


def lane(_target: str) -> str:
    """You're looking at the page while it's written, but a model on this Mac runs one thing at a time."""
    return "default" if ai.local_first() else "interactive"


def written_by(pid: str) -> str:
    """"Claude (Anthropic) · claude-opus-5-5": which AI wrote it, as the screens say it (tasks' drafts say the same)."""
    about = ai.describe(pid)
    return f"{about['label']} · {about['model']}" if about.get("model") else about["label"]


def start(day: str) -> None:
    """Queues the job that writes (or rewrites) the day's summary."""
    jobs.enqueue("muster", KIND, target(day))


def shaped(row: dict) -> dict:
    """The summary as the page shows it, with its job (writing, failed with why, or done)."""
    return {"text": row["summary"], "by": row["summary_by"], "at": row["summary_at"], "moved": row["summary_moved"],
            "job": jobs.latest("muster", [target(row["day"])]).get(target(row["day"]))}


# ── The job ───────────────────────────────────────────────────────────

SYSTEM = """You write the morning summary for someone starting their working day: what moved in their work and their
team's since they last looked. They read it in a few seconds, before planning the day.

- summary: 1 to 4 short sentences of plain text. No greeting, heading, list or advice. Lead with what touches them
  most: work that came to them or was taken off them, what got done, what went past due or had its date changed.
  Then the rest, grouped by person or project. When little moved, one sentence is enough.
- Name people and items exactly as the facts do; "you" is the reader. Say only what the facts say: no person, item,
  project or number that isn't in them, and no guess at why something happened or what comes next."""


class Summary(BaseModel):
    summary: str


def _moment_words(moment: str) -> str:
    local = datetime.fromisoformat(moment.replace("Z", "+00:00")).astimezone()
    return f"{local:%A %d %B, %H:%M}"


def _line(e: dict) -> str:
    bits = [e["what"]]
    if e.get("who") and e["who"] != "You":
        bits.append(f"now with {e['who']}" if e["module"] == "plane" else e["who"])
    elif e.get("who") == "You":
        bits.append("yours")
    where = "" if e["module"] == "tasks" else f" [{e['module_name']}]"
    return f"- {e['title']}{where}: {' · '.join(b for b in bits if b)}"


def prompt(day: str, since: str, gathered: dict, first: bool) -> str:
    """The facts a summary is written from: what moved, by project, and how much is on today."""
    sections = gathered["sections"]
    moved = sections["moved"]
    lines = [f"TODAY: {date.fromisoformat(day):%A} {day}",
             "SINCE: " + ("the last day (their first Muster)" if first else f"their last Muster, {_moment_words(since)}")]
    groups: dict[str, list[dict]] = {}
    for e in moved[:MOST_LINES]:
        groups.setdefault(e.get("project") or "No project", []).append(e)
    lines.append(f"WHAT MOVED ({len(moved)} lines), by project:")
    for name, entries in sorted(groups.items(), key=lambda g: (g[0] == "No project", -len(g[1]))):
        lines.append(f"{name}:")
        lines += [_line(e) for e in entries]
    if len(moved) > MOST_LINES:
        lines.append(f"- and {len(moved) - MOST_LINES} more")
    today = [e for e in sections["today"] if e.get("kind") not in ("meeting", "event", "past_due")]
    lines.append(f"ALSO (for scale, not to summarize): {len(today)} of theirs due, late or in progress today; "
                 f"{len(sections['waiting'])} waiting on them.")
    return "\n".join(lines)


def write(job: Job) -> None:
    """muster/summary: asks the AI for the day's summary. Nothing moved: no summary, and no AI asked."""
    day = job.target.split(":", 1)[1]
    row = store.row(day)
    if row is None:
        return
    job.stage("Reading what moved")
    since = row["since"] or briefing.day_before()
    gathered = briefing.gather(since, date.fromisoformat(day))
    moved = gathered["sections"]["moved"]
    if not moved:
        store.save(day, summary=None, summary_by=None, summary_at=db.now(), summary_moved=0)
        events.publish("muster.changed", {"day": day})
        return
    first = not store.earlier(day, limit=1)
    job.stage("Writing the summary")
    found, pid = ai.structured(prompt(day, since, gathered, first), SYSTEM, Summary)
    text = " ".join((found.summary or "").split())
    if not text:
        raise ValueError("The AI wrote an empty summary. Try again, or pick another model in Settings → AI.")
    store.save(day, summary=text[:1500], summary_by=written_by(pid), summary_at=db.now(), summary_moved=len(moved))
    events.publish("muster.changed", {"day": day})
