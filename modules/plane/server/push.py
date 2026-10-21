"""Sending your changes to Plane (PLAN.md chunk 7 and §3.3): the only way anything Traverse does reaches Plane.

How a push goes:
1. "Send to Plane" on a task: tasks publishes contracts.WORK_SHARE_REQUESTED with only the fields you've changed
   since the base, and their base. `requested` makes them a push (plane_pushes) with one entry per field: what Plane
   has (the mirror) and what it will have. Its job is parked as "Needs you" (rule 2), and the task is linked to it
   (kind "share") so its page can say where it waits. Asking again replaces what's waiting rather than adding to it.
2. The outbox (#/plane/outbox) shows it field by field. Notes start left out (§7: a description is written whole),
   and any field can be. Send approves it; Discard forgets it.
3. The job (`send`) reads the item from Plane again first (rule 4). A field whose Plane value has changed since you
   last saw it stops the push: both values show, and you choose Plane's (the task takes it) or yours (sent over it).
   Assignees are merged, never replaced (rule 5): Plane's list as it is now, plus yours, minus the one you replaced.
   Only the push's fields are written, in one PATCH (rule 3); a new task in a linked project is made there (POST).
4. What was sent is logged with each field's before and after and when you approved it (rule 7). The mirror takes
   Plane's answer and the task is told (WORK_UPDATED_ELSEWHERE, or WORK_ARRIVED with local_ref for a new item), so
   its base moves on. Undo makes a new push of the "before" values, with the same preview and check.
5. Dry run (rule 8, a setting) does all of that except the write: Send reads Plane, checks, and says what it would
   have written. The push stays waiting.
The client has no way to delete anything (rule 1), and nothing here would ask it to.

A field's entry in `changes`:
  field, label, key  Traverse's field (linking.FIELDS), its label, and Plane's field
  mine, base         the Traverse values to send, and as both sides last agreed ({"due_on": "2026-10-31"}; {} for new)
  was, will          Plane's value before (from the mirror when asked; once sent, as read right before writing) and to
                     be written (assignees: Plane's list merged with add and remove)
  add, remove        assignees only: the member ids you added and took off
  include            sent only when true
  skip               why it can't be sent at all (no state for that status, someone who isn't in Plane)
  theirs             stopped: Plane's value now, changed since `was`
  over               you chose to send yours over a change made in Plane
  sent               once sent: Plane's value as Plane answered
"""
import json
import logging
import threading
from datetime import datetime, timedelta

from core.server import db, events, jobs, links, mcp, module
from core.server.jobs import Job

from . import html, linking, pull, store, team
from .client import PlaneClient, PlaneError

log = logging.getLogger("plane.push")

KIND = "push"
NEEDS_YOU = ("waiting", "stopped", "failed")
OPEN = (*NEEDS_YOU, "sending")
PRIORITY_LABEL = {"none": "None", "low": "Low", "medium": "Medium", "high": "High", "urgent": "Urgent"}
_writing = threading.Lock()     # one push at a time, so two can't read and write the same item at once


def dry_run(cfg: dict) -> bool:
    """Dry run unless it's been turned off: a setting that's missing or unreadable never means "write"."""
    return cfg.get("dry_run") is not False


def _ref(push_id: str) -> str:
    return links.ref("plane", push_id)


def _row(push_id: str) -> dict | None:
    return db.one("SELECT * FROM plane_pushes WHERE id = ?", (push_id,))


def _get(push_id: str) -> dict:
    row = _row(push_id)
    if row is None:
        raise KeyError(push_id)
    return row


def _set(push_id: str, **fields) -> None:
    if "changes" in fields:
        fields["changes"] = json.dumps(fields["changes"])
    fields["updated_at"] = db.now()
    db.execute(f"UPDATE plane_pushes SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?", (*fields.values(), push_id))
    events.publish("plane.pushes.changed", {"push": push_id})


def _labels(entries: list[dict]) -> str:
    names = [e["label"] for e in entries]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


# ── Traverse's values as Plane's ──────────────────────────────────────

def merge(now: list[str], add: list[str], remove: list[str]) -> list[str]:
    """A list as Plane has it now, plus your additions, minus your removals: nobody added in Plane is dropped."""
    return sorted({m for m in now if m not in remove} | set(add))


