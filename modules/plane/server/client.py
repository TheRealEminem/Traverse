"""A small, read-only client for Plane's REST API (https://developers.plane.so).

It can only read. Every request goes through `_get`, which sends GET and nothing else, and there is no method that
creates, changes, archives or deletes anything: Traverse never deletes in Plane (PLAN.md §3.3, rule 1), and in this
chunk it doesn't write at all. tests/test_client.py fails if a writing method or verb ever appears here.

Plane signs requests in with a personal API key in the X-API-Key header. Lists come back a page at a time (cursor
and per_page, at most 100) and are followed to the end. Plane allows 60 requests a minute per key: a 429 waits for
X-RateLimit-Reset (or backs off) and tries again, and running out of the minute's allowance waits before the next.
Errors are raised as PlaneError with a sentence a person can act on.
"""
import logging
import time
from typing import Callable, Iterator
from urllib.parse import urlparse

import httpx

log = logging.getLogger("plane.client")

CLOUD_API = "https://api.plane.so"
CLOUD_WEB = "https://app.plane.so"
PER_PAGE = 100
MAX_PAGES = 500                 # 50,000 rows: far past any real workspace, but never an endless loop
MAX_TRIES = 5                   # per request, for rate limits and Plane's own hiccups
MAX_WAIT = 65.0                 # seconds; Plane's window is a minute


class PlaneError(Exception):
    """Something Plane said no to, or couldn't be reached. The message is for the screen."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def web_url(base_url: str) -> str:
    """Where people open Plane in a browser: Plane Cloud's app for its API, the same server for a self-hosted one."""
    base = (base_url or CLOUD_API).rstrip("/")
    return CLOUD_WEB if urlparse(base).netloc == urlparse(CLOUD_API).netloc else base


