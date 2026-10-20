"""The Plane client: it reads (with paging, rate limits and readable errors), changes or adds work items when asked,
and cannot delete anything."""
import ast
import inspect
import json
import time
from pathlib import Path

import httpx
import pytest

from modules.plane.server import client as client_module
from modules.plane.server.client import PlaneClient, PlaneError, web_url

from modules.plane.tests.fakeplane import PROJECTS, WS, FakePlane

ITEMS = f"/api/v1/workspaces/{WS}/projects/{PROJECTS['BD']}/work-items/"
PROJECTS_PATH = f"/api/v1/workspaces/{WS}/projects/"
FORBIDDEN_CALLS = {"delete", "put", "request", "send", "stream", "build_request"}
DELETING_NAMES = ("delete", "remove", "archive", "unarchive", "destroy", "trash", "purge", "erase", "drop", "clear",
                  "replace", "put", "transfer")


# ── It can never delete (PLAN.md §3.3, rule 1) ─────────────────────────

def test_the_client_has_no_way_to_delete():
    """Checked in the source: no DELETE or PUT anywhere, no method named like deleting, and the only writes are a PATCH
    and a POST inside _send, reached only from the two writing methods."""
    source = Path(client_module.__file__).read_text()
    tree = ast.parse(source)
    writers = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in FORBIDDEN_CALLS, f"client.py calls .{node.func.attr}() (line {node.lineno})"
                if node.func.attr in ("post", "patch"):
                    assert fn.name == "_send", f".{node.func.attr}() outside _send (line {node.lineno})"
                if node.func.attr == "_send":
                    writers.add(fn.name)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value.upper() not in {"DELETE", "PUT"}, f"an HTTP {node.value} on line {node.lineno}"
    methods = [name for name, _ in inspect.getmembers(PlaneClient, inspect.isfunction) if not name.startswith("__")]
    for name in methods:
        assert not name.lstrip("_").lower().startswith(DELETING_NAMES), f"PlaneClient.{name} sounds like it deletes"
    assert writers == {"update_work_item", "create_work_item"}
    assert {"me", "projects", "members", "states", "labels", "cycles", "work_items", "work_item"} <= set(methods)


def test_only_a_patch_or_a_post_can_be_sent():
    fake = FakePlane()
    c = fake.client()
    for verb in ("DELETE", "PUT", "GET", "delete"):
        with pytest.raises(PlaneError, match="never deletes"):
            c._send(verb, ITEMS, {})
    assert fake.requests == []


def test_every_read_is_a_get():
    fake = FakePlane()
    c = fake.client()
    pid = PROJECTS["SOFTWARE"]
    c.me(), c.projects(), c.members(), c.states(pid), c.labels(pid), c.cycles(pid), c.work_items(pid)
    c.work_item(pid, fake.item("SOFTWARE-5")["id"])
    assert fake.requests and {r.method for r in fake.requests} == {"GET"}
    assert all(r.headers["X-API-Key"] == "plane_api_test" for r in fake.requests)


# ── Writing, when asked ────────────────────────────────────────────────

def test_a_change_sends_only_the_fields_given():
    fake = FakePlane()
    item = fake.item("DALEETING-6")
    answer = fake.client().update_work_item(item["project"], item["id"], {"target_date": "2026-10-31"})
    assert answer["target_date"] == "2026-10-31" and answer["name"] == "Write the case study draft"
    [(method, path, body)] = fake.writes
    assert (method, body) == ("PATCH", {"target_date": "2026-10-31"}) and path.endswith(f"/work-items/{item['id']}/")
    assert fake.requests[-1].headers["X-API-Key"] == "plane_api_test"
    assert json.loads(fake.requests[-1].content) == {"target_date": "2026-10-31"}


def test_a_new_item_is_added_to_its_project():
    fake = FakePlane()
    made = fake.client().create_work_item(PROJECTS["SOFTWARE"], {"name": "Write the API docs", "priority": "high"})
    assert made["id"] and made["sequence_id"] == 6 and made["priority"] == "high"
    assert [w[0] for w in fake.writes] == ["POST"]