def _member(who: str | None, name: str | None) -> str | None:
    """The Plane member an assignee is (None for no one). Raises ValueError for someone Plane doesn't have."""
    if not who and not name:
        return None
    if who == "core:me":
        me = team.me_id()
        if not me:
            raise ValueError("Traverse doesn't know which Plane member is you yet (Settings → Plane)")
        return me
    if who and who.startswith("plane:"):
        member = who.split(":", 1)[1]
        if db.one("SELECT 1 FROM plane_members WHERE id = ? AND removed_at IS NULL", (member,)):
            return member
    raise ValueError(f"{name or 'They'} isn't in Plane")


def _plane_value(field: str, value, project_id: str):
    if field == "notes":
        return html.to_html(value)
    if field == "status":
        state = linking.state_map(project_id).get(value)
        if not state:
            project = db.one("SELECT name FROM plane_projects WHERE id = ?", (project_id,))
            raise ValueError(f"{project['name'] if project else 'The project'} has no state for "
                             f"{linking.STATUS_LABEL.get(value, value)}")
        return state
    if field == "priority":
        return linking.PRIORITY_NAME.get(int(value or 0), "none")
    return value


def _entry(field: str, mine: dict, base: dict, item: dict | None, project_id: str) -> dict:
    """One field of a push: what Plane has, what it will have, or why it can't go."""
    cols, key, label = linking.FIELDS[field]
    was = linking.raw(item, field) if item else ([] if field == "assignee" else None)
    entry = {"field": field, "label": label, "key": key, "mine": mine, "base": base, "was": was,
             "include": field != "notes" or item is None}
    try:
        if field == "assignee":
            target = _member(mine.get("assignee_ref"), mine.get("assignee_name"))
            try:
                before = _member(base.get("assignee_ref"), base.get("assignee_name"))
            except ValueError:
                before = None                   # someone Plane doesn't have: nobody there to take off
            entry["add"] = [target] if target else []
            entry["remove"] = [before] if before and before != target else []
            entry["will"] = merge(was, entry["add"], entry["remove"])
        else:
            entry["will"] = _plane_value(field, mine[cols[0]], project_id)
    except ValueError as e:
        entry.update(skip=str(e), will=was, include=False)
    return entry


def _same(field: str, a, b) -> bool:
    """Plane values that are the same as far as Traverse can tell (notes as the Markdown they read as)."""
    if field == "notes":
        return html.to_markdown(a) == html.to_markdown(b)
    return a == b


def _worth_making(entry: dict) -> bool:
    """A new item's field that says something (its name and status always do)."""
    return entry["field"] in ("text", "status") or entry["will"] not in (None, "", [], "none", "<p></p>")


# ── Asking (contracts.WORK_SHARE_REQUESTED) ───────────────────────────

def requested(payload: dict) -> None:
    """Your changes to a Plane item (or a new task in a linked project) become a push waiting for you."""
    ref, local = payload.get("ref") or "", payload.get("local_ref") or ""
    fields, base = payload.get("fields") or {}, payload.get("base") or {}
    if ref.startswith("plane:"):
        item = db.one("SELECT * FROM plane_items WHERE id = ?", (ref.split(":", 1)[1],))
        if item is None:
            log.warning("Not sending %s: it isn't in the copy of Plane", ref)
            return
        kind, project_id = "update", item["project_id"]
    elif ref and ref == local and payload.get("project_ref"):
        link = db.one("SELECT project_id FROM plane_links WHERE local_ref = ?", (payload["project_ref"],))
        if link is None:
            return
        kind, project_id, item = "create", link["project_id"], None
    else:
        return
    changes = [_entry(field, {c: fields[c] for c in cols if c in fields}, {c: base.get(c) for c in cols if c in fields},
                      item, project_id)
               for field, (cols, _, _) in linking.FIELDS.items() if any(c in fields for c in cols)]
    if kind == "create":
        changes = [e for e in changes if _worth_making(e)]
    stamp = db.now()
    old = db.one(f"SELECT * FROM plane_pushes WHERE local_ref = ? AND kind = ? AND status IN {NEEDS_YOU} "
                 f"ORDER BY created_at DESC LIMIT 1", (local, kind))
    if old:
        chosen = {e["field"]: e["include"] for e in json.loads(old["changes"]) if not e.get("skip")}
        for e in changes:
            if e["field"] in chosen and not e.get("skip"):
                e["include"] = chosen[e["field"]]
        push_id = old["id"]
        _set(push_id, changes=changes, status="waiting", note=None, project_id=project_id,
             item_id=item["id"] if item else old["item_id"])     # a new item it may have made already stays found
    else:
        push_id = db.new_id()
        db.execute("INSERT INTO plane_pushes (id, kind, local_ref, project_id, item_id, changes, status, created_at, "
                   "updated_at) VALUES (?, ?, ?, ?, ?, ?, 'waiting', ?, ?)",
                   (push_id, kind, local, project_id, item["id"] if item else None, json.dumps(changes), stamp, stamp))
    links.add(local, _ref(push_id), "share")
    jobs.enqueue("plane", KIND, push_id, approve=True, reason="Waiting for you to send it")
    events.publish("plane.pushes.changed", {"push": push_id})


