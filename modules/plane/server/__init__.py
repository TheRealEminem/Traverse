"""Plane: the connection to the team's Plane workspace. Traverse's own module (D5), never shared with other apps.

It reads Plane (PLAN.md §3.4): a recurring pull mirrors the chosen projects' items, states, labels and cycles and the
workspace's members into plane_* tables; the Team view shows who's on what; and the members join the host's people
directory, with you as core:me. Linking (chunk 6, linking.py) ties Plane projects to Traverse projects and brings items
in as linked tasks that follow Plane, through the shared work.* contracts. And it sends to Plane only what you
approve (chunk 7, push.py): your changes to linked tasks, field by field, after checking nobody changed them there
meanwhile, new tasks in linked projects, and your updates as new comments on linked items (chunk 12). It never deletes
anything in Plane, and never edits a comment (§3.1, §3.3). Claude can read the team's workload and the outbox through
the host's MCP server (tools.py), and never send. Every pull keeps a log of what changed (plane_changes), which feeds its
part of the day's briefing, Muster's "what moved" (briefing.py).
"""
from core.server import contracts
from core.server.module import Module

from . import briefing, linking, people, pull, push, routes, store, tools

SETTING_KEYS = {"plane.personal_api_key", "plane.workspace_slug", "plane.base_url", "plane.projects"}


def _deleted(payload: dict) -> None:
    """contracts.ITEM_DELETED: a linked Traverse project is unlinked; a task's waiting changes are forgotten."""
    linking.local_deleted(payload)
    push.local_deleted(payload)


def _settings_changed(payload: dict) -> None:
    """A new key, workspace, server or choice of projects: read Plane again now rather than in a few minutes."""
    if SETTING_KEYS & set(payload.get("keys") or []) and pull.configured():
        pull.pull_now()


MODULE = Module(
    id="plane",
    name="Plane",
    router=routes.router,
    migrations=store.MIGRATIONS,
    settings={
        # A personal API key (Plane → Profile settings → Personal access tokens). Write-only: the host never sends a
        # setting ending in _api_key back to the page. (Plain "api_key" wouldn't be a secret to the host.)
        "personal_api_key": "",
        "workspace_slug": "",                   # the part after app.plane.so/ in the address, "cold-connect"
        "base_url": "https://api.plane.so",     # Plane Cloud; a self-hosted Plane's own address otherwise
        "projects": [],                         # the Plane project ids to mirror
        "me": "",                               # the member who is you; empty: whoever the API key belongs to
        "pull_minutes": 5,                      # 0: only when you press "Pull now"
        # Send checks against Plane and says what it would write, but writes nothing (§3.3, rule 8). On until you
        # turn it off, so the first sends are trials.
        "dry_run": True,
    },
    choices={"pull_minutes": (0, 2, 5, 15, 30)},
    jobs={"pull": pull.pull, push.KIND: push.send},
    lanes={"pull": "cloud", push.KIND: "interactive"},    # a push is something you're waiting for
    recurring={"pull": pull.every},
    subscribe={"core.settings.changed": _settings_changed, contracts.ITEM_DELETED: _deleted,
               contracts.WORK_SHARE_REQUESTED: push.requested, contracts.WORK_COMMENT_REQUESTED: push.comment_requested},
    search=store.search,
    describe=store.describe,
    export=store.export,
    count=store.count_in,
    people=people.find,
    tools=tools.TOOLS,
    brief=briefing.brief,
)
