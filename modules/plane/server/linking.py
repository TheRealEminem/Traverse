"""Linking Plane to Traverse (PLAN.md chunk 6): which Traverse project each Plane project goes to and what its states
mean there, bringing Plane items in as linked tasks, and telling Traverse when they change in Plane. Nothing here
talks to Plane: everything works from the mirror (sending is push.py's).

A Plane value doesn't always say one Traverse value: a state can mean Doing or Waiting, an item can have several
assignees, and notes go through HTML. So when a push sends one, plane_sent remembers what it meant ("this state is
Waiting") for as long as Plane keeps that value; the item then reads back as what you sent, rather than as a change.

This module never reads or writes tasks' tables (D5, ARCHITECTURE rule 1). It publishes the shared work.* contracts
(core/server/contracts.py) with Plane's values already turned into Traverse's (§3.2), and finds what's linked through
the host's links, kind "synced": "tasks:<project id>" → "plane:<project id>" and "tasks:<id>" → "plane:<item id>".
Whoever holds the local copies (tasks) decides what follows and what gets flagged.
"""
import json
import logging

from core.server import contracts, db, events, links, module, settings

from . import html, store, team
from .client import web_url

log = logging.getLogger("plane.linking")

SOURCE = "Plane"
STATUSES = ("todo", "doing", "waiting", "done", "dropped")
STATUS_LABEL = {"todo": "To do", "doing": "Doing", "waiting": "Waiting", "done": "Done", "dropped": "Dropped"}
# Plane's state groups, read as Traverse statuses when the project's map doesn't say otherwise.
GROUP_STATUS = {"triage": "todo", "backlog": "todo", "unstarted": "todo", "started": "doing", "completed": "done",
                "cancelled": "dropped"}
# Which group each status's state is preset from (§3.2), and the words that make a started state "waiting".
STATUS_GROUP = {"todo": "unstarted", "doing": "started", "waiting": "started", "done": "completed", "dropped": "cancelled"}
WAITING_WORDS = ("wait", "block", "hold", "review")
PRIORITY = {"none": 0, "low": 1, "medium": 2, "high": 3, "urgent": 4}
PRIORITY_NAME = {n: name for name, n in PRIORITY.items()}

# Traverse's fields (grouped as the tasks module groups them: an assignee is a ref and a name), each with its
# columns in contracts.WORK_FIELDS, the Plane field it goes to (§3.2) and its label.
FIELDS = {
    "text": (("text",), "name", "Title"),
    "notes": (("notes",), "description_html", "Notes"),
    "status": (("status",), "state", "Status"),
    "priority": (("priority",), "priority", "Priority"),
    "start_on": (("start_on",), "start_date", "Start"),
    "due_on": (("due_on",), "target_date", "Due"),
    "assignee": (("assignee_ref", "assignee_name"), "assignees", "Assignee"),
}
_MIRROR_COLUMN = {"name": "name", "description_html": "description_html", "state": "state_id", "priority": "priority",
                  "start_date": "start_date", "target_date": "target_date", "assignees": "assignees"}


def raw(item: dict, field: str):
    """A mirror row's Plane value for one of Traverse's fields: the name, the HTML, the state id, the sorted list of
    assignee ids…"""
    value = item[_MIRROR_COLUMN[FIELDS[field][1]]]
    if field == "assignee":
        return sorted(json.loads(value or "[]"))
    if field in ("start_on", "due_on"):
        return _day(value)
    return value


def ref(plane_id: str) -> str:
    return links.ref("plane", plane_id)


# ── States and the map ────────────────────────────────────────────────

def states(project_id: str) -> list[dict]:
    return db.query("SELECT id, name, state_group, color, sequence, is_default FROM plane_states "
                    "WHERE project_id = ? AND removed_at IS NULL ORDER BY sequence, name", (project_id,))


