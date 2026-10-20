"""The plane module's tables (plane_*): a read-only mirror of the team's Plane workspace, written only by the pull.

Rows keep Plane's own ids (random UUIDs, so they merge as safely as db.new_id() ones), which makes a Plane item's
ref "plane:<item id>" and a member's "plane:<member id>". A pull writes a whole snapshot in one transaction and only
touches rows whose values changed, so running it twice changes nothing. Something that disappears from Plane isn't
deleted here: it gets `removed_at`, and comes back if Plane shows it again.

plane_links isn't part of the mirror: it's yours, which Traverse project each Plane project goes to and what its
states mean there (linking.py).
"""
import json

from core.server import db

MIGRATIONS = [
    """
    CREATE TABLE plane_projects (
        id          TEXT PRIMARY KEY,          -- Plane's project id
        identifier  TEXT NOT NULL,             -- the work item prefix, "SOFTWARE"
        name        TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        archived_at TEXT,
        removed_at  TEXT                       -- gone from Plane (or no longer visible to the key) as of this time
    );
    CREATE TABLE plane_members (
        id           TEXT PRIMARY KEY,         -- Plane's user id
        display_name TEXT NOT NULL DEFAULT '',
        first_name   TEXT NOT NULL DEFAULT '',
        last_name    TEXT NOT NULL DEFAULT '',
        email        TEXT,
        role         TEXT,                     -- owner, admin, member, guest
        is_bot       INTEGER NOT NULL DEFAULT 0,
        is_active    INTEGER NOT NULL DEFAULT 1,
        removed_at   TEXT
    );
    CREATE TABLE plane_states (
        id          TEXT PRIMARY KEY,
        project_id  TEXT NOT NULL,
        name        TEXT NOT NULL,
        state_group TEXT NOT NULL,             -- backlog, unstarted, started, completed, cancelled (or triage)
        color       TEXT,
        sequence    REAL NOT NULL DEFAULT 0,
        is_default  INTEGER NOT NULL DEFAULT 0,
        removed_at  TEXT
    );
    CREATE INDEX plane_states_project ON plane_states(project_id);
    CREATE TABLE plane_labels (
        id         TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        name       TEXT NOT NULL,
        color      TEXT,
        parent_id  TEXT,
        removed_at TEXT
    );
    CREATE INDEX plane_labels_project ON plane_labels(project_id);
    CREATE TABLE plane_cycles (
        id         TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        name       TEXT NOT NULL,
        start_date TEXT,
        end_date   TEXT,
        status     TEXT,                       -- current, upcoming, completed, draft
        removed_at TEXT
    );
    CREATE INDEX plane_cycles_project ON plane_cycles(project_id);
    CREATE TABLE plane_items (
        id               TEXT PRIMARY KEY,     -- Plane's work item id
        project_id       TEXT NOT NULL,
        sequence_id      INTEGER NOT NULL,     -- the number in "SOFTWARE-5"
        name             TEXT NOT NULL,
        description_html TEXT NOT NULL DEFAULT '',
        state_id         TEXT,
        priority         TEXT NOT NULL DEFAULT 'none',   -- none, low, medium, high, urgent
        start_date       TEXT,
        target_date      TEXT,                 -- the due date
        assignees        TEXT NOT NULL DEFAULT '[]',     -- JSON list of member ids, sorted
        labels           TEXT NOT NULL DEFAULT '[]',     -- JSON list of label ids, sorted
        cycle_id         TEXT,
        parent_id        TEXT,
        is_draft         INTEGER NOT NULL DEFAULT 0,
        completed_at     TEXT,
        archived_at      TEXT,
        created_by       TEXT,
        created_at       TEXT,
        updated_at       TEXT,                 -- Plane's: the version this copy is of
        removed_at       TEXT
    );
    CREATE INDEX plane_items_project ON plane_items(project_id);
    CREATE TABLE plane_meta (
        key   TEXT PRIMARY KEY,                -- "me" (the key's own member), "workspace", "last_pull"
        value TEXT NOT NULL                    -- JSON
    );
    """,
    """
    CREATE TABLE plane_links (
        project_id  TEXT PRIMARY KEY,          -- the Plane project
        local_ref   TEXT NOT NULL UNIQUE,      -- the Traverse project it goes to ("tasks:<id>")
        state_map   TEXT NOT NULL DEFAULT '{}',-- JSON: Traverse status -> the Plane state it means in this project
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    );
    """,
]

MIRROR_TABLES = ("plane_projects", "plane_members", "plane_states", "plane_labels", "plane_cycles", "plane_items")

# The columns a pull writes, per table (everything except id and removed_at).
COLUMNS = {
    "plane_projects": ("identifier", "name", "description", "archived_at"),
    "plane_members": ("display_name", "first_name", "last_name", "email", "role", "is_bot", "is_active"),
    "plane_states": ("project_id", "name", "state_group", "color", "sequence", "is_default"),
    "plane_labels": ("project_id", "name", "color", "parent_id"),
    "plane_cycles": ("project_id", "name", "start_date", "end_date", "status"),
    "plane_items": ("project_id", "sequence_id", "name", "description_html", "state_id", "priority", "start_date",
                    "target_date", "assignees", "labels", "cycle_id", "parent_id", "is_draft", "completed_at",
                    "archived_at", "created_by", "created_at", "updated_at"),
}

