"""The calendar module's tables: the calendars it reads (calendar_sources) and a short-lived copy of their events
(calendar_events). Only this module touches them.

A source is one of
    ical  a calendar's private iCal address (Google's "Secret address in iCal format", Outlook's published ICS…),
          read by the server every few minutes (feeds.py). The address is a secret: anyone who has it can read the
          calendar, so it's never sent back to the page, only its host ("calendar.google.com").
    mac   this Mac's Calendar, every account the Calendar app has. The server can't read it: the Mac app's window does,
          after macOS has asked you once, and sends the events here (mac.py). At most one.

Events are kept for the window that matters to a day: from today's midnight to a week after tomorrow (WINDOW_DAYS),
and each read of a source replaces all of its events. Ones that have ended before today are forgotten.
"""
import hashlib
from datetime import date, datetime, time, timedelta
from urllib.parse import urlparse

from core.server import db

KINDS = ("ical", "mac")
WINDOW_DAYS = 8                  # today and the next seven
MOST_EVENTS = 500                # per source

MIGRATIONS = [
    """
    CREATE TABLE calendar_sources (
        id          TEXT PRIMARY KEY,
        kind        TEXT NOT NULL,                -- 'ical' or 'mac' (above)
        name        TEXT NOT NULL,
        url         TEXT,                         -- an ical source's address: a secret, never sent to the page
        enabled     INTEGER NOT NULL DEFAULT 1,
        read_at     TEXT,                         -- the last time its events came through
        tried_at    TEXT,                         -- the last attempt
        error       TEXT,                         -- why the last attempt failed; NULL when it worked
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    );
    CREATE TABLE calendar_events (
        id          TEXT PRIMARY KEY,             -- the same for the same event (and the same time of a repeat)
        source_id   TEXT NOT NULL REFERENCES calendar_sources(id) ON DELETE CASCADE,
        title       TEXT NOT NULL,
        starts      TEXT NOT NULL,                -- this computer's time, "2026-10-21T10:00"; a day for all-day ones
        ends        TEXT NOT NULL,                -- (all-day: the day after the last one, as calendars say it)
        all_day     INTEGER NOT NULL DEFAULT 0,
        free        INTEGER NOT NULL DEFAULT 0,   -- "Show as: Free": it doesn't take your time
        calendar    TEXT NOT NULL DEFAULT ''      -- the calendar's own name, when the source has several
    );
    CREATE INDEX calendar_events_starts ON calendar_events(starts);
    """,
]


def today() -> date:
    """This computer's calendar day (tests replace it)."""
    return date.today()


def window(on: date | None = None) -> tuple[datetime, datetime]:
    """The span events are kept for: today's midnight to WINDOW_DAYS later, in this computer's time."""
    start = datetime.combine(on or today(), time())
    return start, start + timedelta(days=WINDOW_DAYS)


# ── Sources ───────────────────────────────────────────────────────────

def sources() -> list[dict]:
    return db.query("SELECT * FROM calendar_sources ORDER BY kind = 'mac', created_at")


def source(source_id: str) -> dict | None:
    return db.one("SELECT * FROM calendar_sources WHERE id = ?", (source_id,))


def mac_source() -> dict | None:
    return db.one("SELECT * FROM calendar_sources WHERE kind = 'mac'")


def address(value) -> str:
    """A feed's address, checked: https (webcal:// is how calendars hand out https feeds), or http on this computer."""
    text = value.strip() if isinstance(value, str) else ""
    if text.lower().startswith("webcal://"):
        text = "https://" + text[len("webcal://"):]
    found = urlparse(text)
    local = found.hostname in ("localhost", "127.0.0.1", "::1")
    if not found.hostname or not (found.scheme == "https" or (found.scheme == "http" and local)) or len(text) > 2000:
        raise ValueError("Paste the calendar's private address: it starts with https:// or webcal://")
    return text


def host_of(url: str | None) -> str | None:
    return urlparse(url).hostname if url else None


def name_of(value, fallback: str) -> str:
    text = " ".join(value.split())[:80] if isinstance(value, str) else ""
    return text or fallback


def add(kind: str, name=None, url=None) -> dict:
    if kind not in KINDS:
        raise ValueError("A calendar is an iCal address or this Mac's Calendar")
    if kind == "mac" and mac_source():
        raise ValueError("This Mac's Calendar is here already")
    stamp, source_id = db.now(), db.new_id()
    if kind == "ical":
        url = address(url)
        name = name_of(name, host_of(url) or "Calendar")
    else:
        url, name = None, name_of(name, "This Mac’s Calendar")
    db.execute("INSERT INTO calendar_sources (id, kind, name, url, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
               (source_id, kind, name, url, stamp, stamp))
    return source(source_id)


