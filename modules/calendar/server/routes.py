"""The calendar API, mounted at /api/calendar. A source's address is never sent back: only the host it's on. Errors are
a sentence: 400 for a value that isn't right, 404 for a calendar that isn't here."""
from contextlib import contextmanager

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.server import events, jobs

from . import feeds, mac, store

router = APIRouter()


@contextmanager
def answers():
    try:
        yield
    except KeyError as e:
        raise HTTPException(404, "That calendar isn't here any more.") from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


def shown(row: dict, counts: dict | None = None) -> dict:
    """A source as the page sees it: everything but its address."""
    counts = store.counts() if counts is None else counts
    return {"id": row["id"], "kind": row["kind"], "name": row["name"], "enabled": bool(row["enabled"]),
            "host": store.host_of(row["url"]), "read_at": row["read_at"], "tried_at": row["tried_at"],
            "error": row["error"], "events": counts.get(row["id"], 0),
            "job": jobs.latest("calendar", [row["id"]]).get(row["id"])}


def _changed() -> None:
    events.publish("calendar.changed", {})


class SourceIn(BaseModel):
    kind: str
    name: str | None = None
    url: str | None = None


class SourcePatch(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    url: str | None = None


class EventsIn(BaseModel):
    events: list


@router.get("/sources")
def list_sources():
    counts = store.counts()
    return [shown(r, counts) for r in store.sources()]


@router.post("/sources", status_code=201)
def add_source(body: SourceIn):
    """An iCal address (read straight away, in a job) or this Mac's Calendar (the app's window sends its events)."""
    with answers():
        row = store.add(body.kind, body.name, body.url)
    if row["kind"] == "ical":
        jobs.enqueue("calendar", feeds.KIND, row["id"])
    _changed()
    return shown(row)


@router.patch("/sources/{source_id}")
def patch_source(source_id: str, body: SourcePatch):
    with answers():
        row = store.change(source_id, body.model_dump(exclude_unset=True))
    if row["kind"] == "ical" and row["enabled"] and ({"url", "enabled"} & body.model_fields_set):
        jobs.enqueue("calendar", feeds.KIND, row["id"])
    _changed()
    return shown(row)


@router.delete("/sources/{source_id}", status_code=204)
def remove_source(source_id: str):
    jobs.cancel_for("calendar", source_id)
    if not store.remove(source_id):
        raise HTTPException(404, "That calendar isn't here any more.")
    _changed()


@router.post("/sources/{source_id}/read", status_code=202)
def read_now(source_id: str):
    row = store.source(source_id)
    if row is None:
        raise HTTPException(404, "That calendar isn't here any more.")
    if row["kind"] != "ical":
        raise HTTPException(400, "This Mac's Calendar is sent by the app's window whenever it's open.")
    jobs.enqueue("calendar", feeds.KIND, source_id)
    _changed()
    return shown(row)


@router.put("/sources/{source_id}/events")
def take_events(source_id: str, body: EventsIn):
    """This Mac's Calendar, as the app's window read it: today's and the next week's events."""
    with answers():
        return {"kept": mac.take(source_id, body.events)}
