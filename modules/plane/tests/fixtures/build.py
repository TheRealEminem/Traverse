"""Writes cold_connect.json: Plane's REST answers for a stand-in of the Cinder Labs workspace, for the tests.

The shapes are Plane's own, recorded on 2026-10-19 (projects, members, states, labels, cycles and work items, with
every field Plane sends, through Plane's MCP server, which reads the same API). The workspace is the real one as of
2026-10-18: the same projects, people, states, assignees, priorities and due dates, so the Team view's numbers can be
checked against what Plane showed that day (34 open: Dale 23, Mickey 5, Elijah 2, no one 4, leaving out the "Cold
Connect" demo project). Titles are invented, emails are example ones, and ids are made up (stable from run to run).

Run it again only to change the stand-in:  .venv/bin/python modules/plane/tests/fixtures/build.py
"""
import json
import uuid
from pathlib import Path

WS = "cold-connect"
WS_ID = "13d469b4-e3ad-45ef-8578-2fc80c7139b3"
NS = uuid.UUID("6f1c1c9e-0b7e-4c47-9a5e-5e3c1d7b2a10")


def uid(*parts) -> str:
    return str(uuid.uuid5(NS, "/".join(map(str, parts))))


MEMBERS = {   # key: (first, last, display, role, is_bot)
    "M": ("Dale", "Morgan", "dale", "owner", False),
    "E": ("Elijah", "Anderson-Justis", "eli", "member", False),
    "K": ("Mickey", "", "mickey", "member", False),
    "mcp": ("Plane MCP", "", "Plane MCP", "admin", True),
    "bot": ("Plane", "", "Plane", "admin", True),
}
ROLE = {"owner": 20, "admin": 20, "member": 15}

PROJECTS = [  # identifier, name, description
    ("OPERATIONS", "Operations", "All things to operate"),
    ("CUSTO", "Customer Relationships", "Where we track and develop our customer relationships and meetings"),
    ("INFRA", "Infrastructure", ""),
    ("SOFTWARE", "Software", ""),
    ("HARDWARE", "Hardware", ""),
    ("DALEETING", "Marketing", "All things marketing and design"),
    ("BD", "Business Development", ""),
    ("COLDC", "Cinder Labs", "Welcome to the Plane Demo Project!"),
]
STATES = [("Backlog", "backlog", "#60646C"), ("Todo", "unstarted", "#60646C"), ("In Progress", "started", "#F59E0B"),
          ("Done", "completed", "#46A758"), ("Cancelled", "cancelled", "#9AA4BC")]