def default_map(project_id: str) -> dict[str, str | None]:
    """Each status's Plane state, preset from its group: the project's default state when it's in the group, else the
    group's first; "waiting" prefers a started state that sounds like waiting ("Blocked", "In review")."""
    found = states(project_id)

    def first(groups: tuple[str, ...], prefer=lambda s: False) -> str | None:
        for group in groups:
            in_group = [s for s in found if s["state_group"] == group]
            if in_group:
                return next((s for s in in_group if prefer(s)), in_group[0])["id"]
        return None

    return {
        "todo": first(("unstarted", "backlog"), lambda s: s["is_default"]),
        "doing": first(("started",)),
        "waiting": first(("started",), lambda s: any(w in s["name"].lower() for w in WAITING_WORDS)),
        "done": first(("completed",)),
        "dropped": first(("cancelled",)),
    }


def _link_row(project_id: str) -> dict | None:
    return db.one("SELECT * FROM plane_links WHERE project_id = ?", (project_id,))


def state_map(project_id: str) -> dict[str, str | None]:
    """The map in use: what you chose, with the preset for anything not chosen or whose state is gone from Plane."""
    row = _link_row(project_id)
    chosen = json.loads(row["state_map"]) if row else {}
    there = {s["id"] for s in states(project_id)}
    preset = default_map(project_id)
    return {s: chosen.get(s) if chosen.get(s) in there else preset[s] for s in STATUSES}


def status_for(state_id: str | None, mapping: dict[str, str | None]) -> str | None:
    """A Plane state as a Traverse status: the status mapped to it (its group's own when several are), or else its
    group's. None when the item has no state Traverse knows."""
    if not state_id:
        return None
    row = db.one("SELECT state_group FROM plane_states WHERE id = ?", (state_id,))
    if row is None:
        return None
    by_group = GROUP_STATUS.get(row["state_group"], "todo")
    mapped = [s for s in STATUSES if mapping.get(s) == state_id]
    return by_group if by_group in mapped or not mapped else mapped[0]


# ── A Plane item as Traverse's fields (§3.2) ──────────────────────────

def _day(value) -> str | None:
    return str(value)[:10] if value else None


def _remembered() -> dict[tuple[str, str], tuple]:
    """{(item id, field): (Plane's value right after a push, what it means in Traverse)} from plane_sent."""
    return {(r["item_id"], r["field"]): (json.loads(r["plane_value"]), json.loads(r["value"]))
            for r in db.query("SELECT item_id, field, plane_value, value FROM plane_sent")}


def remember(item_id: str, field: str, plane_value, value: dict, push_id: str) -> None:
    """After a push: while Plane keeps plane_value for this field, it means `value` ({"status": "waiting"})."""
    db.execute("INSERT INTO plane_sent (id, item_id, field, plane_value, value, push_id) VALUES (?, ?, ?, ?, ?, ?) "
               "ON CONFLICT(item_id, field) DO UPDATE SET plane_value = excluded.plane_value, value = excluded.value, "
               "push_id = excluded.push_id",
               (db.new_id(), item_id, field, json.dumps(plane_value), json.dumps(value), push_id))


def forget_changed(item_ids: list[str] | None = None) -> int:
    """Drops what was remembered about values Plane no longer holds (someone changed them since): those read as Plane
    says again. Returns how many it dropped."""
    rows = db.query("SELECT s.id AS sent_id, s.field AS sent_field, s.plane_value AS sent_value, i.* "
                    "FROM plane_sent s JOIN plane_items i ON i.id = s.item_id")
    stale = [r["sent_id"] for r in rows if (item_ids is None or r["id"] in item_ids)
             and json.loads(r["sent_value"]) != raw(r, r["sent_field"])]
    for sent_id in stale:
        db.execute("DELETE FROM plane_sent WHERE id = ?", (sent_id,))
    return len(stale)


