"""Plane members as people for the host's people directory (Module.people, core/server/people.py).

Each member comes back as "plane:<member id>", except the one who is you (Settings → Plane, or the API key's owner),
who comes back with is_self, so the directory stores you as "core:me" like every other module and app does.
"""
from core.server import db

from . import store, team

_MAX = 25


def find(q: str, limit: int) -> list[dict]:
    """(q, limit) -> [{id, name, email, detail, is_self}]: members whose name, handle or email match. Names that start
    with q first, then names with a word that does, then the rest. An empty q is the whole team, so a picker can offer
    them before anything is typed."""
    q = q.strip()
    limit = max(1, min(int(limit or 8), _MAX))
    me = team.me_id()
    esc = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    full = "(first_name || ' ' || last_name)"
    rows = db.query(
        "SELECT * FROM plane_members WHERE removed_at IS NULL AND is_bot = 0 AND is_active = 1 "
        f"AND ({full} LIKE ?1 ESCAPE '\\' OR display_name LIKE ?1 ESCAPE '\\' OR email LIKE ?1 ESCAPE '\\') "
        f"ORDER BY CASE WHEN {full} LIKE ?2 ESCAPE '\\' OR display_name LIKE ?2 ESCAPE '\\' THEN 0 "
        f"WHEN {full} LIKE ?3 ESCAPE '\\' THEN 1 ELSE 2 END, {full} COLLATE NOCASE LIMIT ?4",
        (f"%{esc}%", f"{esc}%", f"% {esc}%", limit))
    return [_person(r, me) for r in rows]


def _person(m: dict, me: str | None) -> dict:
    handle = m.get("display_name")
    return {"id": m["id"], "name": store.member_name(m), "email": m.get("email"),
            "detail": f"Plane · @{handle}" if handle else "Plane", "is_self": m["id"] == me}