def test_writes_refuse_fields_traverse_never_sends():
    fake = FakePlane()
    c = fake.client()
    with pytest.raises(PlaneError, match="doesn't write labels"):
        c.update_work_item(PROJECTS["SOFTWARE"], "x", {"labels": []})
    with pytest.raises(PlaneError, match="needs a name"):
        c.create_work_item(PROJECTS["SOFTWARE"], {"name": "  "})
    assert fake.requests == []


def test_a_post_that_fails_is_not_sent_again_but_a_patch_is():
    fake = FakePlane()
    item = fake.item("DALEETING-6")
    path = f"/api/v1/workspaces/{WS}/projects/{item['project']}/work-items/"
    fake.fail(f"POST {path}", 502)
    with pytest.raises(PlaneError, match="Plane had a problem"):
        fake.client().create_work_item(item["project"], {"name": "Once only"})
    assert [w[0] for w in fake.writes] == [] and len(fake.requests) == 1        # tried once: it may have been made
    fake.fail(f"PATCH {path}{item['id']}/", 502)
    fake.client().update_work_item(item["project"], item["id"], {"priority": "low"})
    assert item["priority"] == "low" and len(fake.requests) == 3                # the same values again change nothing


def test_plane_saying_no_to_a_write_is_readable():
    fake = FakePlane()
    item = fake.item("DALEETING-6")
    fake.fail(f"PATCH {fake.item_path('DALEETING-6')}", (400, {}))
    with pytest.raises(PlaneError, match="Plane said no"):
        fake.client().update_work_item(item["project"], item["id"], {"priority": "low"})
    with pytest.raises(PlaneError, match="isn't in Plane any more"):
        fake.client().work_item(item["project"], "no-such-item")


# ── Paging ─────────────────────────────────────────────────────────────

def test_lists_are_followed_page_by_page_to_the_end():
    fake = FakePlane()
    fake.page_size = 3
    items = fake.client().work_items(PROJECTS["BD"])
    assert sorted(i["sequence_id"] for i in items) == list(range(1, 15))     # all 14, none twice
    pages = [r for r in fake.requests if r.url.path == ITEMS]
    assert len(pages) == 5                                                    # 3 + 3 + 3 + 3 + 2
    assert [r.url.params.get("cursor") for r in pages] == [None, "3:1:0", "3:2:0", "3:3:0", "3:4:0"]
    assert all(r.url.params["per_page"] == "100" for r in pages)


def test_a_plain_list_is_one_page():
    fake = FakePlane()
    assert {m["display_name"] for m in fake.client().members()} == {"dale", "eli", "mickey", "Plane MCP", "Plane"}
    assert len(fake.requests) == 1


def test_a_cursor_that_never_moves_does_not_loop_forever():
    fake = FakePlane()
    stuck = {**fake.data[PROJECTS_PATH], "next_page_results": True, "next_cursor": "100:1:0"}
    fake.data[PROJECTS_PATH] = stuck
    fake._page = lambda body, request: {**body, "next_cursor": "100:1:0"}
    assert len(fake.client().projects()) == 8
    assert len(fake.requests) == 2              # the first page, then the same cursor again: stop


# ── Rate limits and hiccups ────────────────────────────────────────────

def test_a_rate_limit_waits_until_plane_says_and_tries_again():
    fake = FakePlane()
    fake.fail(PROJECTS_PATH, (429, {"X-RateLimit-Reset": str(int(time.time()) + 7), "X-RateLimit-Remaining": "0"}))
    assert len(fake.client().projects()) == 8
    assert len(fake.slept) == 1 and 6 <= fake.slept[0] <= 9


def test_retry_after_is_honored_and_errors_from_plane_back_off():
    fake = FakePlane()
    fake.fail(PROJECTS_PATH, (429, {"Retry-After": "3"}), 502, 503)
    assert len(fake.client().projects()) == 8
    assert fake.slept == [3.0, 4.0, 8.0]          # Retry-After, then 2^2 and 2^3 for the server errors


