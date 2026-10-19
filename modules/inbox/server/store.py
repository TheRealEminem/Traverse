"""The inbox's tables (inbox_*) and the queries on them. Only this module touches these tables.

A capture is something you brought in (a paste, a file, a meeting from Trailmix, later a capture from Claude). Its
proposals are the work items the AI found in it, each waiting for you to accept, edit or drop it.

    capture.status    new (being read) -> review (proposals wait for you) -> done (every one decided, or none found)
    proposal.status   proposed -> accepted | dropped (a dropped one can come back)
"""
from core.server import db

MIGRATIONS = [
    """
    CREATE TABLE inbox_captures (
        id            TEXT PRIMARY KEY,
        source        TEXT NOT NULL CHECK (source IN ('paste', 'file', 'claude', 'trailmix')),
        title         TEXT NOT NULL,
        title_auto    INTEGER NOT NULL DEFAULT 1,   -- 1 until a title is given: the AI's reading may name it
        raw_text      TEXT NOT NULL,
        status        TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'review', 'done')),
        origin_id     TEXT,                         -- where it came from, in its own app: a Trailmix meeting's uid
        origin_title  TEXT,                         -- …its name there (a file's name, a meeting's title)
        origin_url    TEXT,                         -- …where to open it
        origin_at     TEXT,                         -- …when it happened (a meeting's date), for reading "Friday"
        read_by       TEXT,                         -- which AI wrote the proposals ("Ollama · qwen2.5:7b")
        read_at       TEXT,
        created_at    TEXT NOT NULL,
        updated_at    TEXT NOT NULL
    );
    CREATE INDEX inbox_captures_status ON inbox_captures(status, created_at);
    CREATE TABLE inbox_proposals (
        id            TEXT PRIMARY KEY,
        capture_id    TEXT NOT NULL REFERENCES inbox_captures(id) ON DELETE CASCADE,
        sort          INTEGER NOT NULL,
        text          TEXT NOT NULL,
        assignee_name TEXT,
        due_on        TEXT,                         -- YYYY-MM-DD
        priority      INTEGER NOT NULL DEFAULT 0 CHECK (priority BETWEEN 0 AND 4),  -- Plane's scale, as tasks has it
        quote         TEXT NOT NULL DEFAULT '',     -- the sentence it came from
        status        TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'accepted', 'dropped')),
        decided_at    TEXT,
        created_at    TEXT NOT NULL,
        updated_at    TEXT NOT NULL
    );
    CREATE INDEX inbox_proposals_capture ON inbox_proposals(capture_id, sort);
    -- Every meeting Trailmix has offered, by its uid, kept even when its capture is deleted, so it never comes back.
    CREATE TABLE inbox_imports (
        id            TEXT PRIMARY KEY,
        source        TEXT NOT NULL,
        origin_id     TEXT NOT NULL,
        capture_id    TEXT,                         -- NULL when it had nothing to do
        created_at    TEXT NOT NULL,
        UNIQUE (source, origin_id)
    );
    CREATE VIRTUAL TABLE inbox_fts USING fts5(id UNINDEXED, title, raw_text, tokenize='porter unicode61');
    """,
]

SOURCES = ("paste", "file", "claude", "trailmix")
MAX_CHARS = 60_000           # what one reading takes in; a longer paste is refused with a sentence saying so
MAX_PROPOSALS = 40

CAPTURE_COLUMNS = ("id, source, title, title_auto, status, origin_id, origin_title, origin_url, origin_at, read_by, "
                   "read_at, created_at, updated_at")


def _reindex(conn, capture_id: str) -> None:
    conn.execute("DELETE FROM inbox_fts WHERE id = ?", (capture_id,))
    conn.execute("INSERT INTO inbox_fts (id, title, raw_text) SELECT id, title, raw_text FROM inbox_captures WHERE id = ?",
                 (capture_id,))


def insert_capture(conn, source: str, title: str, raw_text: str, *, title_auto: bool = True, origin_id=None,
                   origin_title=None, origin_url=None, origin_at=None) -> str:
    """Inside a caller's connection, so a capture can be made in one step with what records it (an import)."""
    capture_id, stamp = db.new_id(), db.now()
    conn.execute(
        "INSERT INTO inbox_captures (id, source, title, title_auto, raw_text, origin_id, origin_title, origin_url, "
        "origin_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (capture_id, source, title, int(title_auto), raw_text, origin_id, origin_title, origin_url, origin_at, stamp, stamp),
    )
    _reindex(conn, capture_id)
    return capture_id


def create(source: str, title: str, raw_text: str, **origin) -> str:
    with db.connect() as conn:
        return insert_capture(conn, source, title, raw_text, **origin)


