"""The muster API, mounted at /api/muster. Errors are a sentence a person can read: 400 for a value that isn't right,
404 for a pick that isn't in the day's plan."""
from contextlib import contextmanager

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import days

router = APIRouter()


@contextmanager
def answers():
    try:
        yield
    except KeyError as e:
        raise HTTPException(404, "That pick isn't in the day's plan.") from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


def _day(value: str) -> str:
    try:
        return days.day_of(value)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


class DayPatch(BaseModel):
    intention: str | None = None
    tomorrow_note: str | None = None


class PickIn(BaseModel):
    ref: str | None = None
    title: str | None = None
    href: str | None = None
    minutes: int | None = None


class PickPatch(BaseModel):
    minutes: int | None = None
    done: bool | None = None
    title: str | None = None


class MoveIn(BaseModel):
    after: str | None = None


class WrapUpIn(BaseModel):
    let_go: list[str] = []
    note: str | None = None


@router.get("/start")
def start():
    """The first page of the day, for the web registry's start hook: {"path": "muster"} until you've looked today."""
    return {"path": days.start_page()}


@router.get("/today")
def today():
    return days.view(days.today().isoformat())


@router.post("/today/open")
def open_today():
    """The page is showing today: the first look fixes where "what moved" starts."""
    return days.open_day(days.today().isoformat())


@router.get("/days/{day}")
def get_day(day: str):
    return days.view(_day(day))


@router.post("/days/{day}/open")
def open_day(day: str):
    return days.open_day(_day(day))


@router.patch("/days/{day}")
def patch_day(day: str, body: DayPatch):
    with answers():
        days.update_day(_day(day), body.model_dump(exclude_unset=True))
    return {"ok": True}


@router.post("/days/{day}/kickoff")
def kick_off(day: str):
    days.kick_off(_day(day))
    return {"ok": True}


@router.post("/days/{day}/wrapup")
def wrap_up(day: str, body: WrapUpIn):
    with answers():
        return days.wrap_up(_day(day), body.let_go, body.note)


@router.post("/days/{day}/picks", status_code=201)
def add_pick(day: str, body: PickIn):
    with answers():
        return days.add_pick(_day(day), **body.model_dump())


@router.patch("/days/{day}/picks/{pick_id}")
def patch_pick(day: str, pick_id: str, body: PickPatch):
    with answers():
        return days.update_pick(_day(day), pick_id, body.model_dump(exclude_unset=True))


@router.post("/days/{day}/picks/{pick_id}/move")
def move_pick(day: str, pick_id: str, body: MoveIn):
    with answers():
        return days.move_pick(_day(day), pick_id, body.after)


@router.delete("/days/{day}/picks/{pick_id}", status_code=204)
def remove_pick(day: str, pick_id: str):
    with answers():
        days.remove_pick(_day(day), pick_id)