class Where:
    """An item's key ("SOFTWARE-5") and the address it opens at in Plane, for many items (read once)."""
    def __init__(self):
        cfg = settings.section("plane")
        self.web = web_url(cfg.get("base_url") or "")
        self.slug = cfg.get("workspace_slug") or ""
        self.identifiers = {p["id"]: p["identifier"] for p in store.projects()}

    def key(self, item: dict) -> str:
        ident = self.identifiers.get(item["project_id"])
        return f"{ident}-{item['sequence_id']}" if ident else ""

    def url(self, item: dict) -> str | None:
        key = self.key(item)
        return f"{self.web}/{self.slug}/browse/{key}/" if key and self.slug else None


class _Context(Where):
    """What turning many items into fields needs, read once: you, the members, each project's map, the web address,
    and what pushes left Plane's values meaning."""
    def __init__(self):
        super().__init__()
        self.me = team.me_id()
        self.members = {m["id"]: m for m in store.members(include_bots=True)}
        self.maps: dict[str, dict] = {}
        self.sent = _remembered()

    def mapping(self, project_id: str) -> dict:
        if project_id not in self.maps:
            self.maps[project_id] = state_map(project_id)
        return self.maps[project_id]

    def fields(self, item: dict) -> dict:
        assignees = json.loads(item["assignees"] or "[]")
        if self.me and self.me in assignees:
            who, name = "core:me", None
        elif assignees:
            pick = min(assignees, key=lambda a: (store.member_name(self.members.get(a)).lower(), a))
            who, name = ref(pick), store.member_name(self.members.get(pick))
        else:
            who, name = None, None
        out = {"text": item["name"], "notes": html.to_markdown(item["description_html"]),
               "priority": PRIORITY.get(item["priority"] or "none", 0), "start_on": _day(item["start_date"]),
               "due_on": _day(item["target_date"]), "assignee_ref": who, "assignee_name": name}
        status = status_for(item["state_id"], self.mapping(item["project_id"]))
        if status:
            out["status"] = status
        for field in FIELDS:
            known = self.sent.get((item["id"], field))
            if known and known[0] == raw(item, field):
                out.update(known[1])          # what you sent, while Plane still has it
        return out


def fields_for(item: dict) -> dict:
    return _Context().fields(item)


# ── Linking projects ──────────────────────────────────────────────────

def _project(project_id: str) -> dict:
    row = db.one("SELECT * FROM plane_projects WHERE id = ? AND removed_at IS NULL", (project_id,))
    if row is None:
        raise KeyError(project_id)
    return row


def link(project_id: str, local_ref: str | None = None) -> dict:
    """Links a Plane project to a Traverse project: local_ref ("tasks:<id>"), or a new one named after it. Its map
    starts from the presets."""
    project = _project(project_id)
    if _link_row(project_id):
        raise ValueError(f"{project['name']} is linked already. Unlink it first to choose another project.")
    there = ref(project_id)
    if local_ref:
        if not module.describe(local_ref):
            raise ValueError("That Traverse project doesn't exist")
        taken = db.one("SELECT p.name FROM plane_links l JOIN plane_projects p ON p.id = l.project_id "
                       "WHERE l.local_ref = ?", (local_ref,))
        if taken:
            raise ValueError(f"That project is linked to {taken['name']} already")
        links.add(local_ref, there, "synced")
    else:
        events.publish(contracts.WORK_PROJECT_ARRIVED, {"ref": there, "name": project["name"],
                                                        "summary": project["description"] or None, "source": SOURCE})
        made = [r for r in links.sources(there, "synced") if module.describe(r)]
        if not made:
            raise ValueError("Nothing in Traverse took the project. Is Projects turned on?")
        local_ref = made[0]
    now = db.now()
    db.execute("INSERT INTO plane_links (project_id, local_ref, state_map, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
               (project_id, local_ref, json.dumps(default_map(project_id)), now, now))
    events.publish("plane.links.changed", {"project_id": project_id})
    return view(project_id)


def unlink(project_id: str) -> bool:
    """The projects stop being linked. Both stay, and so do the tasks brought in (they keep following their items)."""
    row = _link_row(project_id)
    if row is None:
        return False
    db.execute("DELETE FROM plane_links WHERE project_id = ?", (project_id,))
    links.remove(row["local_ref"], ref(project_id), "synced")
    events.publish("plane.links.changed", {"project_id": project_id})
    return True


