"""The plane module's part of the day's briefing (core/server/briefing.py, Module.brief): what moved in Plane since a
moment, read from the change log (plane_changes); items that went past due meanwhile; the team's past-due items; cycles
ending this week; and what waits for you in the Outbox. All of it comes from the mirror and the outbox: nothing here
talks to Plane.

One entry per item that moved, its changes in one line ("To do → In progress · by Sam"), "who" being whoever has it
now, so the screen can group what moved by person as well as by project. "by Sam" is said only when Sam isn't one of the
people who have the item now: the line names them already, so it would be the same name twice.
"""
import json
from datetime import date, timedelta

from core.server import briefing, db, links, module, settings

from . import push, store, team
from .linking import Where

WEEK = 7
PRIORITY = {"none": "No priority", "low": "Low", "medium": "Medium", "high": "High", "urgent": "Urgent"}
# Which change says most about an item, when it had several: that one picks the entry's kind and tone.
WEIGHT = ("removed", "done", "cancelled", "added", "assigned_you", "assigned", "state", "due", "priority", "name")
TONE = {"removed": "neutral", "done": "forest", "cancelled": "neutral", "added": "neutral", "assigned_you": "sun",
        "assigned": "neutral", "state": "sky", "due": "neutral", "priority": "neutral", "name": "neutral",
        "past_due": "trail"}


def _day(value: str) -> str:
    """"2026-10-24" → "Fri 24 Oct"."""
    d = date.fromisoformat(value[:10])
    return f"{d:%a} {d.day} {d:%b}"


class _Names:
    """Members, states and projects by id, read once (removed ones too: an old change may name them)."""
    def __init__(self):
        self.me = team.me_id()
        self.members = {m["id"]: store.member_name(m) for m in db.query("SELECT * FROM plane_members")}
        self.states = {s["id"]: s for s in db.query("SELECT id, name, state_group FROM plane_states")}
        self.projects = {p["id"]: p for p in db.query("SELECT id, name, identifier FROM plane_projects")}

    def person(self, member_id: str | None, me: str = "You") -> str:
        if member_id and member_id == self.me:
            return me
        return self.members.get(member_id, "Someone not in the workspace") if member_id else "No one"

    def people(self, member_ids: list[str], me: str = "You") -> str:
        if not member_ids:
            return "No one"
        return ", ".join(sorted((self.person(m, me) for m in member_ids), key=lambda n: (n != me, n.lower())))

    def state(self, state_id: str | None) -> str:
        return (self.states.get(state_id) or {}).get("name") or "No state"

    def group(self, state_id: str | None) -> str:
        return (self.states.get(state_id) or {}).get("state_group") or "backlog"


def _item_entry(item: dict, names: _Names, where: Where) -> dict:
    key = where.key(item)
    return {"id": item["id"], "title": f"{key} {item['name']}".strip(), "href": f"#/plane/team?item={item['id']}",
            "url": where.url(item), "project": (names.projects.get(item["project_id"]) or {}).get("name"),
            "who": names.people(json.loads(item["assignees"] or "[]"))}


def _phrase(field: str, before, after, names: _Names) -> tuple[str, str] | None:
    """One field's change as (kind, words), or None when it ended where it started."""
    if before == after:
        return None
    if field == "added":
        return "added", "Added"
    if field == "removed":
        return "removed", "Removed from Plane"
    if field == "state":
        group = names.group(after)
        kind = "done" if group == "completed" else "cancelled" if group == "cancelled" else "state"
        return kind, f"{names.state(before)} → {names.state(after)}"
    if field == "assignees":
        was = f" (was {names.people(before, me='you')})" if before else ""
        if not after:
            return "assigned", f"No one on it{was}"
        kind = "assigned_you" if names.me in after and names.me not in (before or []) else "assigned"
        now = "Assigned to you" if after == [names.me] else f"Now with {names.people(after, me='you')}"
        return kind, now + was
    if field == "due":
        if not after:
            return "due", "Due date taken off"
        return "due", f"Due {_day(after)}" + (f" (was {_day(before)})" if before else "")
    if field == "priority":
        return "priority", f"{PRIORITY.get(after, after)} priority" + (f" (was {PRIORITY.get(before, before)})" if before else "")
    if field == "name":
        return "name", f"Renamed (was “{before}”)"
    return None


