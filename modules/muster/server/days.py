"""A day in Muster: opening it, its plan (picks), kicking off and wrapping up, and what the page shows.

- **Since your last Muster.** The first look at Muster on a day fixes where that day's "what moved" starts: the last
  time you looked at it on an earlier day (or a day ago, the first time). It stays put all day, so what moved later
  on still shows, and tomorrow starts from your last look today.
- **Picks carry over.** On a day's first look, picks from earlier days that aren't done, carried or let go come
  along, in their order, after whatever is already there (once each). Wrapping up does the same for tomorrow, now,
  except for the picks you let go. A pick its own module says is done, or that's gone, stays behind.
- **Ticking a pick** that's work somewhere else (a task) says so through the shared contract work.marked_done, and
  that module marks it done. Muster never writes another module's tables, and nothing it does reaches Plane.

Everything else the page shows comes from the host: the briefing (core/server/briefing.py) and describe.
"""
import uuid
from datetime import date, timedelta

from core.server import briefing, contracts, db, events, module, settings

from . import store

MAX_MINUTES = 24 * 60


def today() -> date:
    """This computer's calendar day (tests replace it)."""
    return date.today()


def day_of(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        raise ValueError(f"{value!r} isn't a day like 2026-10-21") from None


def _next(day: str) -> str:
    return (date.fromisoformat(day) + timedelta(days=1)).isoformat()


def _changed(day: str) -> None:
    events.publish("muster.changed", {"day": day})


def _described(pick: dict) -> dict | None:
    return module.describe(pick["ref"]) if pick.get("ref") else None


def _open(pick: dict) -> bool:
    """Still to do: not ticked, carried or let go here, and not done or gone where it lives."""
    if pick["done"] or pick.get("rolled_to") or pick.get("let_go"):
        return False
    if pick.get("ref"):
        found = _described(pick)
        return bool(found) and not found.get("done")
    return True


# ── Opening a day ─────────────────────────────────────────────────────

def _since_for(day: str) -> str:
    """Where a day's "what moved" starts: your last look at Muster before it, or a day ago."""
    last = db.one("SELECT max(seen_at) AS at FROM muster_days WHERE day < ?", (day,))["at"]
    return last or briefing.day_before()


def carry_into(target: str) -> int:
    """Brings the open picks of every earlier day (the last 60 with a row) to `target`, after its own. Returns how
    many came; a pick whose ref is in the target's plan already only leaves its old day."""
    row = store.make(target)
    picks = row["picks"]
    have = {p["ref"] for p in picks if p.get("ref") and not p.get("let_go")}
    came = 0
    for old in reversed(store.earlier(target)):
        moved = False
        for p in old["picks"]:
            if not _open(p):
                continue
            p["rolled_to"], moved = target, True
            if p.get("ref") and p["ref"] in have:
                continue
            picks.append({**p, "rolled_to": None, "done": False, "first_day": p.get("first_day") or old["day"]})
            have.add(p.get("ref"))
            came += 1
        if moved:
            store.save(old["day"], picks=old["picks"])
    if came:
        store.save(target, picks=picks)
    return came


def ensure(day: str) -> dict:
    """The day's row, made if needed. Until the day's first look, earlier days' open picks are carried into it."""
    row = store.make(day)
    if not row["opened_at"] and carry_into(day):
        row = store.row(day)
    return row


def open_day(day: str) -> dict:
    """You're looking at Muster on this day: the first look fixes "since"; every look is the latest one."""
    row = ensure(day)
    stamp = db.now()
    if not row["opened_at"]:
        store.save(day, since=_since_for(day), opened_at=stamp, seen_at=stamp)
    else:
        store.save(day, seen_at=stamp)
    _changed(day)
    return view(day)


def start_page() -> str | None:
    """The first page of the day (the web registry's start): Muster, until you've looked at it today."""
    if not settings.section("muster").get("open_first"):
        return None
    row = store.row(today().isoformat())
    return None if row and row["opened_at"] else "muster"


# ── The plan ──────────────────────────────────────────────────────────

def _minutes(value) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_MINUTES:
        raise ValueError("Minutes are a whole number, up to a day's worth")
    return value


def _find(picks: list[dict], pick_id: str) -> dict:
    for p in picks:
        if p["id"] == pick_id:
            return p
    raise KeyError(pick_id)


def add_pick(day: str, *, ref: str | None = None, title: str | None = None, href: str | None = None,
             minutes=None) -> dict:
    """Puts something in the day's plan, last: a ref (its module names it) or a line of your own."""
    row = ensure(day)
    title = (title or "").strip() if isinstance(title, str) else ""
    if ref is not None:
        if not store.is_ref(ref):
            raise ValueError("A pick is a reference like tasks:<id>, or a line of text")
        found = module.describe(ref)
        if not found and not title:
            raise ValueError("That isn't here any more")
        title = (found or {}).get("title") or title
        href = (found or {}).get("href") or href
        if any(p.get("ref") == ref and not p.get("rolled_to") and not p.get("let_go") for p in row["picks"]):
            raise ValueError("That's in the plan already")
    elif not title:
        raise ValueError("A pick needs some text")
    pick = {"id": uuid.uuid4().hex[:12], "ref": ref, "title": title[:300], "href": href if isinstance(href, str) else None,
            "minutes": _minutes(minutes), "done": False, "first_day": day, "rolled_to": None, "let_go": False,
            "added_at": db.now()}
    store.save(day, picks=[*row["picks"], pick])
    _changed(day)
    return pick


def update_pick(day: str, pick_id: str, changes: dict) -> dict:
    """minutes, done (said to the pick's own module too) or title (a line of your own only)."""
    unknown = set(changes) - {"minutes", "done", "title"}
    if unknown:
        raise ValueError(f"Can't change {', '.join(sorted(unknown))}")
    row = ensure(day)
    pick = _find(row["picks"], pick_id)
    if pick.get("rolled_to"):
        raise ValueError("That went on to another day")
    if "minutes" in changes:
        pick["minutes"] = _minutes(changes["minutes"])
    if "title" in changes:
        if pick.get("ref"):
            raise ValueError("Its own module names it; rename it there")
        text = (changes["title"] or "").strip() if isinstance(changes["title"], str) else ""
        if not text:
            raise ValueError("A pick needs some text")
        pick["title"] = text[:300]
    done = changes.get("done")
    if done is not None:
        if not isinstance(done, bool):
            raise ValueError("done is true or false")
        pick["done"] = done
        if done:
            pick["let_go"] = False
    store.save(day, picks=row["picks"])
    if done is not None and pick.get("ref"):
        events.publish(contracts.WORK_MARKED_DONE, {"ref": pick["ref"], "done": done})
    _changed(day)
    return pick


def move_pick(day: str, pick_id: str, after_id: str | None) -> list[dict]:
    """Puts a pick right after another (first, when after_id is None)."""
    row = ensure(day)
    picks = row["picks"]
    pick = _find(picks, pick_id)
    if after_id == pick_id:
        raise ValueError("A pick can't go after itself")
    rest = [p for p in picks if p["id"] != pick_id]
    if after_id is None:
        at = 0
    else:
        _find(rest, after_id)
        at = next(i for i, p in enumerate(rest) if p["id"] == after_id) + 1
    rest.insert(at, pick)
    store.save(day, picks=rest)
    _changed(day)
    return rest


def remove_pick(day: str, pick_id: str) -> None:
    row = ensure(day)
    _find(row["picks"], pick_id)
    store.save(day, picks=[p for p in row["picks"] if p["id"] != pick_id])
    _changed(day)


# ── Kick-off and wrap-up ──────────────────────────────────────────────

def update_day(day: str, changes: dict) -> None:
    unknown = set(changes) - {"intention", "tomorrow_note"}
    if unknown:
        raise ValueError(f"Can't change {', '.join(sorted(unknown))}")
    ensure(day)
    cols = {}
    for key, value in changes.items():
        if not isinstance(value, str):
            raise ValueError("That should be text")
        cols[key] = value.strip()[:500]
    store.save(day, **cols)
    _changed(day)


def kick_off(day: str) -> None:
    row = ensure(day)
    if not row["kicked_off_at"]:
        store.save(day, kicked_off_at=db.now())
    _changed(day)


def wrap_up(day: str, let_go: list[str] | None = None, note: str | None = None) -> dict:
    """The end of the day: picks you let go stay behind, every other open one goes to tomorrow now, and your line
    for tomorrow-you is kept. Wrapping up again takes anything added since along too."""
    row = ensure(day)
    let_go = set(let_go or [])
    for p in row["picks"]:
        if p["id"] in let_go and not p["done"] and not p.get("rolled_to"):
            p["let_go"] = True
    stamp = db.now()
    cols = {"picks": row["picks"], "wrapped_up_at": stamp, "seen_at": stamp}
    if note is not None:
        if not isinstance(note, str):
            raise ValueError("The note for tomorrow should be text")
        cols["tomorrow_note"] = note.strip()[:500]
    store.save(day, **cols)
    tomorrow = _next(day)
    carry_into(tomorrow)
    picks = store.row(day)["picks"]
    _changed(day)
    return {"to": tomorrow, "done": sum(1 for p in picks if _shown_done(p)),
            "rolled": sum(1 for p in picks if p.get("rolled_to") == tomorrow),
            "let_go": sum(1 for p in picks if p.get("let_go"))}


# ── What the page shows ───────────────────────────────────────────────

def _shown_done(pick: dict) -> bool:
    return bool(pick["done"] or (_described(pick) or {}).get("done"))


def _shown(pick: dict) -> dict:
    found = _described(pick)
    there = bool(found and found.get("done"))
    return {**pick, "title": (found or {}).get("title") or pick["title"], "href": (found or {}).get("href") or pick["href"],
            "done": bool(pick["done"] or there), "done_there": there and not pick["done"],
            "gone": bool(pick.get("ref")) and found is None,
            "module": pick["ref"].split(":", 1)[0] if pick.get("ref") else None}


def view(day: str) -> dict:
    """Everything #/muster shows for a day: the day's row, its picks as their modules name them now, the note from
    your last wrap-up, working hours, and the briefing from the day's "since"."""
    row = ensure(day)
    since = row["since"] or _since_for(day)
    before = store.earlier(day, limit=1)
    last = before[0] if before else None
    cfg = settings.section("muster")
    return {
        "day": day, "today": today().isoformat(), "since": since, "first": not before,
        "opened_at": row["opened_at"], "kicked_off_at": row["kicked_off_at"], "wrapped_up_at": row["wrapped_up_at"],
        "intention": row["intention"], "tomorrow_note": row["tomorrow_note"],
        "note": {"day": last["day"], "text": last["tomorrow_note"]} if last and last["tomorrow_note"] else None,
        "picks": [_shown(p) for p in row["picks"]],
        "hours": {"start": cfg.get("day_starts") or "09:00", "end": cfg.get("day_ends") or "17:00"},
        "briefing": briefing.gather(since, date.fromisoformat(day)),
    }
