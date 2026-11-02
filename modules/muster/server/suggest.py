"""A suggested plan for the day (PLAN.md chunk 15b): the AI (Settings → AI) picks from what the briefing has for you,
in order, each with a reason and an estimate, fitted into the free time your working hours and meetings leave. It's
only a suggestion: it never applies itself. You accept, move or drop each pick; an accepted one becomes one of the
day's picks, in the suggestion's order, and the rest of Muster treats it like any other.

The muster/plan job tells the AI the day's meetings and the free stretches between them, from the briefing's meeting
lines (meetings.py: Traverse's calendar module gives them), so the plan fits around them wherever the page is open.

A day's plan (muster_days.plan, JSON):
    {"status": "suggesting" | "ready", "asked_at", "written_by", "made_at", "note", "meetings": n, "free_minutes": n, "left_out": [refs you dropped today, not suggested again], "proposals": [
       {"id", "ref", "title", "href", "module", "minutes", "reason", "state": "proposed" | "accepted" | "dropped",
        "pick_id": the day's pick it became}]}
Running the job twice just suggests again.
"""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from core.server import ai, briefing, db, events, jobs, module, settings
from core.server.jobs import Job

from . import meetings, store
from .summary import written_by

KIND = "plan"
MOST_CANDIDATES = 30
MOST_PICKS = 10
STATES = ("proposed", "dropped")
# Briefing lines that aren't yours to do today: meetings and other calendar events (and a calendar that couldn't be
# read), the team's past due, projects at risk, cycles ending, milestones.
NOT_WORK = {"meeting", "event", "calendar", "past_due", "at_risk", "cycle", "milestone"}


def now() -> datetime:
    """This computer's time (tests replace it)."""
    return datetime.now()


def target(day: str) -> str:
    return f"{KIND}:{day}"


def _changed(day: str) -> None:
    events.publish("muster.changed", {"day": day})


def shaped(row: dict) -> dict | None:
    plan = row["plan"]
    if plan is None:
        return None
    return {**plan, "job": jobs.latest("muster", [target(row["day"])]).get(target(row["day"]))}


def _hours() -> tuple[str, str]:
    cfg = settings.section("muster")
    return cfg.get("day_starts") or "09:00", cfg.get("day_ends") or "17:00"


# ── Asking ────────────────────────────────────────────────────────────

def start(day: str) -> dict:
    """"Suggest a plan": queues the job. A plan already suggested is replaced; what you dropped from it stays left
    out."""
    row = store.make(day)
    old = row["plan"] or {}
    left_out = list(dict.fromkeys([*(old.get("left_out") or []),
                                   *(p["ref"] for p in old.get("proposals", []) if p["state"] == "dropped" and p["ref"])]))
    plan = {"status": "suggesting", "asked_at": db.now(), "written_by": None, "made_at": None, "note": None,
            "meetings": 0, "free_minutes": None, "left_out": left_out, "proposals": []}
    jobs.cancel_for("muster", target(day))
    store.save(day, plan=plan)
    jobs.enqueue("muster", KIND, target(day))
    _changed(day)
    return shaped(store.row(day))


def discard(day: str) -> None:
    jobs.cancel_for("muster", target(day))
    store.make(day)
    store.save(day, plan=None)
    _changed(day)


# ── The job ───────────────────────────────────────────────────────────

SYSTEM = """You suggest a plan for someone's working day: which of their candidate tasks to do today, in what order,
each with an estimate and a short reason. It's only a suggestion; they accept, move or drop each pick.

- picks: in the order to do them, using only the candidates' keys (like C3), each at most once. Fill the free time
  that's left after what's already planned, not more: fewer, well-chosen picks beat a crowded day.
- Order: what's late or due today first, then what waits on them, then what's due later this week. Put short picks
  in the short gaps before meetings and long ones in the longest free stretch. Leave out what can wait.
- minutes: a realistic estimate in minutes (15, 30, 45, 60, 90…). Keep the estimate a candidate already has.
- reason: one short sentence, in your own words rather than the title's, on why this and why now, from the facts:
  late, due today, waiting on them, due soon, or where it fits around a meeting they have. Never invent work,
  meetings, people or dates.
- note: one sentence on the shape of the day (how full it is, where the long stretch is)."""


class Pick(BaseModel):
    """The reason comes before the estimate, so a model that fills the schema in order thinks first."""
    key: str = Field(description="a candidate's key, like C3")
    reason: str
    minutes: int = Field(description="minutes")


class DayPlan(BaseModel):
    picks: list[Pick]
    note: str


