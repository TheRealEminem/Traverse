"""Inbox: capture anything, the AI proposes work items, you review them (Traverse PLAN.md chunks 9 and 10).

Paste a thread, an email or notes, or bring in a .txt, .md or .eml file; with the setting on, meetings come in from
Trailmix too. The inbox/extract job reads each capture into proposals (who, by when, how urgent, and the sentence each
came from). What you accept is announced as the shared "actions.found" contract, and the tasks module files it into
the project the capture is linked to. The inbox never reads the tasks module's tables or calls its API: it finds
projects through the host's search and points at one with a link. Claude can put things in it too, with its own
proposals, through the host's MCP server (tools.py). Its part of the day's briefing (proposals waiting, meetings
from Trailmix) is in briefing.py.
"""
from core.server.module import Module

from . import briefing, extract, routes, store, tools, trailmix


MODULE = Module(
    id="inbox",
    name="Inbox",
    router=routes.router,
    migrations=store.MIGRATIONS,
    settings={"trailmix": False, "trailmix_url": "http://127.0.0.1:8765"},
    jobs={"extract": extract.extract, "trailmix": trailmix.check},
    recurring={"trailmix": trailmix.every},
    search=store.search,
    describe=store.describe,
    export=store.export,
    count=store.count,
    tools=tools.TOOLS,
    brief=briefing.brief,
)