def set_map(project_id: str, changes: dict) -> dict:
    """Chooses which Plane state some statuses mean ({"waiting": "<state id>"}). Linked tasks of the project are
    told their items again, so a status that now reads differently follows (if you haven't changed it)."""
    project = _project(project_id)
    row = _link_row(project_id)
    if row is None:
        raise ValueError(f"Link {project['name']} to a Traverse project first")
    unknown = set(changes) - set(STATUSES)
    if unknown:
        raise ValueError(f"Can't map {', '.join(sorted(unknown))}: statuses are {', '.join(STATUSES)}")
    there = {s["id"]: s for s in states(project_id)}
    for status, state_id in changes.items():
        if state_id not in there:
            raise ValueError(f"That isn't one of {project['name']}'s states")
    chosen = {**json.loads(row["state_map"]), **changes}
    db.execute("UPDATE plane_links SET state_map = ?, updated_at = ? WHERE project_id = ?",
               (json.dumps(chosen), db.now(), project_id))
    publish_linked(project_id)
    events.publish("plane.links.changed", {"project_id": project_id})
    return view(project_id)


def local_deleted(payload: dict) -> None:
    """contracts.ITEM_DELETED: a Traverse project linked to a Plane project is gone, so the link is too."""
    db.execute("DELETE FROM plane_links WHERE local_ref = ?", (payload["ref"],))


# ── Bringing items in, and telling Traverse when they change ──────────

def linked_items() -> dict[str, str]:
    """{plane item id: local ref} for every Plane item with a linked copy."""
    return {there.split(":", 1)[1]: here for there, here in links.pairs("synced", "plane").items()}


def bring(item_ids: list[str]) -> dict:
    """Brings Plane items into Traverse as linked tasks. Each goes into the Traverse project linked to its Plane
    project; a project not linked yet gets a new Traverse project first. Items already in Traverse are left as they
    are. Returns what happened, for the screen."""
    item_ids = list(dict.fromkeys(item_ids))
    if not item_ids:
        return {"brought": 0, "already": 0, "new_projects": [], "missing": 0}
    marks = ",".join("?" * len(item_ids))
    rows = db.query(f"SELECT * FROM plane_items WHERE id IN ({marks}) AND removed_at IS NULL", item_ids)
    linked = linked_items()
    waiting = [r for r in rows if r["id"] not in linked]
    new_projects = []
    for project_id in dict.fromkeys(r["project_id"] for r in waiting):
        if not _link_row(project_id):
            new_projects.append(link(project_id)["name"])
    ctx = _Context()
    for item in waiting:
        events.publish(contracts.WORK_ARRIVED, {"ref": ref(item["id"]), "fields": ctx.fields(item),
                                                "project_ref": ref(item["project_id"]), "source": SOURCE,
                                                "url": ctx.url(item)})
    now_linked = linked_items()
    brought = sum(1 for r in waiting if r["id"] in now_linked)
    if waiting and not brought:
        raise ValueError("Nothing in Traverse took the items. Is Projects turned on?")
    return {"brought": brought, "already": len(rows) - len(waiting), "new_projects": new_projects,
            "missing": len(item_ids) - len(rows)}


def mine() -> list[str]:
    """Open items assigned to you in the mirrored projects (the Team view's "You")."""
    me = team.me_id()
    if not me:
        return []
    chosen = list(settings.section("plane").get("projects") or [])
    return [r["id"] for r in team.open_items(chosen) if me in json.loads(r["assignees"] or "[]")]