# project, number, state group, assignee (M, E, K or -), priority, due date, parent number, title
ITEMS = [
    ("SOFTWARE", 5, "unstarted", "E", "high", "2026-10-13", None, "Share GitHub repos with Dale"),
    ("SOFTWARE", 4, "unstarted", "E", "medium", "2026-10-16", None, "Populate the demo site with data"),
    ("SOFTWARE", 3, "completed", "M", "medium", "2026-10-08", 2, "Connect the demo site through a Cloudflare tunnel"),
    ("SOFTWARE", 2, "completed", "E", "medium", "2026-10-07", None, "Stand up the demo site"),
    ("SOFTWARE", 1, "started", "M", "medium", None, None, "Alerting for temperature excursions"),
    ("OPERATIONS", 10, "unstarted", "M", "medium", "2026-10-16", None, "Renew the insurance policy"),
    ("OPERATIONS", 9, "unstarted", "M", "urgent", None, None, "File the quarterly tax return"),
    ("OPERATIONS", 8, "completed", "M", "none", None, None, "Set up the shared drive"),
    ("OPERATIONS", 7, "started", "M", "medium", None, None, "Bookkeeping for September"),
    ("OPERATIONS", 6, "completed", "K", "high", "2026-10-09", None, "Order shipping boxes"),
    ("OPERATIONS", 5, "completed", "M", "high", "2026-10-08", None, "Open the business bank account"),
    ("OPERATIONS", 4, "completed", "K", "low", None, None, "Inventory the spare sensors"),
    ("OPERATIONS", 3, "unstarted", "K", "low", None, None, "Tidy the workshop shelves"),
    ("OPERATIONS", 2, "backlog", "K", "medium", "2026-10-11", None, "Price out a label printer"),
    ("OPERATIONS", 1, "completed", "K", "medium", "2026-10-11", None, "Return the loaner multimeter"),
    ("HARDWARE", 4, "backlog", "-", "none", None, 2, "Test the enclosure seal"),
    ("HARDWARE", 3, "backlog", "M", "none", None, None, "Battery life under cold soak"),
    ("HARDWARE", 2, "backlog", "M", "none", None, None, "Enclosure revision C"),
    ("HARDWARE", 1, "backlog", "M", "none", None, None, "Choose the cellular modem"),
    ("DALEETING", 6, "unstarted", "M", "high", None, 3, "Write the case study draft"),
    ("DALEETING", 5, "unstarted", "M", "medium", None, 3, "Collect photos from the pilot"),
    ("DALEETING", 4, "unstarted", "K", "medium", "2026-10-11", None, "Refresh the one-pager"),
    ("DALEETING", 3, "unstarted", "K", "high", None, None, "Pilot case study"),
    ("DALEETING", 2, "completed", "M", "none", None, 1, "Pick the brand colors"),
    ("DALEETING", 1, "backlog", "K", "low", None, None, "Website refresh"),
    ("BD", 14, "started", "M", "none", "2026-10-07", None, "Send the grant letter of intent"),
    ("BD", 13, "started", "M", "none", None, 1, "Follow up with the cooperative"),
    ("BD", 12, "backlog", "M", "none", None, 1, "Map the distributors in the region"),
    ("BD", 11, "started", "M", "none", None, 6, "Budget for the pilot extension"),
    ("BD", 10, "backlog", "-", "none", None, 6, "Find a local installer"),
    ("BD", 9, "completed", "M", "none", None, 6, "Site visit notes"),
    ("BD", 8, "unstarted", "M", "none", None, 6, "Draft the pilot agreement"),
    ("BD", 7, "completed", "M", "none", None, 6, "Intro call with the clinic network"),
    ("BD", 6, "started", "M", "none", None, None, "Pilot extension"),
    ("BD", 5, "completed", "M", "none", None, None, "Pitch deck v2"),
    ("BD", 4, "started", "M", "none", None, None, "Investor update for October"),
    ("BD", 3, "completed", "M", "none", "2026-09-23", None, "Apply to the accelerator"),
    ("BD", 2, "started", "M", "none", None, None, "Partnership with the logistics company"),
    ("BD", 1, "started", "M", "none", None, None, "Cooperative partnership"),
    ("INFRA", 7, "backlog", "M", "none", None, None, "Move backups off the laptop"),
    ("INFRA", 6, "completed", "M", "none", None, 3, "Domain and DNS"),
    ("INFRA", 5, "started", "M", "none", None, 3, "Monitoring for the ingest server"),
    ("INFRA", 4, "completed", "M", "none", None, 3, "Provision the ingest server"),
    ("INFRA", 3, "unstarted", "M", "none", None, None, "Production environment"),
    ("INFRA", 2, "started", "M", "none", None, None, "Password manager for the team"),
    ("INFRA", 1, "completed", "M", "none", None, None, "Company email"),
    ("CUSTO", 3, "backlog", "-", "none", None, None, "Customer interview guide"),
    ("CUSTO", 2, "backlog", "-", "none", None, None, "Set up a simple CRM"),
    ("CUSTO", 1, "started", "M", "high", None, None, "Weekly check-in with the pilot site"),
    # The demo project Plane makes for a new workspace: left out of the mirror, so it must not count.
    ("COLDC", 7, "backlog", "M", "none", None, None, "Explore work items"),
    ("COLDC", 6, "backlog", "-", "none", None, None, "Try a cycle"),
    ("COLDC", 5, "started", "M", "medium", "2026-10-01", None, "Invite your team"),
    ("COLDC", 4, "started", "K", "low", None, None, "Customize your states"),
    ("COLDC", 3, "unstarted", "E", "none", None, None, "Create a page"),
    ("COLDC", 2, "completed", "M", "none", None, None, "Welcome to Plane"),
    ("COLDC", 1, "completed", "M", "none", None, None, "Set up your profile"),
]
LABELS = {"SOFTWARE": [("Demo", "#3B82F6")], "BD": [("Grant", "#10B981"), ("Pilot", "#F59E0B")]}
ITEM_LABELS = {("BD", 14): ["Grant"], ("BD", 6): ["Pilot"], ("BD", 11): ["Pilot"], ("SOFTWARE", 4): ["Demo"]}
CYCLES = {"BD": [("October push", "2026-10-06", "2026-10-24", "current")]}
ITEM_CYCLES = {("BD", 14): "October push", ("BD", 4): "October push", ("BD", 2): "October push"}


def page(results: list) -> dict:
    """Plane's list envelope, as one page of up to 100."""
    n = len(results)
    return {"grouped_by": None, "sub_grouped_by": None, "total_count": n, "next_cursor": "100:1:0",
            "prev_cursor": "100:-1:1", "next_page_results": False, "prev_page_results": False, "count": n,
            "total_pages": 1 if n else 0, "total_results": n, "extra_stats": None, "results": results,
            "total_groups": None, "next_group_offset": None, "sub_total_groups": None, "sub_next_group_offset": None}


