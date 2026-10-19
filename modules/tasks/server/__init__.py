"""Tasks: all of your work, from anywhere. Projects with milestones, work items with subtasks and blockers, and
updates (since step 2; Traverse PLAN.md chunk 2). It listens for the shared "actions.found" contract, so any module
that finds action items (notes today, meetings tomorrow) feeds it without either knowing about the other, and it
links each task back to where it came from.
"""
from core.server import contracts
from core.server.module import Module

from . import hooks, routes, store

MODULE = Module(
    id="tasks",
    name="Tasks",
    router=routes.router,
    migrations=store.MIGRATIONS,
    subscribe={
        contracts.ACTIONS_FOUND: hooks.take_actions,
        contracts.ITEM_DELETED: hooks.source_deleted,
    },
    search=hooks.search,
    describe=hooks.describe,
    export=hooks.export,
    count=hooks.count,
)
