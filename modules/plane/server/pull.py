"""plane/pull: read the team's Plane workspace into the mirror (store.py). Read-only toward Plane.

Every few minutes (Settings → Plane), and on "Pull now". It reads everything first and writes it in one
transaction, so a pull cut off half way writes nothing, and a pull of an unchanged workspace changes nothing. When
something changed, linked tasks are told what their items look like now (linking.publish_linked).
"""
import logging

from core.server import db, events, jobs, settings
from core.server.jobs import Job

from . import linking, store
from .client import PlaneClient, PlaneError

log = logging.getLogger("plane.pull")

TARGET = "scheduled"            # the schedule's target too, so "Pull now" and the clock never run two at once


def config() -> dict:
    return settings.section("plane")


def configured(cfg: dict | None = None) -> bool:
    cfg = cfg or config()
    return bool(cfg.get("personal_api_key") and cfg.get("workspace_slug"))


def client(cfg: dict | None = None, **kwargs) -> PlaneClient:
    """The one way the module makes a Plane client (tests replace it with one that talks to a fake Plane)."""
    cfg = cfg or config()
    return PlaneClient(cfg["base_url"], cfg["personal_api_key"], cfg["workspace_slug"], **kwargs)


def every() -> int:
    """Module.recurring: seconds between pulls, or 0 (paused) until Plane is set up or when pulls are manual."""
    cfg = config()
    return int(cfg.get("pull_minutes") or 0) * 60 if configured(cfg) else 0


def pull_now() -> str:
    """Queues a pull unless one is waiting or running already. Returns the job id."""
    db.execute("DELETE FROM core_jobs WHERE module = 'plane' AND kind = 'pull' AND target = ? AND status IN ('done', 'error')",
               (TARGET,))
    return jobs.enqueue("plane", "pull", TARGET)


def read(c: PlaneClient, mirror: list[str], stage=lambda text: None) -> dict:
    """Everything one pull reads, as rows for store.apply()."""
    stage("Reading the workspace")
    me = c.me()
    projects = [p for p in c.projects() if p.get("id")]
    try:
        members = c.members()
    except PlaneError as e:
        if e.status != 403:
            raise
        # A key that may not list the whole workspace: gather the members of the mirrored projects instead.
        members = [m for pid in mirror for m in c.project_members(pid)]
    known = {p["id"] for p in projects}
    chosen = [p for p in projects if p["id"] in set(mirror) & known]
    pulled = {}
    for n, p in enumerate(chosen, start=1):
        stage(f"Reading {p.get('name') or 'a project'} ({n} of {len(chosen)})")
        pid = p["id"]
        pulled[pid] = {
            "states": [store.state_row(s, pid) for s in c.states(pid)],
            "labels": [store.label_row(lb, pid) for lb in c.labels(pid)],
            "cycles": [store.cycle_row(cy, pid) for cy in c.cycles(pid)],
            "items": [store.item_row(i, pid) for i in c.work_items(pid)],
        }
    by_id = {}
    for m in members:
        row = store.member_row(m)
        by_id[row["id"]] = row
    return {"me": me, "projects": [store.project_row(p) for p in projects], "members": list(by_id.values()),
            "pulled": pulled}


def pull(job: Job) -> None:
    """The job handler. Safe to run twice: the second run of an unchanged workspace changes nothing."""
    cfg = config()
    if not configured(cfg):
        raise ValueError("Add your Plane API key and workspace in Settings → Plane first.")
    with client(cfg) as c:
        snapshot = read(c, list(cfg.get("projects") or []), job.stage)
        requests = c.requests
    job.stage("Saving")
    changed = store.apply(snapshot)
    me = snapshot["me"] or {}
    if me.get("id") and store.meta("me") != me["id"]:
        store.set_meta("me", me["id"])
    total = sum(changed.values())
    store.set_meta("last_pull", {"at": db.now(), "changed": total, "requests": requests,
                                 "projects": len(snapshot["pulled"])})
    log.info("Plane pull: %s rows changed in %s requests", total, requests)
    if total:
        events.publish("plane.mirror.changed", {"tables": {k: v for k, v in changed.items() if v}})
        job.stage("Updating linked tasks")
        linking.publish_linked()
    events.publish("plane.pulled", {"changed": total})