def member(key: str) -> dict:
    first, last, display, role, bot = MEMBERS[key]
    email = (f"bot-{key}@plane.so" if bot else f"{display}@cold-connect.example")
    return {"id": uid("member", key), "first_name": first, "last_name": last, "email": email, "avatar": "",
            "avatar_url": None, "display_name": display, "role": ROLE[role], "role_slug": role, "is_active": True,
            "is_bot": bot}


def build() -> dict:
    me = member("M")
    out = {"/api/v1/users/me/": {k: me[k] for k in ("id", "first_name", "last_name", "email", "avatar", "avatar_url",
                                                     "display_name")},
           f"/api/v1/workspaces/{WS}/members/": [member(k) for k in ("mcp", "E", "K", "bot", "M")]}
    projects = []
    for ident, name, desc in PROJECTS:
        pid = uid("project", ident)
        projects.append({"id": pid, "identifier": ident, "name": name, "cover_image": None, "icon_prop": None,
                         "emoji": None, "description": desc, "cover_image_url": None, "archived_at": None})
        base = f"/api/v1/workspaces/{WS}/projects/{pid}"
        states = {group: uid("state", ident, group) for _, group, _ in STATES}
        out[f"{base}/states/"] = page([
            {"id": states[group], "created_at": "2026-09-20T16:17:51.456859Z", "updated_at": "2026-09-20T16:17:51.456870Z",
             "deleted_at": None, "name": sname, "description": "", "color": color, "sequence": (n + 1) * 10000 + 5000,
             "group": group, "is_triage": False, "default": group == "backlog", "external_source": None,
             "external_id": None, "created_by": me["id"], "updated_by": None, "project": pid, "workspace": WS_ID,
             "deleted_by": None} for n, (sname, group, color) in enumerate(STATES)])
        labels = {lname: uid("label", ident, lname) for lname, _ in LABELS.get(ident, [])}
        out[f"{base}/labels/"] = page([
            {"id": labels[lname], "name": lname, "color": color, "description": "", "parent": None, "sort_order": 65535,
             "project": pid, "workspace": WS_ID, "external_source": None, "external_id": None}
            for lname, color in LABELS.get(ident, [])])
        cycles = {cname: uid("cycle", ident, cname) for cname, *_ in CYCLES.get(ident, [])}
        out[f"{base}/cycles/"] = page([
            {"id": cycles[cname], "name": cname, "description": "", "start_date": f"{start}T00:00:00Z",
             "end_date": f"{end}T23:59:59Z", "status": status, "owned_by": me["id"], "project": pid,
             "workspace": WS_ID, "archived_at": None} for cname, start, end, status in CYCLES.get(ident, [])])
        items = []
        for proj, seq, group, who, priority, due, parent, title in ITEMS:
            if proj != ident:
                continue
            done = group in ("completed", "cancelled")
            created = f"2026-10-{max(1, 18 - seq):02d}T17:23:35.100719Z"
            items.append({
                "id": uid("item", ident, seq), "type_id": None, "created_at": created, "updated_at": created,
                "deleted_at": None, "point": None, "name": title,
                "description_html": f"<p class=\"editor-paragraph-block\">{title}.</p>",
                "description_stripped": f"{title}.", "description_binary": None, "priority": priority,
                "start_date": None, "target_date": due, "sequence_id": seq, "sort_order": 65535 + seq * 1000,
                "completed_at": created if done else None, "archived_at": None, "is_draft": False,
                "external_source": None, "external_id": None, "created_by": me["id"], "updated_by": None,
                "project": pid, "workspace": WS_ID, "parent": uid("item", ident, parent) if parent else None,
                "state": states[group], "estimate_point": None, "type": None, "deleted_by": None,
                "cycle_id": cycles.get(ITEM_CYCLES.get((ident, seq), "")), "created_via": None, "updated_via": None,
                "last_activity_at": created, "state_group": group,
                "assignees": [] if who == "-" else [uid("member", who)],
                "labels": [labels[lb] for lb in ITEM_LABELS.get((ident, seq), [])],
            })
        out[f"{base}/work-items/"] = page(items)
    out[f"/api/v1/workspaces/{WS}/projects/"] = page(projects)
    return out


if __name__ == "__main__":
    target = Path(__file__).with_name("cold_connect.json")
    target.write_text(json.dumps(build(), indent=1, sort_keys=True) + "\n")
    print(f"Wrote {target}")