def test_running_out_of_requests_waits_for_the_window_before_the_next():
    fake = FakePlane()
    reset = str(int(time.time()) + 20)
    original = fake.handle

    def handle(request):
        r = original(request)
        r.headers["X-RateLimit-Remaining"] = "0"
        r.headers["X-RateLimit-Reset"] = reset
        return r

    fake.transport = httpx.MockTransport(handle)
    fake.client().me()
    assert len(fake.slept) == 1 and 18 <= fake.slept[0] <= 22


def test_a_rate_limit_that_never_lifts_says_so():
    fake = FakePlane()
    fake.fail(PROJECTS_PATH, *[(429, {"Retry-After": "1"})] * 5)
    with pytest.raises(PlaneError, match="slow down"):
        fake.client().projects()
    assert len(fake.slept) == 4


def test_a_timeout_is_retried_then_explained():
    fake = FakePlane()
    fake.fail(PROJECTS_PATH, httpx.ReadTimeout("slow"))
    assert len(fake.client().projects()) == 8
    fake.fail(PROJECTS_PATH, *[httpx.ReadTimeout("slow")] * 5)
    with pytest.raises(PlaneError, match="didn't answer in time"):
        fake.client().projects()


# ── Readable errors ────────────────────────────────────────────────────

def test_a_wrong_key_says_where_to_get_a_new_one():
    fake = FakePlane()
    c = PlaneClient("https://api.plane.so", "not-the-key", WS, transport=fake.transport, sleep=fake.slept.append)
    with pytest.raises(PlaneError, match="didn't accept the API key") as e:
        c.me()
    assert e.value.status == 401 and "Personal access tokens" in str(e.value)


def test_an_unknown_workspace_names_it():
    fake = FakePlane()
    c = PlaneClient("https://api.plane.so", "plane_api_test", "cold-conect", transport=fake.transport)
    with pytest.raises(PlaneError, match="no workspace called “cold-conect”"):
        c.projects()


def test_forbidden_and_server_errors_are_sentences():
    fake = FakePlane()
    fake.fail(PROJECTS_PATH, 403)
    with pytest.raises(PlaneError, match="isn't allowed to see that") as e:
        fake.client().projects()
    assert e.value.status == 403
    fake.fail(PROJECTS_PATH, *[500] * 5)
    with pytest.raises(PlaneError, match=r"Plane had a problem \(500\)"):
        fake.client().projects()


def test_an_unreachable_server_and_a_page_that_isnt_json():
    def offline(request):
        raise httpx.ConnectError("no route to host")
    c = PlaneClient("https://plane.example.org", "k", WS, transport=httpx.MockTransport(offline))
    with pytest.raises(PlaneError, match="Couldn't reach Plane at https://plane.example.org"):
        c.me()
    c = PlaneClient("https://plane.example.org", "k", WS,
                    transport=httpx.MockTransport(lambda r: httpx.Response(200, text="<html>Sign in</html>")))
    with pytest.raises(PlaneError, match="isn't JSON"):
        c.me()


def test_a_client_needs_a_key_and_a_workspace():
    with pytest.raises(PlaneError, match="API key"):
        PlaneClient("https://api.plane.so", "", WS)
    with pytest.raises(PlaneError, match="workspace"):
        PlaneClient("https://api.plane.so", "k", " ")


def test_items_open_in_plane_cloud_or_your_own_server():
    assert web_url("https://api.plane.so") == "https://app.plane.so"
    assert web_url("") == "https://app.plane.so"
    assert web_url("https://plane.example.org/") == "https://plane.example.org"


def test_plane_clouds_web_address_means_its_api():
    from modules.plane.server.client import api_url, web_url
    assert api_url("https://app.plane.so") == "https://api.plane.so"
    assert api_url("https://app.plane.so/") == "https://api.plane.so"
    assert api_url("") == "https://api.plane.so"
    assert api_url("https://plane.example.com/") == "https://plane.example.com"
    assert web_url("https://app.plane.so") == "https://app.plane.so"
