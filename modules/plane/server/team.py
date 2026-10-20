"""The Team view's numbers: who has which open Plane items, in which states and projects, what's past due and what
nobody has. Everything is worked out from the mirror; nothing here talks to Plane.

An item is open while its state isn't in the completed or cancelled group, and it isn't archived, a draft, or gone
from Plane. Only the projects chosen in Settings → Plane count. An item with two assignees counts once for each
person, and once in the totals.
"""
import json
from datetime import date, timedelta

from core.server import db, links, module, settings

from . import store
from .client import web_url

GROUP_ORDER = ("triage", "backlog", "unstarted", "started")
GROUP_LABEL = {"triage": "Triage", "backlog": "Backlog", "unstarted": "To do", "started": "In progress"}
PRIORITY_RANK = {"urgent": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
SOON_DAYS = 7


def me_id() -> str | None:
    """The Plane member who is you: chosen in Settings → Plane, or else the owner of the API key."""
    return settings.section("plane").get("me") or store.meta("me")


def open_items(project_ids: list[str]) -> list[dict]:
    if not project_ids:
        return []
    marks = ",".join("?" * len(project_ids))
    return db.query(
        "SELECT i.id, i.project_id, i.sequence_id, i.name, i.priority, i.start_date, i.target_date, i.assignees, "
        "i.labels, i.cycle_id, i.parent_id, i.updated_at, s.id AS state_id, s.name AS state_name, "
        "s.state_group, p.identifier, p.name AS project_name, c.name AS cycle_name "
        "FROM plane_items i "
        "JOIN plane_projects p ON p.id = i.project_id AND p.removed_at IS NULL "
        "LEFT JOIN plane_states s ON s.id = i.state_id "
        "LEFT JOIN plane_cycles c ON c.id = i.cycle_id AND c.removed_at IS NULL "
        f"WHERE i.project_id IN ({marks}) AND i.removed_at IS NULL AND i.archived_at IS NULL AND i.is_draft = 0 "
        "AND coalesce(s.state_group, 'backlog') NOT IN ('completed', 'cancelled')",
        project_ids)


def _blank_split() -> dict[str, int]:
    return {g: 0 for g in GROUP_ORDER}


def rollup(today: date | None = None) -> dict:
    """Everything the Team view shows, in one answer (GET /api/plane/team)."""
    today = today or date.today()
    soon = today + timedelta(days=SOON_DAYS)
    cfg = settings.section("plane")
    mirrored = [p for p in store.projects() if p["id"] in set(cfg.get("projects") or [])]
    project_ids = [p["id"] for p in mirrored]
    members = {m["id"]: m for m in store.members(include_bots=True)}
    me = me_id()
    web = web_url(cfg.get("base_url") or "")
    slug = cfg.get("workspace_slug") or ""
    labels = {r["id"]: r["name"] for r in db.query("SELECT id, name FROM plane_labels WHERE removed_at IS NULL")}
    # What's in Traverse already: linked copies of items, and the Traverse project each Plane project goes to.
    copies = links.pairs("synced", "plane")
    linked_to = {r["project_id"]: r["local_ref"] for r in db.query("SELECT project_id, local_ref FROM plane_links")}

    def in_traverse(local_ref: str | None) -> dict | None:
        found = module.describe(local_ref) if local_ref else None
        return {"ref": local_ref, "title": found["title"], "href": found["href"]} if found else None

    people: dict[str | None, dict] = {}
    projects = {p["id"]: {"id": p["id"], "identifier": p["identifier"], "name": p["name"], "open": 0,
                          "by_group": _blank_split(), "past_due": 0, "unassigned": 0, "people": {},
                          "linked": in_traverse(linked_to.get(p["id"]))} for p in mirrored}
    totals = {"open": 0, "past_due": 0, "unassigned": 0, "due_soon": 0, "in_progress": 0}
    by_group = _blank_split()
    items = []

    def person(member_id: str | None) -> dict:
        if member_id not in people:
            m = members.get(member_id) if member_id else None
            people[member_id] = {
                "id": member_id,
                "ref": None if member_id is None else ("core:me" if member_id == me else f"plane:{member_id}"),
                "name": "No one" if member_id is None else store.member_name(m),
                "display_name": (m or {}).get("display_name") or "",
                "is_me": member_id is not None and member_id == me,
                "open": 0, "by_group": _blank_split(), "past_due": 0, "due_soon": 0, "projects": {},
            }
        return people[member_id]

    for row in open_items(project_ids):
        group = row["state_group"] or "backlog"
        group = group if group in GROUP_ORDER else "backlog"
        due = row["target_date"]
        past_due = bool(due) and due < today.isoformat()
        due_soon = bool(due) and not past_due and due <= soon.isoformat()
        assignees = json.loads(row["assignees"] or "[]")

        totals["open"] += 1
        totals["past_due"] += past_due
        totals["due_soon"] += due_soon
        totals["in_progress"] += group == "started"
        totals["unassigned"] += not assignees
        by_group[group] += 1

        proj = projects[row["project_id"]]
        proj["open"] += 1
        proj["by_group"][group] += 1
        proj["past_due"] += past_due
        proj["unassigned"] += not assignees

        for member_id in assignees or [None]:
            p = person(member_id)
            p["open"] += 1
            p["by_group"][group] += 1
            p["past_due"] += past_due
            p["due_soon"] += due_soon
            p["projects"][row["project_id"]] = p["projects"].get(row["project_id"], 0) + 1
            key = member_id or "none"
            proj["people"][key] = proj["people"].get(key, 0) + 1

        key = f"{row['identifier']}-{row['sequence_id']}"
        items.append({
            "id": row["id"], "ref": f"plane:{row['id']}", "key": key, "name": row["name"],
            "project_id": row["project_id"], "project": row["project_name"],
            "state": {"id": row["state_id"], "name": row["state_name"] or GROUP_LABEL[group], "group": group},
            "priority": row["priority"], "target_date": due, "past_due": past_due, "due_soon": due_soon,
            "assignees": [{"id": a, "name": person(a)["name"], "is_me": a == me} for a in assignees],
            "labels": [labels[lb] for lb in json.loads(row["labels"] or "[]") if lb in labels],
            "cycle": row["cycle_name"], "updated_at": row["updated_at"],
            "url": f"{web}/{slug}/browse/{key}/" if slug else web,
            "task": in_traverse(copies.get(f"plane:{row['id']}")),
        })

    # Past due first (oldest first), then by due date, then priority, then the newest.
    items.sort(key=lambda i: (not i["past_due"], i["target_date"] or "9999", PRIORITY_RANK.get(i["priority"], 9),
                              _neg(i["updated_at"])))
    named = sorted((p for k, p in people.items() if k is not None),
                   key=lambda p: (not p["is_me"], -p["open"], p["name"].lower()))
    # Team members with nothing open still get a card, after everyone who has something.
    for m in members.values():
        if not m["is_bot"] and m["is_active"] and m["removed_at"] is None and m["id"] not in people:
            named.append(person(m["id"]))
    if None in people:
        named.append(people[None])

    last = store.meta("last_pull")
    return {
        "configured": bool(cfg.get("personal_api_key") and slug),
        "workspace": slug, "web_url": web, "today": today.isoformat(),
        "projects_chosen": len(cfg.get("projects") or []),
        "pulled_at": (last or {}).get("at"),
        "totals": totals,
        "states": [{"group": g, "label": GROUP_LABEL[g], "open": by_group[g]} for g in GROUP_ORDER
                   if by_group[g] or g != "triage"],
        "people": named,
        "projects": sorted(projects.values(), key=lambda p: (-p["open"], p["name"].lower())),
        "items": items,
    }


def _neg(stamp: str | None) -> str:
    """Sorts ISO stamps newest first inside an ascending sort."""
    return "".join(chr(255 - ord(ch)) for ch in (stamp or ""))