def local_deleted(payload: dict) -> None:
    """contracts.ITEM_DELETED: a task with changes waiting to be sent is gone, so they won't be."""
    for row in db.query(f"SELECT id FROM plane_pushes WHERE local_ref = ? AND status IN {NEEDS_YOU}", (payload["ref"],)):
        _forget(row["id"])


# ── What you can do in the outbox ─────────────────────────────────────

def approve(push_id: str) -> None:
    """Send: the push's job goes ahead (it reads Plane again before writing anything). Yours only: never from one of
    Claude's tools (core/server/mcp.py), which may propose a push but not send it."""
    if mcp.calling():
        raise PermissionError("Claude can't send to Plane. Only you can, with Send in the outbox.")
    push = _get(push_id)
    if push["status"] == "sending":
        return
    if push["status"] not in NEEDS_YOU:
        raise ValueError("That's been sent already" if push["status"] == "sent" else "That was discarded")
    changes = json.loads(push["changes"])
    if any("theirs" in e and e["include"] for e in changes):
        raise ValueError("Choose Plane's or yours for what changed in Plane first")
    if not any(e["include"] and not e.get("skip") for e in changes):
        raise ValueError("Choose at least one thing to send")
    _set(push_id, status="sending", approved_at=db.now(), note=None)
    jobs.enqueue("plane", KIND, push_id)    # the parked job goes ahead (or a new one, after something went wrong)


def discard(push_id: str) -> None:
    """Forgets a push that hasn't been sent. Nothing in Plane or in the task changes; the task's edits stay edits."""
    push = _get(push_id)
    if push["status"] not in NEEDS_YOU:
        raise ValueError("It's being sent now" if push["status"] == "sending" else "It isn't waiting to be sent")
    _forget(push_id)


def _forget(push_id: str) -> None:
    push = _get(push_id)
    _set(push_id, status="discarded")
    jobs.cancel_for("plane", push_id)
    links.remove(push["local_ref"], _ref(push_id), "share")
    if push["undo_of"]:
        db.execute("UPDATE plane_pushes SET undone_by = NULL WHERE id = ? AND undone_by = ?", (push["undo_of"], push_id))


def include(push_id: str, choices: dict) -> None:
    """Puts fields in or leaves them out ({"notes": true}). A field left out isn't sent, and stays your edit."""
    push = _get(push_id)
    if push["status"] not in NEEDS_YOU:
        raise ValueError("It isn't waiting to be sent")
    changes = json.loads(push["changes"])
    for field, on in choices.items():
        entry = next((e for e in changes if e["field"] == field), None)
        if entry is None:
            raise ValueError(f"{linking.FIELDS[field][2] if field in linking.FIELDS else field} isn't in this push")
        if entry.get("skip") and on:
            raise ValueError(entry["skip"])
        entry["include"] = bool(on)
    stopped = any("theirs" in e and e["include"] for e in changes)
    _set(push_id, changes=changes, status="stopped" if stopped else ("waiting" if push["status"] == "stopped"
                                                                      else push["status"]))


def choose(push_id: str, field: str, keep: str) -> None:
    """A field changed in Plane since you last saw it: keep "plane" (it leaves the push, and the task takes Plane's
    value) or "mine" (yours is sent over it when you press Send)."""
    push = _get(push_id)
    if keep not in ("plane", "mine"):
        raise ValueError("keep is plane or mine")
    changes = json.loads(push["changes"])
    entry = next((e for e in changes if e["field"] == field and "theirs" in e), None)
    if push["status"] != "stopped" or entry is None:
        raise ValueError("That isn't waiting for a choice")
    if keep == "mine":
        entry["was"] = entry.pop("theirs")      # you've seen Plane's value; Send writes yours over it, unless it moves again
        entry["over"] = True
    else:
        changes.remove(entry)
        linking.publish_item(push["item_id"], take=[field])
    if not any(not e.get("skip") for e in changes):
        _set(push_id, changes=changes)
        _forget(push_id)
        return
    stopped = any("theirs" in e and e["include"] for e in changes)
    _set(push_id, changes=changes, status="stopped" if stopped else "waiting", note=push["note"] if stopped else None)