def _estimate(value) -> int | None:
    """Minutes, rounded to a step a person would say (5 under an hour, else 15); None for nonsense."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    step = 5 if n < 60 else 15
    return min(max(step, round(n / step) * step), 8 * 60)


def _open_picks(row: dict) -> list[dict]:
    out = []
    for p in row["picks"]:
        if p["done"] or p.get("rolled_to") or p.get("let_go"):
            continue
        found = module.describe(p["ref"]) if p.get("ref") else {}
        if found is None or found.get("done"):
            continue
        out.append(p)
    return out


def candidates(gathered: dict, planned: list[dict], left_out: list[str]) -> list[dict]:
    """What the briefing has that you could do today and haven't planned or dropped: today's, what waits on you, and
    what's due this week, in that order, each once. Two lines with the same title (a task, and its change waiting in
    the Outbox) count as one."""
    name = lambda title: " ".join(title.casefold().split())   # noqa: E731
    skip = {p["ref"] for p in planned if p.get("ref")} | set(left_out)
    seen = {name(p["title"]) for p in planned}
    sections = gathered["sections"]
    out = []
    for e in [*sections["today"], *sections["waiting"], *sections["ahead"]]:
        if e.get("kind") in NOT_WORK or e["ref"] in skip or name(e["title"]) in seen:
            continue
        seen.add(name(e["title"]))
        out.append(e)
    return out[:MOST_CANDIDATES]


def _when(e: dict) -> str:
    when = e.get("when") or ""
    return f"due {when}" if len(when) == 10 and e.get("kind") in ("late", "due", "doing") else ""


def prompt(day: str, row: dict, found: list[dict], planned: list[dict], at: datetime | None,
           today: list[dict]) -> tuple[str, int]:
    """The facts a plan is suggested from, and the minutes of free time it has. today: the briefing's today lines,
    whose meetings it fits around."""
    hours = _hours()
    blocks = meetings.free_blocks(today, day, hours, at)
    free = sum(b - a for a, b in blocks)
    lines = [f"TODAY: {date.fromisoformat(day):%A} {day}" + (f", now {at:%H:%M}" if at else ""),
             f"WORKING HOURS: {hours[0]} to {hours[1]}"]
    busy, all_day = meetings.busy(today, day), meetings.all_day(today)
    lines.append("MEETINGS TODAY (from their calendars):" if busy or all_day else "MEETINGS TODAY: none in their calendars")
    lines += [f"- all day: {e['title']}" for e in all_day]
    lines += [f"- {meetings.hhmm(a)}–{meetings.hhmm(b)} {e['title']}" for a, b, e in busy]
    stretches = ", ".join(f"{meetings.hhmm(a)}–{meetings.hhmm(b)} ({b - a} min)" for a, b in blocks)
    lines.append(f"FREE TIME LEFT TODAY: {stretches or 'none'}; {free} minutes in all.")
    if planned:
        taken = sum(p.get("minutes") or 0 for p in planned)
        lines.append(f"ALREADY IN TODAY'S PLAN (they come first; {taken} minutes estimated):")
        lines += [f"- {p['title']}" + (f" ({p['minutes']} min)" if p.get("minutes") else " (no estimate)") for p in planned]
        lines.append(f"FREE TIME AFTER THAT: about {max(0, free - taken)} minutes.")
    if row["intention"]:
        lines.append(f"THEIR LINE FOR TODAY: {row['intention']}")
    lines.append("CANDIDATES:")
    for i, e in enumerate(found, start=1):
        bits = [e["what"], _when(e), e.get("project") or "", "" if e["module"] == "tasks" else f"in {e['module_name']}",
                f"estimate {e['minutes']} min (theirs)" if e.get("minutes") else ""]
        lines.append(f"- C{i}: {e['title']} · " + " · ".join(b for b in bits if b))
    return "\n".join(lines), free


def write(job: Job) -> None:
    """muster/plan: asks the AI for the day's plan. A plan discarded meanwhile is left alone."""
    day = job.target.split(":", 1)[1]
    row = store.row(day)
    if row is None or not row["plan"] or row["plan"]["status"] != "suggesting":
        return
    job.stage("Reading the day")
    at = now()
    at = at if at.date().isoformat() == day else None
    planned = _open_picks(row)
    gathered = briefing.gather(row["since"] or briefing.day_before(), date.fromisoformat(day))
    found = candidates(gathered, planned, row["plan"].get("left_out") or [])
    today = gathered["sections"]["today"]
    text, free = prompt(day, row, found, planned, at, today)
    begin, finish = (meetings.minutes_of(h) for h in _hours())
    taken = sum(1 for a, b, _ in meetings.busy(today, day) if a < finish and b > begin)
    done = {"status": "ready", "made_at": db.now(), "free_minutes": free, "meetings": taken}
    if not found:
        _finish(day, {**done, "note": "Nothing to suggest: everything due, late, in progress or waiting on you is in "
                                      "your plan already, or you left it out.", "proposals": []})
        return
    job.stage("Planning the day")
    reply, pid = ai.structured(text, SYSTEM, DayPlan)
    keyed = {f"C{i}": e for i, e in enumerate(found, start=1)}
    proposals, used = [], set()
    for p in reply.picks:
        e = keyed.get((p.key or "").strip().upper())
        if e is None or e["ref"] in used:
            continue
        used.add(e["ref"])
        proposals.append({"id": uuid.uuid4().hex[:12], "ref": e["ref"], "title": e["title"], "href": e["href"],
                          "module": e["module"], "minutes": e.get("minutes") or _estimate(p.minutes),
                          "reason": " ".join((p.reason or "").split())[:300], "state": "proposed", "pick_id": None})
        if len(proposals) >= MOST_PICKS:
            break
    if not proposals and reply.picks:
        raise ValueError("The AI's picks weren't from the list it was given. Try again, or pick another model in Settings → AI.")
    _finish(day, {**done, "written_by": written_by(pid), "note": " ".join((reply.note or "").split())[:300] or None,
                  "proposals": proposals})