def change(source_id: str, changes: dict) -> dict:
    """{"name", "enabled", "url"} (an ical source's new address, which clears its error)."""
    row = source(source_id)
    if row is None:
        raise KeyError(source_id)
    unknown = set(changes) - {"name", "enabled", "url"}
    if unknown:
        raise ValueError(f"Can't change {', '.join(sorted(unknown))}")
    cols: dict = {}
    if "name" in changes:
        cols["name"] = name_of(changes["name"], row["name"])
    if "enabled" in changes:
        if not isinstance(changes["enabled"], bool):
            raise ValueError("enabled is true or false")
        cols["enabled"] = int(changes["enabled"])
    if "url" in changes:
        if row["kind"] != "ical":
            raise ValueError("This Mac's Calendar has no address")
        cols.update(url=address(changes["url"]), error=None)
    if cols:
        cols["updated_at"] = db.now()
        db.execute(f"UPDATE calendar_sources SET {', '.join(f'{k} = ?' for k in cols)} WHERE id = ?",
                   (*cols.values(), source_id))
    return source(source_id)


def remove(source_id: str) -> bool:
    return db.execute("DELETE FROM calendar_sources WHERE id = ?", (source_id,)) > 0   # its events go with it


def tried(source_id: str, error: str | None) -> None:
    stamp = db.now()
    if error is None:
        db.execute("UPDATE calendar_sources SET read_at = ?, tried_at = ?, error = NULL WHERE id = ?", (stamp, stamp, source_id))
    else:
        db.execute("UPDATE calendar_sources SET tried_at = ?, error = ? WHERE id = ?", (stamp, error[:300], source_id))


# ── Events ────────────────────────────────────────────────────────────

def event_id(source_id: str, uid: str, starts: str) -> str:
    """The same id for the same event at the same time, read after read, so its ref stays put. A hash of where it
    came from, not a number, so databases still merge."""
    return hashlib.sha256(f"{source_id}\n{uid}\n{starts}".encode()).hexdigest()[:32]


def replace(source_id: str, events: list[dict]) -> int:
    """A source's events, all at once: [{"uid", "title", "starts", "ends", "all_day", "free", "calendar"}], already in
    this computer's time and inside the window. Returns how many are kept."""
    rows = {}
    for e in events[:MOST_EVENTS]:
        found = event_id(source_id, e["uid"], e["starts"])
        rows[found] = (found, source_id, e["title"], e["starts"], e["ends"], int(e["all_day"]), int(e["free"]),
                       e.get("calendar") or "")
    with db.connect() as conn:
        conn.execute("DELETE FROM calendar_events WHERE source_id = ?", (source_id,))
        conn.executemany("INSERT INTO calendar_events (id, source_id, title, starts, ends, all_day, free, calendar) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", list(rows.values()))
    return len(rows)


def forget_past() -> int:
    """Events that ended before today: they aren't kept beyond their day."""
    return db.execute("DELETE FROM calendar_events WHERE ends <= ?", (today().isoformat(),))


def events_between(start: datetime, end: datetime) -> list[dict]:
    """Enabled sources' events that touch [start, end), in order: all-day ones first on their day."""
    rows = db.query(
        "SELECT e.*, s.name AS source_name FROM calendar_events e JOIN calendar_sources s ON s.id = e.source_id "
        "WHERE s.enabled = 1 AND e.starts < ? AND e.ends > ? ORDER BY substr(e.starts, 1, 10), e.all_day DESC, e.starts",
        (end.isoformat(timespec="minutes"), start.isoformat(timespec="minutes")))
    for r in rows:
        r["all_day"], r["free"] = bool(r["all_day"]), bool(r["free"])
    return rows


def counts() -> dict[str, int]:
    """source id -> how many of its events there are, from today on."""
    return {r["source_id"]: r["n"] for r in db.query("SELECT source_id, count(*) AS n FROM calendar_events GROUP BY source_id")}


def describe(item_id: str) -> dict | None:
    found = db.one("SELECT title FROM calendar_events WHERE id = ?", (item_id,))
    if found:
        return {"title": found["title"], "href": None}
    found = source(item_id)
    return {"title": found["name"], "href": "#/settings"} if found else None


def export() -> dict:
    """Which calendars it reads; not their addresses (secrets) or events (the calendars' own)."""
    return {"sources": [{k: r[k] for k in ("id", "kind", "name", "enabled", "created_at")} for r in sources()]}


def count(conn) -> dict:
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "calendar_sources" not in tables:
        return {}
    n = conn.execute("SELECT count(*) FROM calendar_sources").fetchone()[0]
    return {"calendars": n} if n else {}
