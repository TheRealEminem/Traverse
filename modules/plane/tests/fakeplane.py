"""A fake Plane for the plane module's tests: it answers from fixtures/cold_connect.json (Plane's own shapes) through
httpx's MockTransport, pages lists the way Plane does, records every request, and can be told to fail."""
import copy
import json
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
        self.transport = httpx.MockTransport(self.handle)

    # Changing what "Plane" holds
    def items(self, ident: str) -> list[dict]:
        return self.data[f"/api/v1/workspaces/{WS}/projects/{PROJECTS[ident]}/work-items/"]["results"]

    def item(self, key: str) -> dict:
        ident, _, seq = key.rpartition("-")
        return next(i for i in self.items(ident) if i["sequence_id"] == int(seq))

    def fail(self, path: str, *responses) -> None:
        """The next requests to `path` get these: an int status, an (int, headers) pair, or an exception."""
        self.failures.setdefault(path, []).extend(responses)

    def client(self, api_key: str = "plane_api_test", workspace: str = WS, **kwargs) -> PlaneClient:
        return PlaneClient("https://api.plane.so", api_key, workspace, transport=self.transport,
                           sleep=self.slept.append, **kwargs)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.headers.get("X-API-Key") != "plane_api_test":
            return httpx.Response(401, json={"detail": "Invalid API key"})
        queued = self.failures.get(path)
        if queued:
            failure = queued.pop(0)
            if isinstance(failure, Exception):
                raise failure
            status, headers = failure if isinstance(failure, tuple) else (failure, {})
            return httpx.Response(status, headers=headers, json={"detail": "Simulated failure"})
        if path not in self.data:
            return httpx.Response(404, json={"detail": "Not found."})
        body = self.data[path]
        if not isinstance(body, dict) or "results" not in body:
            return httpx.Response(200, json=body)
        return httpx.Response(200, json=self._page(body, request))

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
