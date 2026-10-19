"""The plane API, mounted at /api/plane. Everything here reads; the only thing that reaches Plane is a GET."""
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from core.server import jobs

from . import pull, store, team
from .client import PlaneError, web_url

router = APIRouter()


def _job():
    return jobs.latest("plane", [pull.TARGET]).get(pull.TARGET)


@router.get("/status")
def status():
    """For Settings and the Team view's header: is Plane set up, when it was last read, and the pull's job."""
    cfg = pull.config()
    me = team.me_id()
    member = next((m for m in store.members(include_bots=True) if m["id"] == me), None) if me else None
    return {"configured": pull.configured(cfg), "workspace": cfg.get("workspace_slug") or "",
            "web_url": web_url(cfg.get("base_url") or ""), "me": member and {"id": member["id"], "name": member["name"]},
            "me_from_key": not cfg.get("me"), "last_pull": store.meta("last_pull"), "job": _job(),
            "counts": store.counts()}


@router.post("/test")
async def test_connection():
    """Settings → Plane → Test: reads who the key belongs to and the workspace's projects. Writes nothing to Plane;
    on success it queues a pull, so the project list in Settings fills in."""
    cfg = pull.config()

    def check():
        with pull.client(cfg) as c:
            me = c.me()
            return me, c.projects()

    try:
        me, projects = await run_in_threadpool(check)
    except PlaneError as e:
        raise HTTPException(502, str(e)) from e
    pull.pull_now()
    name = store.member_name(me) if me else "someone"
    n = len(projects)
    return {"message": f"Connected to {cfg['workspace_slug']} as {name}. {n} {'project' if n == 1 else 'projects'} "
                       f"to choose from.", "projects": n}


@router.post("/pull", status_code=202)
def pull_now():
    if not pull.configured():
        raise HTTPException(400, "Add your Plane API key and workspace in Settings → Plane first.")
    return {"job": pull.pull_now()}


@router.get("/projects")
def projects():
    """Plane's projects as of the last pull, with whether each is mirrored (Settings → Plane)."""
    chosen = set(pull.config().get("projects") or [])
    return [{**p, "mirrored": p["id"] in chosen} for p in store.projects()]


@router.get("/members")
def members():
    """The workspace's people (not its bots), for "Which member is you"."""
    return [{"id": m["id"], "name": m["name"], "display_name": m["display_name"], "email": m["email"]}
            for m in store.members() if m["is_active"]]


@router.get("/team")
def team_view():
    return {**team.rollup(), "job": _job()}
