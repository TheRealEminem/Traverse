"""The inbox API, mounted at /api/inbox. Fixed paths come before /captures/{id}.

Errors are a sentence a person can read: 400 for a value that isn't right, 404 for something that isn't there.
Nothing here calls the AI or Trailmix: reading a capture and checking Trailmix are jobs.
"""
from contextlib import contextmanager
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.server import contracts, events, jobs, links, settings

from . import capture, review, store, trailmix

router = APIRouter()


@contextmanager
def answers():
    try:
        yield
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


class PasteIn(BaseModel):
    text: str
    title: str = ""


class FileIn(BaseModel):
    name: str
    text: str


class CapturePatch(BaseModel):
    title: str


class ProjectIn(BaseModel):
    ref: str | None = None


class ProposalPatch(BaseModel):
    text: str | None = None
    assignee_name: str | None = None
    due_on: str | None = None
    priority: int | None = None


class AcceptIn(BaseModel):
    ids: list[str] | None = None   # None: every proposal still waiting


def _capture_or_404(capture_id: str) -> dict:
    found = store.get(capture_id)
    if not found:
        raise HTTPException(404, "That capture isn't in the inbox any more.")
    return found


def _proposal_or_404(proposal_id: str) -> dict:
    found = store.proposal(proposal_id)
    if not found:
        raise HTTPException(404, "That proposal isn't there any more.")
    return found


def _bring_in(fields: dict) -> dict:
    capture_id = store.create(**fields)
    jobs.enqueue("inbox", "extract", capture_id)
    events.publish("inbox.capture.added", {"id": capture_id, "source": fields["source"]})
    return {"id": capture_id}


# ── Fixed paths ───────────────────────────────────────────────────────

@router.get("/captures")
def list_captures():
    rows = store.captures()
    state = jobs.latest("inbox", [r["id"] for r in rows])
    return [{**r, "title_auto": bool(r["title_auto"]), "job": state.get(r["id"])} for r in rows]


@router.get("/count")
def count():
    return {"waiting": store.waiting_count()}


@router.post("/paste", status_code=201)
def paste(body: PasteIn):
    with answers():
        return _bring_in(capture.pasted(body.text, body.title))


@router.post("/file", status_code=201)
def from_file(body: FileIn):
    with answers():
        return _bring_in(capture.from_file(body.name, body.text))


@router.get("/trailmix")
def trailmix_status():
    cfg = settings.section("inbox")
    return {"enabled": cfg["trailmix"], "url": cfg["trailmix_url"], "last": trailmix.last() or None,
            "brought_in": store.imports_count("trailmix"),
            "job": jobs.latest("inbox", ["scheduled"]).get("scheduled")}


@router.post("/trailmix/check", status_code=202)
def trailmix_check():
    if not settings.section("inbox")["trailmix"]:
        raise HTTPException(400, "Turn on “Meetings from Trailmix” first.")
    jobs.enqueue("inbox", "trailmix", "scheduled")
    return {"ok": True}


# ── One capture ───────────────────────────────────────────────────────

@router.get("/captures/{capture_id}")
def get_capture(capture_id: str):
    found = _capture_or_404(capture_id)
    return {**found, "title_auto": bool(found["title_auto"]), "proposals": store.proposals(capture_id),
            "project": review.project_of(capture_id), "job": jobs.latest("inbox", [capture_id]).get(capture_id)}


@router.patch("/captures/{capture_id}")
def rename_capture(capture_id: str, body: CapturePatch):
    _capture_or_404(capture_id)
    title = " ".join(body.title.split())
    if not title:
        raise HTTPException(400, "A capture needs a title.")
    store.update(capture_id, title=title[:120], title_auto=0)
    events.publish("inbox.capture.changed", {"id": capture_id})
    return {"ok": True}


@router.post("/captures/{capture_id}/read", status_code=202)
def read_again(capture_id: str):
    """Reads it again: the proposals still waiting are replaced; what you decided stays."""
    _capture_or_404(capture_id)
    jobs.enqueue("inbox", "extract", capture_id)
    return {"ok": True}


@router.put("/captures/{capture_id}/project")
def set_project(capture_id: str, body: ProjectIn):
    _capture_or_404(capture_id)
    with answers():
        review.set_project(capture_id, body.ref or None)
    events.publish("inbox.capture.changed", {"id": capture_id})
    return {"project": review.project_of(capture_id)}


@router.post("/captures/{capture_id}/accept")
def accept(capture_id: str, body: AcceptIn):
    _capture_or_404(capture_id)
    ids = body.ids if body.ids is not None else [p["id"] for p in store.proposals(capture_id) if p["status"] == "proposed"]
    return {"accepted": review.accept(capture_id, ids)}


@router.delete("/captures/{capture_id}", status_code=204)
def delete_capture(capture_id: str):
    _capture_or_404(capture_id)
    ref = review.ref(capture_id)
    jobs.cancel_for("inbox", capture_id)
    store.delete(capture_id)
    events.publish(contracts.ITEM_DELETED, {"ref": ref})
    links.forget(ref)


# ── Proposals ─────────────────────────────────────────────────────────

@router.patch("/proposals/{proposal_id}")
def edit_proposal(proposal_id: str, body: ProposalPatch):
    found = _proposal_or_404(proposal_id)
    if found["status"] != "proposed":
        raise HTTPException(400, "That one's decided already. Change it in Tasks.")
    changes = body.model_dump(exclude_unset=True)
    if "text" in changes:
        changes["text"] = " ".join((changes["text"] or "").split())
        if not changes["text"]:
            raise HTTPException(400, "A work item needs some words.")
    if "assignee_name" in changes:
        changes["assignee_name"] = " ".join((changes["assignee_name"] or "").split()) or None
    if "due_on" in changes and changes["due_on"]:
        try:
            changes["due_on"] = date.fromisoformat(changes["due_on"]).isoformat()
        except ValueError as e:
            raise HTTPException(400, f"{changes['due_on']!r} isn't a date like 2026-10-31") from e
    elif "due_on" in changes:
        changes["due_on"] = None
    if "priority" in changes and changes["priority"] not in range(5):
        raise HTTPException(400, "Priority goes from 0 (none) to 4 (urgent).")
    if changes:
        store.update_proposal(proposal_id, **changes)
        events.publish("inbox.capture.changed", {"id": found["capture_id"]})
    return store.proposal(proposal_id)


@router.post("/proposals/{proposal_id}/accept")
def accept_one(proposal_id: str):
    found = _proposal_or_404(proposal_id)
    return {"accepted": review.accept(found["capture_id"], [proposal_id])}


@router.post("/proposals/{proposal_id}/drop")
def drop(proposal_id: str):
    found = _proposal_or_404(proposal_id)
    if found["status"] == "proposed":
        review.drop(found)
    return {"ok": True}


@router.post("/proposals/{proposal_id}/restore")
def restore(proposal_id: str):
    review.restore(_proposal_or_404(proposal_id))
    return {"ok": True}