OPEN_GROUPS = ("backlog", "unstarted", "started", "triage")   # everything not completed or cancelled


# ── Turning Plane's JSON into rows ─────────────────────────────────────

def _id(value) -> str | None:
    """Plane sends a related thing as its id, or (with ?expand=) as an object holding one."""
    if isinstance(value, dict):
        return value.get("id")
    return value or None


def _ids(values) -> str:
    return json.dumps(sorted({i for i in (_id(v) for v in values or []) if i}))


ROLE_NAMES = {20: "admin", 15: "member", 5: "guest", 10: "viewer"}


def project_row(p: dict) -> dict:
    return {"id": p["id"], "identifier": p.get("identifier") or "", "name": p.get("name") or "Untitled project",
            "description": p.get("description") or "", "archived_at": p.get("archived_at")}


def member_row(m: dict) -> dict:
    # Workspace members come flat; project members (and some versions) nest the person under "member".
    person = m.get("member") if isinstance(m.get("member"), dict) else m
    role = m.get("role_slug") or m.get("role")
    return {"id": person["id"], "display_name": person.get("display_name") or "",
            "first_name": person.get("first_name") or "", "last_name": person.get("last_name") or "",
            "email": person.get("email") or None,
            "role": ROLE_NAMES.get(role, str(role)) if isinstance(role, int) else role,
            "is_bot": int(bool(person.get("is_bot") or m.get("is_bot"))),
            "is_active": int(m.get("is_active", person.get("is_active", True)) is not False)}


def state_row(s: dict, project_id: str) -> dict:
    return {"id": s["id"], "project_id": _id(s.get("project")) or project_id, "name": s.get("name") or "",
            "state_group": s.get("group") or "backlog", "color": s.get("color"),
            "sequence": float(s.get("sequence") or 0), "is_default": int(bool(s.get("default")))}


def label_row(lb: dict, project_id: str) -> dict:
    return {"id": lb["id"], "project_id": _id(lb.get("project")) or project_id, "name": lb.get("name") or "",
            "color": lb.get("color"), "parent_id": _id(lb.get("parent"))}


def cycle_row(c: dict, project_id: str) -> dict:
    return {"id": c["id"], "project_id": _id(c.get("project")) or project_id, "name": c.get("name") or "",
            "start_date": (c.get("start_date") or None) and str(c["start_date"])[:10],
            "end_date": (c.get("end_date") or None) and str(c["end_date"])[:10],
            "status": (c.get("status") or None) and str(c["status"]).lower()}


def item_row(i: dict, project_id: str) -> dict:
    return {"id": i["id"], "project_id": _id(i.get("project")) or project_id, "sequence_id": int(i.get("sequence_id") or 0),
            "name": i.get("name") or "", "description_html": i.get("description_html") or "",
            "state_id": _id(i.get("state")), "priority": i.get("priority") or "none",
            "start_date": i.get("start_date"), "target_date": i.get("target_date"),
            "assignees": _ids(i.get("assignees")), "labels": _ids(i.get("labels")),
            "cycle_id": _id(i.get("cycle_id") or i.get("cycle")), "parent_id": _id(i.get("parent")),
            "is_draft": int(bool(i.get("is_draft"))), "completed_at": i.get("completed_at"),
            "archived_at": i.get("archived_at"), "created_by": _id(i.get("created_by")),
            "created_at": i.get("created_at"), "updated_at": i.get("updated_at")}


# ── Writing a snapshot ─────────────────────────────────────────────────

def _upsert(conn, table: str, rows: list[dict]) -> int:
    """Inserts new rows and updates changed ones; a row that's the same as before isn't touched. Returns how many
    rows changed."""
    cols = COLUMNS[table]
    every = ("id", *cols, "removed_at")
    changed_if = " OR ".join(f"{table}.{c} IS NOT excluded.{c}" for c in (*cols, "removed_at"))
    sql = (f"INSERT INTO {table} ({', '.join(every)}) VALUES ({', '.join('?' * len(every))}) "
           f"ON CONFLICT(id) DO UPDATE SET {', '.join(f'{c} = excluded.{c}' for c in (*cols, 'removed_at'))} "
           f"WHERE {changed_if}")
    changed = 0
    for row in rows:
        changed += conn.execute(sql, (row["id"], *(row[c] for c in cols), None)).rowcount
    return changed


def _mark_removed(conn, table: str, keep: list[str], stamp: str, where: str = "1", args: tuple = ()) -> int:
    """Rows of `table` (within `where`) that Plane no longer shows get removed_at, once."""
    marks = ",".join("?" * len(keep)) or "''"
    return conn.execute(f"UPDATE {table} SET removed_at = ? WHERE removed_at IS NULL AND {where} AND id NOT IN ({marks})",
                        (stamp, *args, *keep)).rowcount


