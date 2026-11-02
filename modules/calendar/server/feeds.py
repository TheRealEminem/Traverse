"""Reading a calendar's private iCal address (the calendar/read job): fetch it, turn its events into this computer's
time for the window that matters (today and the next week), with repeats expanded and moved or skipped times
honoured, and keep them in place of what the source had.

Left out: cancelled events, events you declined (when the calendar says who you are: Google names your main calendar
after your address), and anything outside the window. "Show as: Free" (TRANSP:TRANSPARENT) is kept as free time.

The address is a secret, so nothing here repeats it: an error says what went wrong in words, never the URL, and
httpx's own log line for each request (INFO, which the server log keeps) names only the host while a calendar is read.
"""
import logging
import threading
from datetime import date, datetime, time, timedelta

import httpx
import icalendar
import recurring_ical_events

from core.server import config, events
from core.server.jobs import Job

from . import store

log = logging.getLogger("calendar.feeds")

KIND = "read"
EVERY_SECONDS = 15 * 60
MOST_BYTES = 20 * 1024 * 1024
_transport: httpx.BaseTransport | None = None          # tests put a fake calendar server here


class ReadError(Exception):
    """A sentence for the screen about why a calendar couldn't be read."""


_reading = threading.local()


class _HostOnly(logging.Filter):
    """httpx logs every request's whole URL; while this thread reads a calendar, its lines say only the host."""

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(_reading, "now", False) and isinstance(record.args, tuple):
            record.args = tuple(f"{a.scheme}://{a.host}/…" if isinstance(a, httpx.URL) else a for a in record.args)
        return True


logging.getLogger("httpx").addFilter(_HostOnly())


def every() -> int:
    """How often the recurring read runs: while there are calendars at all (it also forgets past events)."""
    return EVERY_SECONDS if store.sources() else 0


def fetch(url: str) -> bytes:
    _reading.now = True
    try:
        with httpx.Client(transport=_transport, timeout=httpx.Timeout(20, connect=8), follow_redirects=True,
                          headers={"User-Agent": f"{config.NAME}/{config.VERSION}"}) as http:
            r = http.get(url)
    except httpx.TimeoutException:
        raise ReadError("The calendar didn't answer in time. It's tried again in a few minutes.") from None
    except httpx.HTTPError:
        raise ReadError("Couldn't reach the calendar. It's tried again in a few minutes.") from None
    finally:
        _reading.now = False
    if r.status_code in (401, 403, 404, 410):
        raise ReadError(f"The calendar turned its address down ({r.status_code}). It may have been reset: copy the "
                        "private address again from the calendar's settings.")
    if r.status_code >= 400:
        raise ReadError(f"The calendar's server answered {r.status_code}. It's tried again in a few minutes.")
    if len(r.content) > MOST_BYTES:
        raise ReadError("That calendar is too big to read (over 20 MB).")
    if b"BEGIN:VCALENDAR" not in r.content[:4096].upper():
        raise ReadError("That address doesn't give a calendar. Copy the private iCal address from the calendar's settings.")
    return r.content


def _local(value) -> datetime | date:
    """A moment in this computer's time, without a zone; a day stays a day. Floating times are taken as local."""
    if isinstance(value, datetime):
        return value.astimezone().replace(tzinfo=None) if value.tzinfo else value
    return value


def _as_moment(value: datetime | date) -> datetime:
    return value if isinstance(value, datetime) else datetime.combine(value, time())


def _text(value, longest: int) -> str:
    return " ".join(str(value).split())[:longest] if value is not None else ""


def _declined(component, me: str | None) -> bool:
    if not me:
        return False
    found = component.get("ATTENDEE") or []
    for person in found if isinstance(found, list) else [found]:
        if str(person).lower().removeprefix("mailto:") == me and str(person.params.get("PARTSTAT", "")).upper() == "DECLINED":
            return True
    return False


def parse(data: bytes, on: date) -> list[dict]:
    """The events of an iCal file that touch [on, on + WINDOW_DAYS), as store.replace takes them. Raises ValueError for
    a file that isn't iCal."""
    cal = icalendar.Calendar.from_ical(data)
    name = _text(cal.get("X-WR-CALNAME"), 100)
    me = name.lower() if "@" in name else None
    start, end = store.window(on)
    out = []
    for c in recurring_ical_events.of(cal).between(start - timedelta(days=1), end + timedelta(days=1)):
        if str(c.get("STATUS", "")).upper() == "CANCELLED" or _declined(c, me):
            continue
        first = c.get("DTSTART")
        if first is None:
            continue
        begins = _local(first.dt)
        if c.get("DTEND") is not None:
            finishes = _local(c.get("DTEND").dt)
        elif c.get("DURATION") is not None:
            finishes = _local(first.dt + c.get("DURATION").dt)
        else:
            finishes = begins + timedelta(days=1) if not isinstance(begins, datetime) else begins
        all_day = not isinstance(begins, datetime)
        if _as_moment(begins) >= end or _as_moment(finishes) <= start or _as_moment(finishes) < _as_moment(begins):
            continue
        stamp = (lambda v: v.isoformat()) if all_day else (lambda v: _as_moment(v).isoformat(timespec="minutes"))
        out.append({"uid": _text(c.get("UID"), 300) or _text(c.get("SUMMARY"), 100), "title": _text(c.get("SUMMARY"), 200) or "Busy",
                    "starts": stamp(begins), "ends": stamp(finishes), "all_day": all_day,
                    "free": str(c.get("TRANSP", "OPAQUE")).upper() == "TRANSPARENT", "calendar": name})
    return out


def read_one(source_id: str) -> None:
    row = store.source(source_id)
    if row is None or row["kind"] != "ical" or not row["enabled"]:
        return
    try:
        found = parse(fetch(row["url"]), store.today())
    except ReadError as e:
        store.tried(source_id, str(e))
        return
    except ValueError:
        store.tried(source_id, "The address gave a file that isn't a calendar Traverse can read.")
        return
    except Exception:  # noqa: BLE001 - one odd calendar mustn't stop the others; the log has the details
        log.exception("Couldn't read calendar %s", source_id)
        store.tried(source_id, "Something in this calendar couldn't be read. The server log has the details.")
        return
    store.replace(source_id, found)
    store.tried(source_id, None)


def read(job: Job) -> None:
    """calendar/read: one source ("Read now", or just added), or every enabled iCal source (the schedule). Either way,
    events that ended before today are forgotten first."""
    store.forget_past()
    ids = [r["id"] for r in store.sources() if r["kind"] == "ical" and r["enabled"]] if job.target == "scheduled" else [job.target]
    for source_id in ids:
        job.stage("Reading " + ((store.source(source_id) or {}).get("name") or "the calendar"))
        read_one(source_id)
    events.publish("calendar.changed", {})