class PlaneClient:
    def __init__(self, base_url: str, api_key: str, workspace: str, *, transport: httpx.BaseTransport | None = None,
                 sleep: Callable[[float], None] = time.sleep, timeout: float = 20.0):
        if not api_key:
            raise PlaneError("Add your Plane API key in Settings → Plane first.")
        if not (workspace or "").strip():
            raise PlaneError("Add your Plane workspace in Settings → Plane first.")
        self.base_url = (base_url or CLOUD_API).rstrip("/")
        self.workspace = workspace.strip().strip("/")
        self._sleep = sleep
        self._http = httpx.Client(base_url=self.base_url, transport=transport, timeout=timeout,
                                  headers={"X-API-Key": api_key, "Accept": "application/json"})
        self.requests = 0       # how many GETs this client made (shown after a pull, handy against the rate limit)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "PlaneClient":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    # ── What Traverse reads ─────────────────────────────────────────────

    def me(self) -> dict:
        """The person the API key belongs to (Dale, signed in as himself)."""
        return self._get("/api/v1/users/me/")

    def projects(self) -> list[dict]:
        return list(self._pages(self._ws("projects/")))

    def members(self) -> list[dict]:
        """Everyone in the workspace (Plane sends this as one list, not pages)."""
        return list(self._pages(self._ws("members/")))

    def project_members(self, project_id: str) -> list[dict]:
        return list(self._pages(self._ws(f"projects/{project_id}/members/")))

    def states(self, project_id: str) -> list[dict]:
        return list(self._pages(self._ws(f"projects/{project_id}/states/")))

    def labels(self, project_id: str) -> list[dict]:
        return list(self._pages(self._ws(f"projects/{project_id}/labels/")))

    def cycles(self, project_id: str) -> list[dict]:
        return list(self._pages(self._ws(f"projects/{project_id}/cycles/"), {"cycle_view": "all"}))

    def work_items(self, project_id: str) -> list[dict]:
        return list(self._pages(self._ws(f"projects/{project_id}/work-items/")))

    # ── Paging, rate limits and errors ──────────────────────────────────

    def _ws(self, rest: str) -> str:
        return f"/api/v1/workspaces/{self.workspace}/{rest}"

    def _pages(self, path: str, params: dict | None = None) -> Iterator[dict]:
        """Every row of a list, following Plane's cursor to the end. A plain list (members) is one page. A row seen on
        an earlier page (a list that shifted while it was read) comes once."""
        cursor, seen = None, set()
        for _ in range(MAX_PAGES):
            query = {**(params or {}), "per_page": PER_PAGE, **({"cursor": cursor} if cursor else {})}
            page = self._get(path, query)
            rows = page if isinstance(page, list) else page.get("results") or []
            for row in rows:
                key = row.get("id") if isinstance(row, dict) else None
                if key is None or key not in seen:
                    seen.add(key)
                    yield row
            if isinstance(page, list):
                return
            following = page.get("next_cursor")
            if not page.get("next_page_results") or not following or following == cursor:
                return
            cursor = following
        raise PlaneError(f"Plane kept sending more pages of {path} than Traverse expected. Try again later.")

    def _get(self, path: str, params: dict | None = None):
        """The one place a request leaves Traverse for Plane. It is always a GET."""
        for attempt in range(1, MAX_TRIES + 1):
            try:
                r = self._http.get(path, params=params)
            except httpx.TimeoutException as e:
                if attempt < MAX_TRIES:
                    self._sleep(self._backoff(attempt))
                    continue
                raise PlaneError(f"Plane at {self.base_url} didn't answer in time. Try again in a moment.") from e
            except httpx.HTTPError as e:
                raise PlaneError(f"Couldn't reach Plane at {self.base_url}. Check the address in Settings → Plane "
                                 f"and that this Mac is online.") from e
            self.requests += 1
            if r.status_code == 429 or r.status_code >= 500:
                if attempt < MAX_TRIES:
                    wait = self._retry_after(r) if r.status_code == 429 else self._backoff(attempt)
                    log.info("Plane said %s for %s; waiting %.1fs", r.status_code, path, wait)
                    self._sleep(wait)
                    continue
            if r.status_code >= 400:
                raise self._error(r, path)
            self._pace(r)
            try:
                return r.json()
            except ValueError as e:
                raise PlaneError(f"Plane sent something that isn't JSON for {path}. Is {self.base_url} a Plane API "
                                 f"address?", r.status_code) from e
        raise PlaneError("Plane is still busy. Try again in a few minutes.")  # (the loop always returns or raises)

    @staticmethod
    def _backoff(attempt: int) -> float:
        return min(MAX_WAIT, 2.0 ** attempt)

    @staticmethod
    def _retry_after(r: httpx.Response) -> float:
        """How long Plane asks us to wait: Retry-After, or until X-RateLimit-Reset (epoch seconds), or a minute."""
        try:
            if "Retry-After" in r.headers:
                return max(1.0, min(MAX_WAIT, float(r.headers["Retry-After"])))
            if "X-RateLimit-Reset" in r.headers:
                return max(1.0, min(MAX_WAIT, float(r.headers["X-RateLimit-Reset"]) - time.time() + 1))
        except ValueError:
            pass
        return 60.0

    def _pace(self, r: httpx.Response) -> None:
        """Out of requests for this minute: wait for the window to reset instead of earning a 429."""
        try:
            remaining = int(r.headers.get("X-RateLimit-Remaining", "1"))
        except ValueError:
            return
        if remaining <= 0:
            self._sleep(self._retry_after(r))

    def _error(self, r: httpx.Response, path: str) -> PlaneError:
        detail = ""
        try:
            body = r.json()
            detail = str(body.get("detail") or body.get("error") or "") if isinstance(body, dict) else ""
        except ValueError:
            pass
        code = r.status_code
        if code == 401:
            message = "Plane didn't accept the API key. Make a new one in Plane (Profile settings → Personal access " \
                      "tokens) and paste it in Settings → Plane."
        elif code == 403:
            message = "Your Plane account isn't allowed to see that. Ask a workspace admin, or check the workspace " \
                      "in Settings → Plane."
        elif code == 404 and path.startswith(f"/api/v1/workspaces/{self.workspace}/") and path.count("/") <= 6:
            message = f"Plane has no workspace called “{self.workspace}” that this key can see. It's the part " \
                      f"after app.plane.so/ in your Plane address."
        elif code == 404:
            message = f"Plane couldn't find {path}. It may have been removed."
        elif code == 429:
            message = "Plane asked Traverse to slow down and is still busy. Try again in a minute."
        elif code >= 500:
            message = f"Plane had a problem ({code}). Try again in a few minutes."
        else:
            message = f"Plane said no ({code})."
        if detail and code not in (401, 429) and code < 500:
            message = f"{message} Plane said: “{detail[:200]}”"
        return PlaneError(message, code)