def _finish(day: str, changes: dict) -> None:
    row = store.row(day)
    if row is None or not row["plan"] or row["plan"]["status"] != "suggesting":
        return                                  # discarded, or asked again, while the AI wrote
    store.save(day, plan={**row["plan"], **changes})
    _changed(day)


# ── Your answers ──────────────────────────────────────────────────────

def _ready(day: str) -> tuple[dict, dict]:
    row = store.row(day)
    if row is None or not row["plan"] or row["plan"]["status"] != "ready":
        raise ValueError("There's no suggested plan for that day")
    return row, row["plan"]


def _proposal(plan: dict, proposal_id: str) -> dict:
    found = next((p for p in plan["proposals"] if p["id"] == proposal_id), None)
    if found is None:
        raise KeyError(proposal_id)
    return found


def _place(day: str, plan: dict, proposal: dict) -> None:
    """Puts the pick a proposal became where the suggestion has it among the others you accepted: right after the
    nearest accepted one before it, or else right before the nearest after it."""
    from . import days                                      # (days uses this module; this is the one way back)
    picks = [p for p in store.row(day)["picks"] if not p.get("rolled_to") and not p.get("let_go")]
    ids = [p["id"] for p in picks]
    order = plan["proposals"]
    at = order.index(proposal)
    before = [p["pick_id"] for p in order[:at] if p["state"] == "accepted" and p["pick_id"] in ids]
    after = [p["pick_id"] for p in order[at + 1:] if p["state"] == "accepted" and p["pick_id"] in ids]
    if before:
        days.move_pick(day, proposal["pick_id"], before[-1])
    elif after:
        i = ids.index(after[0])
        prev = ids[i - 1] if i else None
        if prev != proposal["pick_id"]:
            days.move_pick(day, proposal["pick_id"], prev)


def _accept(day: str, plan: dict, proposal: dict) -> None:
    from . import days
    if proposal["state"] != "proposed":
        raise ValueError("That one isn't waiting for you any more")
    try:
        pick = days.add_pick(day, ref=proposal["ref"], title=proposal["title"], href=proposal["href"],
                             minutes=proposal["minutes"])
        proposal["pick_id"] = pick["id"]
    except ValueError as e:
        if "already" not in str(e):
            raise
        mine = store.row(day)["picks"]
        proposal["pick_id"] = next(p["id"] for p in mine if p.get("ref") == proposal["ref"] and not p.get("rolled_to")
                                   and not p.get("let_go"))
    proposal["state"] = "accepted"
    _place(day, plan, proposal)


def accept(day: str, proposal_id: str) -> dict:
    """One proposal into the day's plan."""
    _, plan = _ready(day)
    proposal = _proposal(plan, proposal_id)
    _accept(day, plan, proposal)
    store.save(day, plan=plan)
    _changed(day)
    return proposal


def accept_all(day: str) -> int:
    """Every proposal still waiting, in the suggestion's order (one that's gone meanwhile stays). Returns how many."""
    _, plan = _ready(day)
    accepted = 0
    for p in [p for p in plan["proposals"] if p["state"] == "proposed"]:
        try:
            _accept(day, plan, p)
            accepted += 1
        except ValueError:
            continue
    store.save(day, plan=plan)
    _changed(day)
    return accepted


def change(day: str, proposal_id: str, changes: dict) -> dict:
    """{"state": "proposed" | "dropped", "minutes"} for one proposal that isn't in the plan yet."""
    unknown = set(changes) - {"state", "minutes"}
    if unknown:
        raise ValueError(f"Can't change {', '.join(sorted(unknown))}")
    _, plan = _ready(day)
    proposal = _proposal(plan, proposal_id)
    if proposal["state"] == "accepted":
        raise ValueError("That one is in your plan already. Change it there.")
    if "state" in changes:
        if changes["state"] not in STATES:
            raise ValueError("A suggestion is proposed or dropped")
        proposal["state"] = changes["state"]
    if "minutes" in changes:
        proposal["minutes"] = store.minutes(changes["minutes"])
    store.save(day, plan=plan)
    _changed(day)
    return proposal


def move(day: str, proposal_id: str, after_id: str | None) -> list[dict]:
    """Puts a proposal right after another (first, when after_id is None)."""
    _, plan = _ready(day)
    proposal = _proposal(plan, proposal_id)
    if after_id == proposal_id:
        raise ValueError("A suggestion can't go after itself")
    rest = [p for p in plan["proposals"] if p["id"] != proposal_id]
    ids = [p["id"] for p in rest]
    if after_id is not None and after_id not in ids:
        raise KeyError(after_id)
    rest.insert(0 if after_id is None else ids.index(after_id) + 1, proposal)
    plan["proposals"] = rest
    store.save(day, plan=plan)
    _changed(day)
    return rest
