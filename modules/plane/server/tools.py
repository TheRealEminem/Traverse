"""What Claude may ask of the plane module, through the host's MCP server (core/server/mcp.py): the team's workload, read
from Traverse's copy of Plane, and what waits in the outbox.

Both only read, and neither talks to Plane. Claude proposes a push the way you do, by asking to send a task
(tasks_propose_send, which publishes work.share_requested): `push.requested` parks it as Needs you, and only your Send
in the outbox writes anything. While a tool runs the host refuses to start waiting work, and the client won't write.
"""
from core.server.mcp import Tool

from . import push, team

STATUS = {"waiting": "Waiting for you to send it", "stopped": "Stopped: Plane changed since; choose Plane's or yours",
          "failed": "Didn't go through; Send tries again", "sending": "Sending"}
NOBODY = ("no one", "nobody", "none", "unassigned")
MAX_ITEMS = 40


def _named(found: list[dict], wanted: str, what: str, names) -> dict:
    """The one thing in found whose name (any of names(thing)) is wanted, or a part of it."""
    w = wanted.casefold()
    for match in ([f for f in found if w in (n.casefold() for n in names(f) if n)],
                  [f for f in found if any(w in n.casefold() for n in names(f) if n)]):
        if len(match) == 1:
            return match[0]
        if match:
            raise ValueError(f"“{wanted}” could be {', '.join(names(m)[0] for m in match)}. Say which.")
    raise ValueError(f"No {what} called “{wanted}”. There's {', '.join(names(f)[0] for f in found)}.")


def _item(i: dict) -> dict:
    out = {"key": i["key"], "name": i["name"], "project": i["project"], "state": i["state"]["name"]}
    if i["priority"] and i["priority"] != "none":
        out["priority"] = i["priority"]
    if i["target_date"]:
        out["due"] = i["target_date"]
    if i["past_due"]:
        out["past_due"] = True
    out["assignees"] = [a["name"] + (" (you)" if a["is_me"] else "") for a in i["assignees"]] or ["No one"]
    out["url"] = i["url"]
    if i["task"]:
        out["in_traverse"] = {"ref": i["task"]["ref"], "href": i["task"]["href"]}
    return out


def workload(args: dict) -> dict:
    r = team.rollup()
    if not r["configured"]:
        raise ValueError("Plane isn't set up in Traverse yet: the API key and workspace go in Settings → Plane.")
    if not r["projects_chosen"]:
        raise ValueError("No Plane projects are chosen to read yet (Settings → Plane).")
    items = r["items"]
    shown = "Past due"
    if args.get("person"):
        wanted = args["person"].strip()
        if wanted.casefold() in ("me", "myself", "i", "you"):
            who = next((p for p in r["people"] if p["is_me"]), None)
            if who is None:
                raise ValueError("Traverse doesn't know which Plane member is you yet (Settings → Plane).")
        elif wanted.casefold() in NOBODY:
            who = next((p for p in r["people"] if p["id"] is None), {"id": None, "name": "No one"})
        else:
            who = _named([p for p in r["people"] if p["id"]], wanted, "one", lambda p: [p["name"], p["display_name"]])
        items = [i for i in items if (who["id"] in [a["id"] for a in i["assignees"]]) or (who["id"] is None and not i["assignees"])]
        shown = f"{who['name']}'s open items" if who["id"] else "Open items with no one on them"
    if args.get("project"):
        where = _named(r["projects"], args["project"].strip(), "project", lambda p: [p["name"], p["identifier"]])
        items = [i for i in items if i["project_id"] == where["id"]]
        shown = f"{shown} in {where['name']}" if args.get("person") else f"Open items in {where['name']}"
    if not args.get("person") and not args.get("project"):
        items = [i for i in items if i["past_due"]]
    return {
        "as_of": r["pulled_at"], "today": r["today"], "workspace": r["workspace"], "totals": r["totals"],
        "people": [{"name": p["name"] + (" (you)" if p["is_me"] else ""), "open": p["open"], "past_due": p["past_due"],
                    "due_soon": p["due_soon"], "in_progress": p["by_group"]["started"],
                    "to_do": p["by_group"]["unstarted"], "backlog": p["by_group"]["backlog"] + p["by_group"]["triage"]}
                   for p in r["people"]],
        "projects": [{"key": p["identifier"], "name": p["name"], "open": p["open"], "past_due": p["past_due"],
                      "unassigned": p["unassigned"], **({"in_traverse": p["linked"]["title"]} if p["linked"] else {})}
                     for p in r["projects"]],
        "items_shown": shown, "items": [_item(i) for i in items[:MAX_ITEMS]],
        **({"more_items": len(items) - MAX_ITEMS} if len(items) > MAX_ITEMS else {}),
        "note": "From Traverse's copy of Plane, read at as_of (it reads again every few minutes). Open in Plane: url.",
        "href": "#/plane/team",
    }


def outbox(args: dict) -> dict:
    box = push.outbox()
    waiting = []
    for p in box["waiting"]:
        fields = []
        for f in p["fields"]:
            row = {"field": f["label"], "in_plane_now": f.get("before"), "will_be": f.get("after"), "included": f["include"]}
            if f["skip"]:
                row["cannot_send"] = f["skip"]
            if f["theirs"] is not None:
                row.update(plane_changed_it_to=f["theirs"], yours=f["yours"])
            fields.append(row)
        waiting.append({
            "task": p["task"] and p["task"]["title"],
            "plane_item": f"{p['item']['key']} {p['item']['name']}" if p["item"] else None,
            "what": "Add it to Plane" if p["kind"] == "create" else "Change it in Plane",
            "project": p["project"] and p["project"]["name"], "status": STATUS.get(p["status"], p["status"]),
            **({"note": p["note"]} if p["note"] else {}), "fields": fields})
    out = {"dry_run": box["dry_run"], "waiting": waiting, "sent_lately": len(box["sent"]), "href": "#/plane/outbox",
           "note": "Only the user can send these, from the outbox in Traverse."}
    if box["dry_run"]:
        out["note"] += " Dry run is on: Send checks against Plane and says what it would write, but writes nothing."
    return out


TOOLS = [
    Tool(
        name="team_workload", title="Team workload", handler=workload,
        description="Who has what open in the team's Plane, from Traverse's copy of it: totals, each person (open, past "
                    "due, due in the next week, in progress, to do), each project, and items. With person (a name, me, "
                    "or no one) or project (a name or key like SOFTWARE), it lists those open items; with neither, the "
                    "past-due ones. Reads Traverse's copy only; never Plane itself.",
        params={"person": {"type": "string", "description": "A teammate's name, me, or no one."},
                "project": {"type": "string", "description": "A Plane project's name or key (SOFTWARE)."}},
    ),
    Tool(
        name="outbox", title="What waits to go to Plane", handler=outbox,
        description="What waits in Traverse's outbox for the user to send to Plane, field by field (what Plane has now "
                    "and what it will have), and whether dry run is on. Read only: only the user sends, from the app. "
                    "To propose something for it, use tasks_propose_send.",
    ),
]
