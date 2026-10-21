"""The inbox's part of the day's briefing (core/server/briefing.py, Module.brief): captures whose proposals wait for
you, and the meetings Trailmix has brought in (today's, and those since a moment). Until the calendar arrives
(Traverse PLAN.md chunk 15b), Trailmix's meetings here are the only meetings the briefing knows.
"""
from datetime import date, datetime

from core.server import briefing, db


def _local_day(moment: str | None) -> date | None:
    """A meeting's day on this computer. Trailmix may send a moment with or without its zone (then it's local)."""
    if not moment:
        return None
    try:
        when = datetime.fromisoformat(moment.replace("Z", "+00:00"))
    except ValueError:
        return None
    return when.astimezone().date() if when.tzinfo else when.date()


def _meeting(row: dict) -> dict:
    n = row["items"]
    return {"id": row["id"], "title": row["origin_title"] or row["title"], "href": f"#/inbox/{row['id']}",
            "url": row["origin_url"], "what": f"Meeting · {n} action {'item' if n == 1 else 'items'}",
            "kind": "meeting", "tone": "neutral", "when": row["origin_at"]}


def brief(since: str, today: date) -> dict:
    waiting = []
    for row in db.query(
            "SELECT c.id, c.title, c.created_at, (SELECT count(*) FROM inbox_proposals p WHERE p.capture_id = c.id "
            "AND p.status = 'proposed') AS n FROM inbox_captures c WHERE c.status = 'review' ORDER BY c.created_at"):
        if row["n"]:
            waiting.append({"id": row["id"], "title": row["title"], "href": f"#/inbox/{row['id']}",
                            "what": f"{row['n']} {'proposal' if row['n'] == 1 else 'proposals'} to review",
                            "kind": "proposals", "tone": "sun", "when": row["created_at"]})

    since_day = briefing.local_day(since)
    on_today, moved = [], []
    for row in db.query(
            "SELECT c.*, (SELECT count(*) FROM inbox_proposals p WHERE p.capture_id = c.id) AS items "
            "FROM inbox_captures c WHERE c.source = 'trailmix' ORDER BY c.origin_at"):
        day = _local_day(row["origin_at"]) or _local_day(row["created_at"])
        if day == today:
            on_today.append(_meeting(row))
        elif day and since_day <= day < today:
            moved.append(_meeting(row))
    return {"waiting": waiting, "today": on_today, "moved": moved}