def undo(push_id: str) -> str:
    """A new push putting back what a sent push changed, with the same preview and check (it stops if someone has
    changed those fields in Plane since). Returns its id."""
    push = _get(push_id)
    if push["status"] != "sent":
        raise ValueError("Only something that was sent can be undone")
    if push["kind"] == "create":
        raise ValueError("Traverse never deletes anything in Plane, so a new item can't be undone from here. "
                         "Delete it in Plane if you need to.")
    if push["undone_by"]:
        raise ValueError("It's being undone already" if (_row(push["undone_by"]) or {}).get("status") in OPEN
                         else "It was undone already")
    entries = []
    for e in json.loads(push["changes"]):
        if not e["include"] or e.get("skip") or "sent" not in e or _same(e["field"], e["was"], e["sent"]):
            continue
        back = {"field": e["field"], "label": e["label"], "key": e["key"], "mine": e["base"], "base": e["mine"],
                "was": e["sent"], "include": True}
        if e["field"] == "assignee":
            back["add"] = [m for m in e["was"] if m not in e["sent"]]
            back["remove"] = [m for m in e["sent"] if m not in e["was"]]
            back["will"] = merge(e["sent"], back["add"], back["remove"])
        else:
            back["will"] = e["was"]
        entries.append(back)
    if not entries:
        raise ValueError("Nothing was changed in Plane, so there's nothing to undo")
    undo_id, stamp = db.new_id(), db.now()
    db.execute("INSERT INTO plane_pushes (id, kind, local_ref, project_id, item_id, changes, status, undo_of, "
               "created_at, updated_at) VALUES (?, 'undo', ?, ?, ?, ?, 'waiting', ?, ?, ?)",
               (undo_id, push["local_ref"], push["project_id"], push["item_id"], json.dumps(entries), push_id, stamp,
                stamp))
    db.execute("UPDATE plane_pushes SET undone_by = ? WHERE id = ?", (undo_id, push_id))
    links.add(push["local_ref"], _ref(undo_id), "share")
    jobs.enqueue("plane", KIND, undo_id, approve=True, reason="Waiting for you to send it")
    events.publish("plane.pushes.changed", {"push": undo_id})
    return undo_id


# ── The job ───────────────────────────────────────────────────────────

def send(job: Job) -> None:
    """plane/push: check the push against Plane as it is now, then write it (or, in a dry run, say what it would
    write). Safe to run twice: a field already as it would be written isn't written again."""
    with _writing:
        push = _row(job.target)
        if push is None or push["status"] != "sending":
            return
        cfg = pull.config()
        try:
            with pull.client(cfg) as c:
                (_create if push["kind"] == "create" else _update)(c, push, dry_run(cfg), job)
        except PlaneError as e:
            _set(push["id"], status="failed", note=str(e), checked_at=db.now())
            raise jobs.Wait(str(e)) from e


