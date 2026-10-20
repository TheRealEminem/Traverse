"""Plane: the connection to the team's Plane workspace. Traverse's own module (D5), never shared with other apps.

It only reads Plane (PLAN.md §3.4): a recurring pull mirrors the chosen projects' items, states, labels and cycles and
the workspace's members into plane_* tables; the Team view shows who's on what; and the members join the host's people
directory, with you as core:me. Linking (chunk 6, linking.py) ties Plane projects to Traverse projects and brings items
in as linked tasks that follow Plane, through the shared work.* contracts. Nothing is ever written to Plane from here.
"""
from core.server import contracts
from core.server.module import Module

from . import linking, people, pull, routes, store

SETTING_KEYS = {"plane.personal_api_key", "plane.workspace_slug", "plane.base_url", "plane.projects"}


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
    },
    choices={"pull_minutes": (0, 2, 5, 15, 30)},
    jobs={"pull": pull.pull},
    lanes={"pull": "cloud"},
    recurring={"pull": pull.every},
    subscribe={"core.settings.changed": _settings_changed, contracts.ITEM_DELETED: linking.local_deleted},
    search=store.search,
    describe=store.describe,
    export=store.export,
    count=store.count_in,
    people=people.find,
)