def _moved(since: str, today: date, chosen: list[str], names: _Names, where: Where) -> list[dict]:
    changes = store.changes(since, chosen)
    by_item: dict[str, dict] = {}
    for c in changes:
        seen = by_item.setdefault(c["item_id"], {"fields": {}, "at": c["at"], "by": None})
        first = seen["fields"].get(c["field"])
        seen["fields"][c["field"]] = (first[0] if first else c["before"], c["after"])   # first before, last after
        seen["at"], seen["by"] = c["at"], c["by"] or seen["by"]
    item_ids = list(by_item)
    still_open = team.open_items(chosen)
    open_ids = {r["id"] for r in still_open}
    since_day = briefing.local_day(since).isoformat()
    for r in still_open:                                   # gone past due meanwhile: due since then, before today
        if r["target_date"] and since_day <= r["target_date"] < today.isoformat() and r["id"] not in by_item:
            by_item[r["id"]] = {"fields": {}, "at": r["target_date"], "by": None}
            item_ids.append(r["id"])
    rows = {r["id"]: r for r in db.query(
        f"SELECT * FROM plane_items WHERE id IN ({','.join('?' * len(item_ids))})", item_ids)} if item_ids else {}

    out = []
    for item_id, seen in by_item.items():
        item = rows.get(item_id)
        if not item:
            continue
        found = [p for f, (b, a) in seen["fields"].items() if (p := _phrase(f, b, a, names))]
        due = item["target_date"]
        if item_id in open_ids and due and since_day <= due < today.isoformat():
            found.append(("past_due", f"Went past due ({_day(due)})"))
        if not found:
            continue
        found.sort(key=lambda p: WEIGHT.index(p[0]) if p[0] in WEIGHT else len(WEIGHT))
        kind = found[0][0]
        words = " · ".join(w for _, w in found)
        if seen["by"] and seen["by"] not in json.loads(item["assignees"] or "[]"):
            words += f" · by {names.person(seen['by'], me='you')}"
        out.append({**_item_entry(item, names, where), "what": words, "kind": kind, "tone": TONE.get(kind, "neutral"),
                    "when": seen["at"]})
    out.sort(key=lambda e: e["when"] or "", reverse=True)
    return out


def _past_due(today: date, chosen: list[str], names: _Names, where: Where) -> list[dict]:
    """The team's open items past their due date, oldest first. Yours that are linked tasks are left out: the tasks
    module shows those already."""
    copies = links.pairs("synced", "plane")
    out = []
    for r in sorted(team.open_items(chosen), key=lambda r: r["target_date"] or ""):
        if not r["target_date"] or r["target_date"] >= today.isoformat():
            continue
        assignees = json.loads(r["assignees"] or "[]")
        if names.me in assignees and f"plane:{r['id']}" in copies:
            continue
        out.append({**_item_entry(r, names, where), "what": "Past due", "kind": "past_due", "tone": "trail",
                    "when": r["target_date"]})
    return out


def _cycles(today: date, chosen: list[str], names: _Names) -> list[dict]:
    if not chosen:
        return []
    marks = ",".join("?" * len(chosen))
    cycles = db.query(f"SELECT * FROM plane_cycles WHERE removed_at IS NULL AND project_id IN ({marks}) "
                      "AND end_date >= ? AND end_date <= ? ORDER BY end_date",
                      (*chosen, today.isoformat(), (today + timedelta(days=WEEK)).isoformat()))
    open_by_cycle: dict[str, int] = {}
    for r in team.open_items(chosen):
        if r["cycle_id"]:
            open_by_cycle[r["cycle_id"]] = open_by_cycle.get(r["cycle_id"], 0) + 1
    out = []
    for c in cycles:
        n = open_by_cycle.get(c["id"], 0)
        ends = "Cycle ends today" if c["end_date"] == today.isoformat() else "Cycle ends"
        out.append({"id": c["id"], "title": c["name"], "href": f"#/plane/team?project={c['project_id']}",
                    "what": ends + (f" · {n} still open" if n else " · nothing open"), "kind": "cycle",
                    "tone": "sun" if n and c["end_date"] == today.isoformat() else "neutral", "when": c["end_date"],
                    "project": (names.projects.get(c["project_id"]) or {}).get("name")})
    return out


WAITING_WORDS = {"waiting": "Waiting for you to send it", "stopped": "Stopped: changed in Plane meanwhile",
                 "failed": "Didn't reach Plane"}


def _outbox(names: _Names) -> list[dict]:
    out = []
    for p in db.query(f"SELECT * FROM plane_pushes WHERE status IN {push.NEEDS_YOU} ORDER BY created_at"):
        task = module.describe(p["local_ref"]) or {}
        out.append({"id": p["id"], "title": task.get("title") or "A change for Plane", "href": f"#/plane/outbox?push={p['id']}",
                    "what": WAITING_WORDS[p["status"]] + (" (a new item)" if p["kind"] == "create" else ""),
                    "kind": "outbox", "tone": "trail" if p["status"] == "failed" else "sun", "when": p["created_at"],
                    "project": (names.projects.get(p["project_id"]) or {}).get("name")})
    return out


def brief(since: str, today: date) -> dict:
    cfg = settings.section("plane")
    names = _Names()
    waiting = _outbox(names)
    if not (cfg.get("personal_api_key") and cfg.get("workspace_slug")):
        return {"waiting": waiting}
    chosen = [p for p in cfg.get("projects") or [] if p in names.projects]
    where = Where()
    return {"moved": _moved(since, today, chosen, names, where), "today": _past_due(today, chosen, names, where),
            "ahead": _cycles(today, chosen, names), "waiting": waiting}