def _update(c: PlaneClient, push: dict, dry: bool, job: Job) -> None:
    push_id, project_id, item_id = push["id"], push["project_id"], push["item_id"]
    changes = json.loads(push["changes"])
    todo = [e for e in changes if e["include"] and not e.get("skip")]
    job.stage("Reading it from Plane")
    fresh = store.item_row(c.work_item(project_id, item_id), project_id)
    moved = store.put_item(fresh)
    meaning = linking.fields_for(fresh)
    body, stopped = {}, []
    for e in todo:
        # What Plane's value now means in Traverse, so `base` keeps describing `was` even when you send yours over a
        # change made there (Undo puts that back, and the task follows it).
        e["base"] = {c: meaning.get(c) for c in linking.FIELDS[e["field"]][0]}
        now = linking.raw(fresh, e["field"])
        if e["field"] == "assignee":
            e["was"], e["will"] = now, merge(now, e["add"], e["remove"])
            if e["will"] != now:
                body[e["key"]] = e["will"]
        elif _same(e["field"], now, e["will"]):
            e["was"] = now                      # there already (sent before a restart, or someone made the same change)
        elif _same(e["field"], now, e["was"]):
            body[e["key"]] = e["will"]
        else:
            e["theirs"] = now
            stopped.append(e)
    stamp = db.now()
    if stopped:
        _set(push_id, status="stopped", changes=changes, checked_at=stamp,
             note=f"{_labels(stopped)} changed in Plane since you last saw it. Nothing was sent.")
        linking.publish_item(item_id)           # the task sees Plane's value too ("Changed in Plane")
        raise jobs.Wait(f"{_labels(stopped)} changed in Plane: choose which to keep")
    if dry:
        would = [e for e in todo if e["key"] in body]
        _set(push_id, status="waiting", changes=changes, checked_at=stamp,
             note=(f"Dry run: checked against Plane. Send would change {_labels(would)}." if would else
                   "Dry run: checked against Plane. It's all there already, so Send would write nothing.")
             + " Nothing was sent.")
        if moved:
            linking.publish_item(item_id)
        raise jobs.Wait("Dry run: nothing was sent")
    after = fresh
    if body:
        job.stage("Sending it to Plane")
        c.update_work_item(project_id, item_id, body)
        after = store.item_row(c.work_item(project_id, item_id), project_id)   # what Plane holds now
        store.put_item(after)
    _finish(push, changes, todo, after, None if body else "It was all in Plane already, so nothing needed writing.")
    linking.publish_item(item_id)               # the task's base moves on to what was sent


def _create(c: PlaneClient, push: dict, dry: bool, job: Job) -> None:
    push_id, project_id = push["id"], push["project_id"]
    changes = json.loads(push["changes"])
    job.stage("Checking the project in Plane")
    states = {s["id"] for s in c.states(project_id)}
    for e in changes:
        if e["field"] == "status" and e["include"] and e["will"] not in states:
            e.update(skip="That state isn't in Plane any more, so Plane will use its default", include=False)
    todo = [e for e in changes if e["include"] and not e.get("skip")]
    body = {e["key"]: e["will"] for e in todo}
    project = db.one("SELECT name FROM plane_projects WHERE id = ?", (project_id,))
    if dry:
        _set(push_id, status="waiting", changes=changes, checked_at=db.now(),
             note=f"Dry run: Send would add it to {project['name'] if project else 'the project'} in Plane with "
                  f"{_labels(todo).lower()}. Nothing was sent.")
        raise jobs.Wait("Dry run: nothing was sent")
    item_id = push["item_id"] or (_made_before(c, push, body) if push["attempted_at"] else None)
    if not item_id:
        job.stage("Adding it to Plane")
        _set(push_id, attempted_at=db.now(), changes=changes)
        item_id = c.create_work_item(project_id, body)["id"]
    _set(push_id, item_id=item_id)
    after = store.item_row(c.work_item(project_id, item_id), project_id)
    store.put_item(after)
    _finish({**push, "item_id": item_id}, changes, todo, after, None)
    linking.publish_made(item_id, push["local_ref"])


def _made_before(c: PlaneClient, push: dict, body: dict) -> str | None:
    """A create that was cut off after sending (Traverse stopped): the item it made, if Plane has it, so it isn't made
    twice. Yours, with this name, made since the attempt (give or take the clocks), and not linked to anything."""
    me, since = team.me_id(), datetime.fromisoformat(push["attempted_at"]) - timedelta(minutes=10)
    linked = set(linking.linked_items())
    found = [i for i in c.work_items(push["project_id"])
             if i.get("name") == body.get("name") and store.item_row(i, push["project_id"])["created_by"] == me
             and i["id"] not in linked and i.get("created_at") and datetime.fromisoformat(i["created_at"]) >= since]
    return max(found, key=lambda i: i["created_at"])["id"] if found else None


def _finish(push: dict, changes: list[dict], todo: list[dict], after: dict, note: str | None) -> None:
    """Logs what Plane holds now for each field sent, and remembers what those values mean in Traverse."""
    stamp = db.now()
    for e in todo:
        e["sent"] = linking.raw(after, e["field"])
        linking.remember(push["item_id"], e["field"], e["sent"], e["mine"], push["id"])
    _set(push["id"], status="sent", changes=changes, sent_at=stamp, checked_at=stamp, note=note)
    links.remove(push["local_ref"], _ref(push["id"]), "share")


# ── What the outbox shows ─────────────────────────────────────────────

