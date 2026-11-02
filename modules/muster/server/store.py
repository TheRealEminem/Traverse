"""Muster's one table, muster_days: a row per day you mustered (or that picks were rolled to). Only this module
touches it, and it holds nothing of other modules' but refs.

A day's picks are a JSON list in your order. A pick is
    {"id", "ref", "title", "href", "minutes", "done", "first_day", "rolled_to", "let_go", "added_at"}
    ref        what it is elsewhere ("tasks:<id>", "plane:<item id>"); None for a line you typed
    title      and href: as they were when picked, for when its module can't say any more
    minutes    your estimate for it today; None when you haven't given one
    done       ticked here (it also shows done when its own module says so: describe's "done")
    first_day  the day it was first picked, so a pick carried over says how long it's been around
    rolled_to  on the day it left: the day it was carried to; let_go: wrapped up without it, and not carried

The AI's part of a day (chunk 15b): the morning summary and who wrote it (summary.py), and the suggested plan (plan,
JSON; suggest.py).
"""
import json
import re

from core.server import db

MIGRATIONS = [
    """
    CREATE TABLE muster_days (
        id             TEXT PRIMARY KEY,
        day            TEXT NOT NULL UNIQUE,       -- YYYY-MM-DD, this computer's calendar day
        picks          TEXT NOT NULL DEFAULT '[]', -- JSON: the day's plan, in your order (above)
        intention      TEXT NOT NULL DEFAULT '',   -- a line for the day
        tomorrow_note  TEXT NOT NULL DEFAULT '',   -- the wrap-up's line for tomorrow-you
        since          TEXT,                       -- "since your last Muster": the moment its "what moved" starts at
        opened_at      TEXT,                       -- the day's first look at Muster
        seen_at        TEXT,                       -- …and its latest
        kicked_off_at  TEXT,
        wrapped_up_at  TEXT,
        summary        TEXT,                       -- the morning summary (chunk 15b)
        summary_by     TEXT,                       -- …and which AI wrote it
        created_at     TEXT NOT NULL,
        updated_at     TEXT NOT NULL
    );
    """,
    # 15b: the morning summary's moment and how much it covered, and the suggested plan.
    """
    ALTER TABLE muster_days ADD COLUMN summary_at TEXT;          -- when the summary was written
    ALTER TABLE muster_days ADD COLUMN summary_moved INTEGER;    -- …and how many lines of "what moved" it covered
    ALTER TABLE muster_days ADD COLUMN plan TEXT;                -- JSON: the suggested plan (suggest.py), or NULL
    """,
]

MAX_MINUTES = 24 * 60
_REF = re.compile(r"^[a-z][a-z0-9_-]*:[A-Za-z0-9_.-]+$")
COLUMNS = ("picks", "intention", "tomorrow_note", "since", "opened_at", "seen_at", "kicked_off_at", "wrapped_up_at",
           "summary", "summary_by", "summary_at", "summary_moved", "plan")
JSON_COLUMNS = ("plan",)


def _read(found: dict) -> dict:
    found["picks"] = json.loads(found["picks"])
    for col in JSON_COLUMNS:
        found[col] = json.loads(found[col]) if found.get(col) else None
    return found


def row(day: str) -> dict | None:
    found = db.one("SELECT * FROM muster_days WHERE day = ?", (day,))
    return _read(found) if found else None


def make(day: str) -> dict:
    """The day's row, made empty if there isn't one yet."""
    stamp = db.now()
    db.execute("INSERT INTO muster_days (id, day, created_at, updated_at) VALUES (?, ?, ?, ?) "
               "ON CONFLICT(day) DO NOTHING", (db.new_id(), day, stamp, stamp))
    return row(day)


def save(day: str, conn=None, **cols) -> None:
    unknown = set(cols) - set(COLUMNS)
    if unknown:
        raise ValueError(f"Can't change {', '.join(sorted(unknown))}")
    if "picks" in cols:
        cols["picks"] = json.dumps(cols["picks"])
    for col in JSON_COLUMNS:
        if col in cols and cols[col] is not None:
            cols[col] = json.dumps(cols[col])
    cols["updated_at"] = db.now()
    sql = f"UPDATE muster_days SET {', '.join(f'{k} = ?' for k in cols)} WHERE day = ?"
    if conn is not None:
        conn.execute(sql, (*cols.values(), day))
    else:
        db.execute(sql, (*cols.values(), day))


def earlier(day: str, limit: int = 60) -> list[dict]:
    """The days before `day` that have a row, newest first."""
    return [_read(r) for r in db.query("SELECT * FROM muster_days WHERE day < ? ORDER BY day DESC LIMIT ?", (day, limit))]



def minutes(value) -> int | None:
    """An estimate: a whole number of minutes up to a day's worth, or None."""
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_MINUTES:
        raise ValueError("Minutes are a whole number, up to a day's worth")
    return value


def is_ref(value) -> bool:
    return isinstance(value, str) and bool(_REF.match(value))


def describe(row_id: str) -> dict | None:
    found = db.one("SELECT day FROM muster_days WHERE id = ?", (row_id,))
    return {"title": f"Muster for {found['day']}", "href": "#/muster"} if found else None


def export() -> dict:
    return {"days": [_read(r) for r in db.query("SELECT * FROM muster_days ORDER BY day")]}


def count(conn) -> dict:
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "muster_days" not in tables:
        return {}
    n = conn.execute("SELECT count(*) FROM muster_days WHERE opened_at IS NOT NULL").fetchone()[0]
    return {"days mustered": n} if n else {}
