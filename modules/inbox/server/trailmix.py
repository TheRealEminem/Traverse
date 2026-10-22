"""Meetings from Trailmix: a recurring job that reads Trailmix's local API and puts each summarized meeting's open
action items in the inbox, as a capture linked to that meeting, to be read and reviewed like any other.

Trailmix is its own app (PLAN.md §6b F7), so this only ever reads it, with GET requests: the list of meetings, then
each finished one, because only a meeting's own page has its uid, which is what a meeting is known by here. A
meeting is offered once: its uid is remembered even when it had nothing to do or you delete its capture. Only the
last two weeks are looked at, so turning this on doesn't read years of meetings.

It does nothing while the setting is off (the default) or Trailmix isn't running.
"""
import logging
import threading
from datetime import datetime, timedelta, timezone

import httpx

from core.server import db, events, jobs, links, lockdown, settings
from core.server.jobs import Job

from . import store

log = logging.getLogger("inbox.trailmix")

EVERY_SECONDS = 300
LOOKBACK_DAYS = 14
TIMEOUT = httpx.Timeout(10, connect=2)
_transport: httpx.BaseTransport | None = None     # tests put a fake Trailmix here

# What the last look found, for Settings ("Trailmix is open · checked 2 minutes ago"). Only shown, never relied on:
# after a restart the next look, a few seconds later, says it again.
_last: dict = {}
_last_lock = threading.Lock()


def every() -> int:
    """How often the host runs the check: every five minutes while the setting is on, never while it's off."""
    return EVERY_SECONDS if settings.section("inbox")["trailmix"] else 0


def last() -> dict:
    with _last_lock:
        return dict(_last)


def _note(**found) -> None:
    with _last_lock:
        _last.clear()
        _last.update(found, at=db.now())
    events.publish("inbox.trailmix.checked", {})


def _client(base: str) -> httpx.Client:
    return httpx.Client(base_url=base, timeout=TIMEOUT, transport=_transport, follow_redirects=False)


def _when(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
    except ValueError:
        return None


def meeting_text(meeting: dict, items: list[str]) -> str:
    when = _when(meeting.get("created_at"))
    day = f" · {when.astimezone():%A %-d %B %Y}" if when else ""
    return f"Meeting: {meeting.get('title') or 'Untitled meeting'}{day}\n\nAction items:\n" + "\n".join(f"- {i}" for i in items)


def check(job: Job) -> None:
    """The inbox/trailmix job. Safe to run twice: a meeting already seen is skipped, and a meeting and its capture
    are recorded in one step."""
    cfg = settings.section("inbox")
    if not cfg["trailmix"]:
        return
    base = cfg["trailmix_url"].rstrip("/")
    lockdown.check(base)                    # Trailmix runs on this Mac; one elsewhere waits while Lockdown is on
    try:
        with _client(base) as client:
            job.stage("Looking for new meetings")
            listed = client.get("/api/meetings")
            if listed.status_code in (401, 403):
                return _note(reachable=True, error="Trailmix asks for a sign-in, so Traverse can't read its meetings.")
            listed.raise_for_status()
            cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
            recent = [m for m in listed.json() if m.get("status") == "done"
                      and (_when(m.get("created_at")) or cutoff) >= cutoff and m.get("id") is not None]
            brought = 0
            for meeting in recent:
                found = client.get(f"/api/meetings/{meeting['id']}")
                if found.status_code == 404:
                    continue  # deleted between the list and now
                found.raise_for_status()
                if _bring_in(base, found.json()):
                    brought += 1
    except (httpx.HTTPError, ValueError) as e:
        log.info("Trailmix isn't answering at %s: %s", base, e)
        return _note(reachable=False)
    _note(reachable=True, meetings=len(recent), brought_in=brought)


def _bring_in(base: str, meeting: dict) -> bool:
    """One finished meeting: a capture of its open action items (once per uid). True when one was made."""
    uid = str(meeting.get("uid") or "").strip()
    if not uid or meeting.get("status") != "done" or store.imported("trailmix", uid):
        return False
    items = [" ".join(str(t.get("text") or "").split()) for t in meeting.get("tasks") or [] if not t.get("done")]
    items = [i for i in items if i]
    title = (meeting.get("title") or "Untitled meeting").strip()
    capture = {
        "source": "trailmix", "title": title, "title_auto": False, "raw_text": meeting_text(meeting, items),
        "origin_id": uid, "origin_title": title, "origin_url": f"{base}/#meeting-{meeting['id']}",
        "origin_at": meeting.get("created_at"),
    } if items else None
    capture_id = store.record_import("trailmix", uid, capture)
    if not capture_id:
        return False
    # The meeting itself, for when Trailmix's meetings are a module here (ARCHITECTURE.md §13 keys them by uid).
    links.add(links.ref("inbox", capture_id), f"meetings:{uid}", "from")
    jobs.enqueue("inbox", "extract", capture_id)
    events.publish("inbox.capture.added", {"id": capture_id, "source": "trailmix"})
    return True