def _show(field: str, value, names: dict) -> str:
    """A Plane value the way the outbox shows it: a state's name, people's names, notes as text… ("" for nothing)."""
    if value in (None, "", []):
        return ""
    if field == "notes":
        text = html.to_markdown(value)
        return text if len(text) <= 400 else text[:400].rstrip() + "…"
    if field == "status":
        return names["states"].get(value, "A state Traverse doesn't know")
    if field == "priority":
        return PRIORITY_LABEL.get(value, value)
    if field == "assignee":
        return ", ".join(sorted((names["members"].get(m, "Someone not in the workspace") for m in value), key=str.lower))
    return str(value)


def _view(push: dict, ctx: dict) -> dict:
    changes = json.loads(push["changes"])
    item = ctx["items"].get(push["item_id"]) if push["item_id"] else None
    project = ctx["projects"].get(push["project_id"])
    is_open = push["status"] in OPEN or push["status"] == "discarded"
    fields = []
    for e in changes:
        f = e["field"]
        row = {"field": f, "label": e["label"], "include": e["include"], "skip": e.get("skip"),
               "over": bool(e.get("over")), "changed": False, "already": False, "theirs": None, "yours": None}
        if is_open:
            now = linking.raw(item, f) if item else e["was"]
            will = merge(now, e["add"], e["remove"]) if f == "assignee" and not e.get("skip") else e["will"]
            row.update(before=_show(f, now, ctx), after=_show(f, will, ctx),
                       already=bool(item) and not e.get("skip") and _same(f, now, will))
            if "theirs" in e:
                row.update(before=_show(f, e["was"], ctx), theirs=_show(f, e["theirs"], ctx), yours=_show(f, will, ctx))
            elif item and f != "assignee" and not _same(f, now, e["was"]) and not _same(f, now, will):
                row["changed"] = True           # a pull saw Plane change it since you asked: Send will stop and ask
        else:
            row.update(before=_show(f, e["was"], ctx), after=_show(f, e.get("sent", e["will"]), ctx))
        fields.append(row)
    task = module.describe(push["local_ref"])
    undone = _row(push["undone_by"]) if push["undone_by"] else None
    return {
        "id": push["id"], "kind": push["kind"], "status": push["status"], "note": push["note"],
        "created_at": push["created_at"], "approved_at": push["approved_at"], "sent_at": push["sent_at"],
        "checked_at": push["checked_at"], "undo_of": push["undo_of"],
        "undone": undone and {"id": undone["id"], "status": undone["status"], "sent_at": undone["sent_at"]},
        "task": task and {"title": task["title"], "href": task["href"]},
        "item": item and {"id": item["id"], "key": ctx["where"].key(item), "name": item["name"],
                          "url": ctx["where"].url(item), "removed": bool(item["removed_at"])},
        "project": project and {"id": project["id"], "name": project["name"]},
        "fields": fields, "job": ctx["jobs"].get(push["id"]),
    }


def outbox() -> dict:
    """GET /api/plane/outbox: what waits for you, newest last, and the latest of what was sent."""
    waiting = db.query(f"SELECT * FROM plane_pushes WHERE status IN {OPEN} ORDER BY created_at")
    sent = db.query("SELECT * FROM plane_pushes WHERE status = 'sent' ORDER BY sent_at DESC LIMIT 50")
    rows = waiting + sent
    item_ids = sorted({r["item_id"] for r in rows if r["item_id"]})
    marks = ",".join("?" * len(item_ids))
    ctx = {
        "items": {i["id"]: i for i in db.query(f"SELECT * FROM plane_items WHERE id IN ({marks})", item_ids)} if item_ids else {},
        "projects": {p["id"]: p for p in db.query("SELECT id, name, identifier FROM plane_projects")},
        "states": {s["id"]: s["name"] for s in db.query("SELECT id, name FROM plane_states")},
        "members": {m["id"]: m["name"] for m in store.members(include_bots=True)},
        "jobs": jobs.latest("plane", [r["id"] for r in waiting]),
        "where": linking.Where(),
    }
    return {"dry_run": dry_run(pull.config()), "configured": pull.configured(),
            "waiting": [_view(r, ctx) for r in waiting], "sent": [_view(r, ctx) for r in sent]}


def count() -> int:
    """How many pushes need you (the sidebar's badge)."""
    return db.one(f"SELECT count(*) AS n FROM plane_pushes WHERE status IN {NEEDS_YOU}")["n"]


def view(push_id: str) -> dict:
    found = outbox()
    return next((p for p in found["waiting"] + found["sent"] if p["id"] == push_id), None) or {"id": push_id,
                                                                                            "status": _get(push_id)["status"]}