def update(capture_id: str, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = db.now()
    with db.connect() as conn:
        conn.execute(f"UPDATE inbox_captures SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?",
                     (*fields.values(), capture_id))
        if "title" in fields:
            _reindex(conn, capture_id)


def get(capture_id: str) -> dict | None:
    return db.one("SELECT * FROM inbox_captures WHERE id = ?", (capture_id,))


def captures() -> list[dict]:
    """Every capture, newest first, with how many proposals wait and how many were accepted."""
    return db.query(
        f"SELECT {', '.join('c.' + c.strip() for c in CAPTURE_COLUMNS.split(','))}, "
        "(SELECT count(*) FROM inbox_proposals p WHERE p.capture_id = c.id AND p.status = 'proposed') AS waiting, "
        "(SELECT count(*) FROM inbox_proposals p WHERE p.capture_id = c.id AND p.status = 'accepted') AS accepted "
        "FROM inbox_captures c ORDER BY c.created_at DESC")


def waiting_count() -> int:
    return db.one("SELECT count(*) AS n FROM inbox_captures WHERE status = 'review'")["n"]


def delete(capture_id: str) -> None:
    with db.connect() as conn:
        conn.execute("DELETE FROM inbox_captures WHERE id = ?", (capture_id,))
        conn.execute("DELETE FROM inbox_fts WHERE id = ?", (capture_id,))
        conn.execute("UPDATE inbox_imports SET capture_id = NULL WHERE capture_id = ?", (capture_id,))


# ── Proposals ─────────────────────────────────────────────────────────

def proposals(capture_id: str) -> list[dict]:
    return db.query("SELECT * FROM inbox_proposals WHERE capture_id = ? ORDER BY sort", (capture_id,))


def proposal(proposal_id: str) -> dict | None:
    return db.one("SELECT * FROM inbox_proposals WHERE id = ?", (proposal_id,))


def replace_proposed(capture_id: str, found: list[dict]) -> int:
    """A new reading: the proposals still waiting are replaced; accepted and dropped ones stay, and anything found
    again that matches one of them isn't proposed twice. Returns how many now wait."""
    with db.connect() as conn:
        conn.execute("DELETE FROM inbox_proposals WHERE capture_id = ? AND status = 'proposed'", (capture_id,))
        decided = {r[0].casefold() for r in conn.execute(
            "SELECT text FROM inbox_proposals WHERE capture_id = ?", (capture_id,))}
        sort = conn.execute("SELECT coalesce(max(sort), -1) FROM inbox_proposals WHERE capture_id = ?",
                            (capture_id,)).fetchone()[0]
        added = 0
        for p in found:
            if p["text"].casefold() in decided:
                continue
            decided.add(p["text"].casefold())
            sort += 1
            added += 1
            stamp = db.now()
            conn.execute(
                "INSERT INTO inbox_proposals (id, capture_id, sort, text, assignee_name, due_on, priority, quote, "
                "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (db.new_id(), capture_id, sort, p["text"], p.get("assignee_name"), p.get("due_on"),
                 p.get("priority", 0), p.get("quote") or "", stamp, stamp),
            )
    return added


def update_proposal(proposal_id: str, **fields) -> None:
    fields["updated_at"] = db.now()
    db.execute(f"UPDATE inbox_proposals SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?",
               (*fields.values(), proposal_id))


def settle(capture_id: str) -> str:
    """The capture's status from its proposals: review while any wait, done once none do. Returns it."""
    row = get(capture_id)
    if not row or row["status"] == "new":
        return row["status"] if row else ""
    left = db.one("SELECT count(*) AS n FROM inbox_proposals WHERE capture_id = ? AND status = 'proposed'",
                  (capture_id,))["n"]
    status = "review" if left else "done"
    if status != row["status"]:
        update(capture_id, status=status)
    return status


# ── Imports (Trailmix) ────────────────────────────────────────────────

def imported(source: str, origin_id: str) -> bool:
    return db.one("SELECT 1 AS x FROM inbox_imports WHERE source = ? AND origin_id = ?", (source, origin_id)) is not None


def imports_count(source: str) -> int:
    return db.one("SELECT count(*) AS n FROM inbox_imports WHERE source = ? AND capture_id IS NOT NULL", (source,))["n"]


def record_import(source: str, origin_id: str, capture: dict | None) -> str | None:
    """Remembers that a meeting was offered and, when it had work in it, makes its capture, in one step (so running
    twice can never make two). Returns the new capture's id, or None (nothing to do, or already brought in)."""
    with db.connect() as conn:
        if conn.execute("SELECT 1 FROM inbox_imports WHERE source = ? AND origin_id = ?", (source, origin_id)).fetchone():
            return None
        capture_id = insert_capture(conn, **capture) if capture else None
        conn.execute("INSERT INTO inbox_imports (id, source, origin_id, capture_id, created_at) VALUES (?, ?, ?, ?, ?)",
                     (db.new_id(), source, origin_id, capture_id, db.now()))
    return capture_id


# ── What the host asks for ────────────────────────────────────────────

def describe(capture_id: str) -> dict | None:
    """How other modules show a link to a capture (a task's "from")."""
    row = db.one("SELECT title FROM inbox_captures WHERE id = ?", (capture_id,))
    return {"title": row["title"], "href": f"#/inbox/{capture_id}"} if row else None


def search(q: str, limit: int) -> list[dict]:
    words = " ".join(f'"{w}"*' for w in q.replace('"', " ").split())
    if not words:
        return []
    rows = db.query(
        "SELECT id, title, snippet(inbox_fts, 2, '', '', '…', 10) AS snippet FROM inbox_fts WHERE inbox_fts MATCH ? "
        "ORDER BY rank LIMIT ?", (words, limit))
    return [{"id": r["id"], "title": r["title"], "snippet": r["snippet"]} for r in rows]


def export() -> dict:
    return {
        "captures": db.query("SELECT * FROM inbox_captures ORDER BY created_at"),
        "proposals": db.query("SELECT * FROM inbox_proposals ORDER BY capture_id, sort"),
        "imports": db.query("SELECT * FROM inbox_imports ORDER BY created_at"),
    }


def count(conn) -> dict:
    """What a database holds (a backup's), to label it."""
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if "inbox_captures" not in tables:
        return {}
    return {"captures": conn.execute("SELECT count(*) FROM inbox_captures").fetchone()[0]}
