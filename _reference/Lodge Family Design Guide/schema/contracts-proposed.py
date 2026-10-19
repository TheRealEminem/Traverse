"""PROPOSED additions to core/server/contracts.py for the project app. Not built yet.

Today's file has two contracts, ACTIONS_FOUND and ITEM_DELETED. The project app needs three more agreements: a richer
action item (who and by when), a way to hear that two people became one, and a ref for "you". Each is added the way
contracts.py asks, because a second module now cares about the same thing.

Rule of thumb (ARCHITECTURE.md §8): an event is "this happened, for anyone"; a contract is an event whose meaning more
than one module shares. Payloads are plain dicts. These TypedDicts only document their shape.
"""
from typing import NotRequired, TypedDict

# ── Existing, extended ────────────────────────────────────────────────

ACTIONS_FOUND = "actions.found"


class ActionDetail(TypedDict, total=False):
    text: str               # the same text as in `items`
    owner_name: str         # who it's for, as written ("Ana")
    owner_ref: str          # who it's for, when the publisher knows the record ("crm:<id>", "core:me")
    due_on: str             # a calendar day, "YYYY-MM-DD", when one was said


class ActionsFound(TypedDict):
    source_ref: str                        # "<module>:<id>" of where they came from
    items: list[str]                       # each item's text, in order (unchanged: old listeners keep working)
    details: NotRequired[list[ActionDetail]]  # NEW, optional, same order as items. People's extraction already sees
                                           # owners and dates; passing them lets the project app pre-fill assignee and due date.


ITEM_DELETED = "item.deleted"


class ItemDeleted(TypedDict):
    ref: str                # People should start publishing this when a person, organization or meeting is deleted


# ── New ───────────────────────────────────────────────────────────────

# Two records turned out to be the same person (or organization), and one was folded into the other. Anything that
# stores the old ref (an assignee, an owner, a link) rewrites it to the new one. Published by People's merge.
PEOPLE_MERGED = "people.merged"


class PeopleMerged(TypedDict):
    from_ref: str           # "crm:<id>" that no longer exists
    into_ref: str           # "crm:<id>" that it became


# Whoever owns this copy of the app. Not an event: a ref every module can store, described by the host from the
# `core.your_name` setting. Where People is on, its `is_self` person is the same person, and the people directory
# (03-project-app-blueprint.md §6) returns this ref for them, so "assigned to me" means the same thing everywhere.
ME = "core:me"