def publish_linked(project_id: str | None = None) -> int:
    """Tells Traverse what every linked item looks like in Plane now (or every one in one project): updated, or
    removed when the mirror says it's gone. The other side follows what changed and ignores what didn't, so telling
    it twice is harmless. Returns how many it told."""
    linked = linked_items()
    if not linked:
        return 0
    forget_changed()
    ids = list(linked)
    rows = []
    for chunk in (ids[i:i + 500] for i in range(0, len(ids), 500)):
        sql = f"SELECT * FROM plane_items WHERE id IN ({','.join('?' * len(chunk))})"
        rows += db.query(sql + (" AND project_id = ?" if project_id else ""), (*chunk, *([project_id] if project_id else [])))
    ctx = _Context()
    for item in rows:
        _publish(item, ctx)
    return len(rows)


def publish_made(item_id: str, local_ref: str) -> None:
    """A task sent from Traverse was made in Plane: it becomes the item's linked copy (contracts.WORK_ARRIVED with
    local_ref), agreeing with what Plane holds now."""
    item = db.one("SELECT * FROM plane_items WHERE id = ?", (item_id,))
    ctx = _Context()
    events.publish(contracts.WORK_ARRIVED, {"ref": ref(item_id), "fields": ctx.fields(item), "local_ref": local_ref,
                                            "project_ref": ref(item["project_id"]), "source": SOURCE,
                                            "url": ctx.url(item)})


def publish_item(item_id: str, take: list[str] | None = None) -> None:
    """Tells Traverse what one linked item looks like in Plane now, as a push just read or wrote it. take: Traverse
    fields you chose Plane's value for, so they follow even though you'd changed them."""
    forget_changed([item_id])
    item = db.one("SELECT * FROM plane_items WHERE id = ?", (item_id,))
    if item is not None and item_id in linked_items():
        _publish(item, _Context(), [c for f in take or [] for c in FIELDS[f][0]])


def _publish(item: dict, ctx: _Context, take: list[str] | None = None) -> None:
    there = ref(item["id"])
    if item["removed_at"]:
        events.publish(contracts.WORK_REMOVED_ELSEWHERE, {"ref": there, "source": SOURCE})
    else:
        events.publish(contracts.WORK_UPDATED_ELSEWHERE, {"ref": there, "fields": ctx.fields(item), "source": SOURCE,
                                                          "url": ctx.url(item), **({"take": take} if take else {})})


# ── What the Linking page shows ───────────────────────────────────────

def view(project_id: str) -> dict:
    project = _project(project_id)
    row = _link_row(project_id)
    local = module.describe(row["local_ref"]) if row else None
    me = team.me_id()
    linked = linked_items()
    open_rows = team.open_items([project_id])
    mine_rows = [r for r in open_rows if me and me in json.loads(r["assignees"] or "[]")]
    return {
        "id": project["id"], "identifier": project["identifier"], "name": project["name"],
        "link": row and {"local_ref": row["local_ref"], "title": local["title"] if local else None,
                         "href": local["href"] if local else None, "created_at": row["created_at"],
                         "state_map": state_map(project_id)},
        "preset": default_map(project_id),
        "states": [{"id": s["id"], "name": s["name"], "group": s["state_group"], "color": s["color"]}
                   for s in states(project_id)],
        "open": len(open_rows), "mine": len(mine_rows),
        "in_traverse": sum(1 for i in db.query("SELECT id FROM plane_items WHERE project_id = ? AND removed_at IS NULL",
                                               (project_id,)) if i["id"] in linked),
        "open_waiting": [r["id"] for r in open_rows if r["id"] not in linked],
        "mine_waiting": [r["id"] for r in mine_rows if r["id"] not in linked],
    }


def overview() -> dict:
    """GET /api/plane/links: every mirrored project, linked or not, and your open items not in Traverse yet."""
    chosen = set(settings.section("plane").get("projects") or [])
    projects = [view(p["id"]) for p in store.projects() if p["id"] in chosen]
    return {"projects": projects, "statuses": [{"value": s, "label": STATUS_LABEL[s], "group": STATUS_GROUP[s]}
                                               for s in STATUSES],
            "mine_waiting": [i for p in projects for i in p["mine_waiting"]],
            "mine": sum(p["mine"] for p in projects)}
