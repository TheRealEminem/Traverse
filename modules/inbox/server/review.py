"""Deciding on proposals, and filing what you accept.

Accepting announces the shared contract actions.found for the capture ("inbox:<id>"), and whoever keeps tasks (the
tasks module) makes them. Tasks replaces a source's earlier items you haven't touched with the ones announced, so
each announcement carries everything accepted from the capture so far, except items you've since deleted there
(which would otherwise come back). Which project they go into is a link from the capture to that project; the tasks
module files them there when there's exactly one.
"""
from core.server import contracts, db, events, links, module, settings

from . import store

ABOUT = "about"   # the capture -> project link's kind


def ref(capture_id: str) -> str:
    return links.ref("inbox", capture_id)


def project_of(capture_id: str) -> dict | None:
    """The project the capture files into: {ref, title, href}, or None."""
    for link in links.linked(ref(capture_id)):
        if link["kind"] == ABOUT and link["direction"] == "to" and link["module"] == "tasks":
            return {"ref": link["ref"], "title": link["title"], "href": link["href"]}
    return None


def set_project(capture_id: str, project_ref: str | None) -> None:
    """Files the capture's accepted items into project_ref (a "tasks:<id>" the host can name), or into none."""
    if project_ref and (not project_ref.startswith("tasks:") or module.describe(project_ref) is None):
        raise ValueError("That project isn't there any more.")
    here = ref(capture_id)
    for link in links.linked(here):
        if link["kind"] == ABOUT and link["direction"] == "to" and link["ref"] != project_ref:
            links.remove(here, link["ref"], ABOUT)
    if project_ref:
        links.add(here, project_ref, ABOUT)


def _assignee(name: str | None, your_name: str) -> dict:
    """You become "core:me", so the item is yours wherever tasks shows your work; anyone else is kept by name until
    the people directory (chunk 5) can say who they are."""
    if not name:
        return {}
    first = your_name.split()[0].casefold() if your_name.strip() else ""
    if name.casefold() in ("me", "you", "myself") or (your_name and name.casefold() in (your_name.casefold(), first)):
        return {"assignee_ref": "core:me", "assignee_name": your_name or None}
    return {"assignee_name": name}


def as_item(p: dict, your_name: str) -> dict:
    return {"text": p["text"], "due_on": p["due_on"], "priority": p["priority"], **_assignee(p["assignee_name"], your_name)}


def accept(capture_id: str, proposal_ids: list[str]) -> int:
    """Accepts these proposals (those still waiting) and announces the capture's accepted items. Returns how many
    were accepted now."""
    waiting = {p["id"] for p in store.proposals(capture_id) if p["status"] == "proposed"}
    fresh = [pid for pid in proposal_ids if pid in waiting]
    if not fresh:
        return 0
    filed_before = {link["title"] for link in links.linked(ref(capture_id))
                    if link["module"] == "tasks" and link["kind"] == "action-item"}
    for pid in fresh:
        store.update_proposal(pid, status="accepted", decided_at=db.now())
    your_name = settings.section("core")["your_name"].strip()
    announce = [p for p in store.proposals(capture_id)
                if p["status"] == "accepted" and (p["id"] in fresh or p["text"] in filed_before)]
    events.publish(contracts.ACTIONS_FOUND, {"source_ref": ref(capture_id), "items": [as_item(p, your_name) for p in announce]})
    store.settle(capture_id)
    events.publish("inbox.capture.changed", {"id": capture_id})
    return len(fresh)


def drop(proposal: dict) -> None:
    store.update_proposal(proposal["id"], status="dropped", decided_at=db.now())
    store.settle(proposal["capture_id"])
    events.publish("inbox.capture.changed", {"id": proposal["capture_id"]})


def restore(proposal: dict) -> None:
    """A dropped proposal waits again (Undo)."""
    if proposal["status"] != "dropped":
        return
    store.update_proposal(proposal["id"], status="proposed", decided_at=None)
    store.settle(proposal["capture_id"])
    events.publish("inbox.capture.changed", {"id": proposal["capture_id"]})
