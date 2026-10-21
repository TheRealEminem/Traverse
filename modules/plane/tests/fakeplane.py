"""A fake Plane for the plane module's tests: it answers from fixtures/cold_connect.json (Plane's own shapes) through
httpx's MockTransport, pages lists the way Plane does, records every request, and can be told to fail.

It takes the writes Plane's API takes for work items: PATCH one (only the fields sent change; a list sent replaces
the list, as Plane does), POST a new one, and POST a comment on one (listed again at the same address). Each is
recorded in `writes` as (method, path, body). Anything else that would change something (DELETE, PUT) is refused with
405 and recorded too, so a test can show it never happens."""
import copy
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from core.server import db
from modules.plane.server import store
from modules.plane.server.client import PlaneClient

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "cold_connect.json").read_text())
WS = "cold-connect"
PROJECTS = {p["identifier"]: p["id"] for p in FIXTURE[f"/api/v1/workspaces/{WS}/projects/"]["results"]}
MEMBERS = {m["display_name"]: m["id"] for m in FIXTURE[f"/api/v1/workspaces/{WS}/members/"]}
REAL_PROJECTS = [pid for ident, pid in PROJECTS.items() if ident != "COLDC"]   # everything but Plane's demo project


class FakePlane:
    def __init__(self):
        self.data = copy.deepcopy(FIXTURE)
        self.requests: list[httpx.Request] = []
        self.page_size = 100                  # Plane's own cap; lower it to make lists come in several pages
        self.failures: dict[str, list] = {}   # path -> responses to give before answering normally
        self.slept: list[float] = []
        self.writes: list[tuple[str, str, dict]] = []
        self.lose_next_answer = False         # the next POST makes its item, then its answer never arrives
        self._clock = datetime.now(timezone.utc)      # Plane keeps the real time (give or take its clock)
        self.transport = httpx.MockTransport(self.handle)

    # Changing what "Plane" holds
    def items(self, ident: str) -> list[dict]:
        return self.data[f"/api/v1/workspaces/{WS}/projects/{PROJECTS[ident]}/work-items/"]["results"]

    def item(self, key: str) -> dict:
        ident, _, seq = key.rpartition("-")
        return next(i for i in self.items(ident) if i["sequence_id"] == int(seq))

    def now(self) -> str:
        """Plane's updated_at for the next change: a second later each time, in Plane's format."""
        self._clock += timedelta(seconds=1)
        return self._clock.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def edit(self, key: str, **changes) -> dict:
        """A teammate changes an item in Plane."""
        item = self.item(key)
        item.update(changes, updated_at=self.now())
        return item

    def item_path(self, key: str) -> str:
        item = self.item(key)
        return f"/api/v1/workspaces/{WS}/projects/{item['project']}/work-items/{item['id']}/"

    def fail(self, path: str, *responses) -> None:
        """The next requests to `path` ("PATCH <path>" for one verb only) get these: an int status, an (int, headers)
        pair, or an exception."""
        self.failures.setdefault(path, []).extend(responses)

    def client(self, api_key: str = "plane_api_test", workspace: str = WS, **kwargs) -> PlaneClient:
        return PlaneClient("https://api.plane.so", api_key, workspace, transport=self.transport,
                           sleep=self.slept.append, **kwargs)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.headers.get("X-API-Key") != "plane_api_test":
            return httpx.Response(401, json={"detail": "Invalid API key"})
        queued = self.failures.get(f"{request.method} {path}") or self.failures.get(path)
        if queued:
            failure = queued.pop(0)
            if isinstance(failure, Exception):
                raise failure
            status, headers = failure if isinstance(failure, tuple) else (failure, {})
            return httpx.Response(status, headers=headers, json={"detail": "Simulated failure"})
        if request.method in ("PATCH", "POST"):
            return self._write(request)
        if request.method != "GET":
            self.writes.append((request.method, path, {}))
            return httpx.Response(405, json={"detail": f'Method "{request.method}" not allowed.'})
        if path.endswith("/comments/") and path not in self.data:
            if self._one(path.removesuffix("comments/")) is None:
                return httpx.Response(404, json={"detail": "Not found."})
            return httpx.Response(200, json=self._page({"results": []}, request))
        if path not in self.data:
            found = self._one(path)
            return httpx.Response(200, json=found) if found else httpx.Response(404, json={"detail": "Not found."})
        body = self.data[path]
        if not isinstance(body, dict) or "results" not in body:
            return httpx.Response(200, json=body)
        return httpx.Response(200, json=self._page(body, request))

    WRITABLE = {"name", "description_html", "state", "priority", "start_date", "target_date", "assignees", "labels"}

    def _one(self, path: str) -> dict | None:
        """GET .../work-items/<id>/: one item."""
        listing, _, item_id = path.rstrip("/").rpartition("/")
        rows = self.data.get(listing + "/")
        if not isinstance(rows, dict) or not listing.endswith("/work-items"):
            return None
        return next((i for i in rows["results"] if i["id"] == item_id), None)

    def comments(self, key: str) -> list[dict]:
        """The comments on an item, as "Plane" holds them."""
        return (self.data.get(self.item_path(key) + "comments/") or {"results": []})["results"]

    def _write(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        body = json.loads(request.content or b"{}")
        self.writes.append((request.method, path, body))
        if request.method == "POST" and path.endswith("/comments/"):
            return self._comment(path, body, request)
        unknown = set(body) - self.WRITABLE
        if unknown:
            return httpx.Response(400, json={"error": f"Can't set {', '.join(sorted(unknown))}"})
        if body.get("priority", "none") not in ("none", "low", "medium", "high", "urgent"):
            return httpx.Response(400, json={"priority": ["Not a valid choice."]})
        if request.method == "PATCH":
            item = self._one(path)
            if item is None:
                return httpx.Response(404, json={"detail": "Not found."})
            item.update(body, updated_at=self.now())
            if "state" in body:
                item["state_group"] = self._group(item["project"], body["state"])
            return httpx.Response(200, json=item)
        rows = self.data.get(path)
        if not isinstance(rows, dict) or not path.endswith("/work-items/"):
            return httpx.Response(404, json={"detail": "Not found."})
        if not (body.get("name") or "").strip():
            return httpx.Response(400, json={"name": ["This field is required."]})
        project = path.split("/projects/")[1].split("/")[0]
        states = self.data[f"/api/v1/workspaces/{WS}/projects/{project}/states/"]["results"]
        stamp = self.now()
        item = {**(copy.deepcopy(rows["results"][0]) if rows["results"] else {}), "id": str(uuid.uuid4()),
                "project": project, "sequence_id": max((i["sequence_id"] for i in rows["results"]), default=0) + 1,
                "name": "", "description_html": "<p></p>", "priority": "none", "start_date": None, "target_date": None,
                "assignees": [], "labels": [], "parent": None, "cycle_id": None, "archived_at": None,
                "completed_at": None, "is_draft": False, "created_by": FIXTURE["/api/v1/users/me/"]["id"],
                "created_at": stamp, "updated_at": stamp,
                "state": next(s["id"] for s in states if s.get("default")) if any(s.get("default") for s in states)
                else states[0]["id"]}
        item.update(body)
        item["state_group"] = self._group(project, item["state"])
        rows["results"].append(item)
        if self.lose_next_answer:
            self.lose_next_answer = False
            raise httpx.ReadTimeout("The answer was lost", request=request)
        return httpx.Response(201, json=item)

    COMMENT_FIELDS = {"comment_html", "comment_json", "access", "external_source", "external_id", "parent"}

    def _comment(self, path: str, body: dict, request: httpx.Request) -> httpx.Response:
        """POST .../work-items/<id>/comments/: a new comment, by whoever the key belongs to."""
        if self._one(path.removesuffix("comments/")) is None:
            return httpx.Response(404, json={"detail": "Not found."})
        unknown = set(body) - self.COMMENT_FIELDS
        if unknown:
            return httpx.Response(400, json={"error": f"Can't set {', '.join(sorted(unknown))}"})
        if not (body.get("comment_html") or "").strip():
            return httpx.Response(400, json={"comment_html": ["This field is required."]})
        stamp = self.now()
        me = FIXTURE["/api/v1/users/me/"]["id"]
        comment = {"id": str(uuid.uuid4()), "comment_html": body["comment_html"], "comment_json": {},
                   "external_source": body.get("external_source"), "external_id": body.get("external_id"),
                   "access": body.get("access", "INTERNAL"), "actor": me, "created_by": me, "created_at": stamp,
                   "updated_at": stamp}
        self.data.setdefault(path, {"results": []})["results"].append(comment)
        if self.lose_next_answer:
            self.lose_next_answer = False
            raise httpx.ReadTimeout("The answer was lost", request=request)
        return httpx.Response(201, json=comment)

    def _group(self, project: str, state_id: str) -> str | None:
        states = self.data[f"/api/v1/workspaces/{WS}/projects/{project}/states/"]["results"]
        return next((s["group"] for s in states if s["id"] == state_id), None)

    def _page(self, body: dict, request: httpx.Request) -> dict:
        """Plane's cursor paging: "<per_page>:<page>:<is_prev>"."""
        rows = body["results"]
        size = min(int(request.url.params.get("per_page", 20)), 100, self.page_size)
        cursor = request.url.params.get("cursor")
        n = int(cursor.split(":")[1]) if cursor else 0
        chunk = rows[n * size:(n + 1) * size]
        more = (n + 1) * size < len(rows)
        return {**body, "count": len(chunk), "results": chunk, "total_results": len(rows), "total_count": len(rows),
                "total_pages": -(-len(rows) // size), "next_cursor": f"{size}:{n + 1}:0", "prev_cursor": f"{size}:{n - 1}:1",
                "next_page_results": more, "prev_page_results": n > 0}


def mirror_rows() -> dict[str, list[dict]]:
    """Everything the mirror holds, for comparing before and after."""
    return {t: db.query(f"SELECT * FROM {t} ORDER BY id") for t in store.MIRROR_TABLES}