def apply(snapshot: dict) -> dict[str, int]:
    """Writes one pull's snapshot: {"projects": [...], "members": [...], "pulled": {project_id: {"states": [...],
    "labels": [...], "cycles": [...], "items": [...]}}} of rows (see the *_row functions). Projects that weren't
    pulled this time keep what they had. Returns how many rows changed per table; all zeros means nothing did."""
    stamp = db.now()
    out = {t: 0 for t in MIRROR_TABLES}
    with db.connect() as conn:
        out["plane_projects"] += _upsert(conn, "plane_projects", snapshot["projects"])
        out["plane_projects"] += _mark_removed(conn, "plane_projects", [p["id"] for p in snapshot["projects"]], stamp)
        out["plane_members"] += _upsert(conn, "plane_members", snapshot["members"])
        out["plane_members"] += _mark_removed(conn, "plane_members", [m["id"] for m in snapshot["members"]], stamp)
        for project_id, parts in snapshot["pulled"].items():
            for name in ("states", "labels", "cycles", "items"):
                table = f"plane_{name}"
                out[table] += _upsert(conn, table, parts[name])
                out[table] += _mark_removed(conn, table, [r["id"] for r in parts[name]], stamp, "project_id = ?",
                                            (project_id,))
    return out


# ── Small facts the pull keeps ─────────────────────────────────────────

def meta(key: str, default=None):
    row = db.one("SELECT value FROM plane_meta WHERE key = ?", (key,))
    return json.loads(row["value"]) if row else default


def set_meta(key: str, value) -> None:
    db.execute("INSERT INTO plane_meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
               (key, json.dumps(value)))


# ── Reading ────────────────────────────────────────────────────────────

def member_name(m: dict | None) -> str:
    if not m:
        return "Someone not in the workspace"
    full = f"{m.get('first_name') or ''} {m.get('last_name') or ''}".strip()
    return full or m.get("display_name") or m.get("email") or "Unnamed member"


def projects() -> list[dict]:
    return db.query("SELECT id, identifier, name, description, archived_at FROM plane_projects "
                    "WHERE removed_at IS NULL ORDER BY name COLLATE NOCASE")


def members(include_bots: bool = False) -> list[dict]:
    rows = db.query("SELECT * FROM plane_members WHERE removed_at IS NULL" + ("" if include_bots else " AND is_bot = 0"))
    for m in rows:
        m["name"] = member_name(m)
    return sorted(rows, key=lambda m: m["name"].lower())


def counts() -> dict[str, int]:
    """How much the mirror holds (Settings, backups)."""
    with db.connect() as conn:
        return _count(conn)


def _count(conn) -> dict[str, int]:
    out = {}
    for table in MIRROR_TABLES:
        try:
            out[table.removeprefix("plane_")] = conn.execute(
                f"SELECT count(*) FROM {table} WHERE removed_at IS NULL").fetchone()[0]
        except Exception:  # noqa: BLE001 - a backup from before this module existed has no such table
            out[table.removeprefix("plane_")] = 0
    return out


def count_in(conn) -> dict[str, int]:
    """Module.count: what a database (perhaps a backup's) holds, to label it."""
    found = _count(conn)
    return {"Plane items": found["items"]} if found["items"] else {}


def describe(thing_id: str) -> dict | None:
    """How other modules show a link to a Plane item, member or project (refs "plane:<id>")."""
    item = db.one("SELECT i.name, i.sequence_id, p.identifier FROM plane_items i "
                  "LEFT JOIN plane_projects p ON p.id = i.project_id WHERE i.id = ?", (thing_id,))
    if item:
        key = f"{item['identifier']}-{item['sequence_id']}" if item["identifier"] else ""
        return {"title": f"{key} {item['name']}".strip(), "href": f"#/plane/team?item={thing_id}"}
    m = db.one("SELECT * FROM plane_members WHERE id = ?", (thing_id,))
    if m:
        return {"title": member_name(m), "href": f"#/plane/team?person={thing_id}"}
    p = db.one("SELECT name FROM plane_projects WHERE id = ?", (thing_id,))
    if p:
        return {"title": p["name"], "href": f"#/plane/links?project={thing_id}"}
    return None


def search(q: str, limit: int) -> list[dict]:
    """Plane items by their key ("SOFTWARE-5") or words in their name, for the sidebar search."""
    q = q.strip()
    if not q:
        return []
    esc = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = db.query(
        "SELECT i.id, i.name, i.sequence_id, p.identifier, p.name AS project FROM plane_items i "
        "JOIN plane_projects p ON p.id = i.project_id WHERE i.removed_at IS NULL "
        "AND (i.name LIKE ?1 ESCAPE '\\' OR (p.identifier || '-' || i.sequence_id) LIKE ?2 ESCAPE '\\') "
        "ORDER BY i.updated_at DESC LIMIT ?3",
        (f"%{esc}%", f"{esc}%", limit))
    return [{"id": r["id"], "title": f"{r['identifier']}-{r['sequence_id']} {r['name']}",
             "snippet": r["project"]} for r in rows]


def export() -> dict:
    return {name.removeprefix("plane_"): db.query(f"SELECT * FROM {name}") for name in (*MIRROR_TABLES, "plane_links")}
