"""Lockdown (lockdown.py): one switch, shared with the family, that stops every call beyond this Mac. Each choke point
is tried with a transport that records what would have left (nothing reaches a real model or service), work it stops
parks and goes again when it's off, and the switch is shared with another family app through a throwaway family
folder (conftest.py sets TRAILMIX_FAMILY_DIR)."""
import json
import os
import subprocess
import sys
from pathlib import Path

import anthropic
import httpx
import pytest
from pydantic import BaseModel

from core.server import ai, ai_adapters, config, db, family, jobs, lockdown, settings

ROOT = Path(__file__).resolve().parents[2]
CLOUD = "https://api.example.com/v1"


class Answer(BaseModel):
    text: str


@pytest.fixture(autouse=True)
def fresh():
    def wipe():
        db.execute("DELETE FROM core_ai_usage")
        db.execute("DELETE FROM core_jobs WHERE module = 'probe'")
        with family._connect() as conn:
            conn.execute("DELETE FROM family_settings WHERE key = ?", (lockdown.KEY,))
        db.execute("DELETE FROM core_settings WHERE key IN (?, ?)", (lockdown.KEY, family.SHARING_KEY))
    wipe()
    yield
    jobs.drain()
    wipe()


@pytest.fixture
def sent(monkeypatch):
    """Every request that would have left the app for an AI provider, from any adapter."""
    out = []

    def record(url, *a, **kw):
        out.append(str(url))
        return httpx.Response(200, json={}, request=httpx.Request("POST", str(url)))
    for target in (ai.httpx, ai_adapters.httpx):
        monkeypatch.setattr(target, "post", record)
        monkeypatch.setattr(target, "get", record)
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **kw: out.append("Claude's API") or pytest.fail("Claude reached"))
    return out


def cloud_cfg(**overrides) -> dict:
    return {**settings.section("ai"), "anthropic_api_key": "sk-test", "openai_api_key": "sk-test",
            "ollama_url": "http://localhost:11434", "custom_base_url": "http://127.0.0.1:1234/v1", "custom_model": "local",
            **overrides}


def another_app_saves(changes: dict) -> None:
    """What another family app ("Faraway") does when you save a shared setting there."""
    with family._connect() as conn:
        for key, value in changes.items():
            conn.execute("INSERT INTO family_settings (key, value, updated_at, updated_by) VALUES (?, ?, 'now', 'faraway') "
                         "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, json.dumps(value)))
        family._bump(conn)


# ── AI: the choke point ───────────────────────────────────────────────

def test_cloud_ai_isnt_ready_and_ai_on_this_mac_is(lockdown_on, monkeypatch):
    monkeypatch.setattr(ai, "_ollama_tags", lambda cfg: [{"name": "qwen2.5:7b"}])
    cfg = cloud_cfg()
    assert ai.configured("anthropic", cfg) == (False, ai.LOCKED_OUT)
    assert not ai.configured("openai", cfg)[0] and not ai.configured("gemini", cfg)[0]
    assert ai.configured("ollama", cfg)[0]
    assert ai.configured("custom", cfg)[0]                                        # an OpenAI-compatible server here
    assert not ai.configured("ollama", {**cfg, "ollama_url": "http://studio.local:11434"})[0]   # another machine
    assert not ai.configured("custom", {**cfg, "custom_base_url": "https://openrouter.ai/api/v1"})[0]
    settings.update({lockdown.KEY: False})
    assert ai.configured("anthropic", cfg)[0]


def test_settings_say_why_a_cloud_provider_isnt_ready(lockdown_on, client):
    providers = {p["id"]: p for p in client.get("/api/ai/providers").json()}
    assert not providers["anthropic"]["ready"] and providers["anthropic"]["reason"].startswith(lockdown.REASON)


def test_nothing_reaches_a_cloud_provider(lockdown_on, sent, monkeypatch):
    cfg = cloud_cfg(provider="openai", fallback="none")
    monkeypatch.setattr(ai.settings, "section", lambda ns: cfg)
    with pytest.raises(ai.Locked) as stopped:
        ai.complete("Hello")
    assert isinstance(stopped.value, jobs.Wait) and str(stopped.value).startswith(lockdown.REASON)
    with pytest.raises(ai.Locked):
        ai.structured("Hello", None, Answer)
    with pytest.raises(ai.Locked):                                  # straight to the adapters, without attempt()
        ai.generate("openai", cloud_cfg(), "Hello")
    with pytest.raises(ai.Locked):
        ai_adapters.generate_structured("gemini", cloud_cfg(gemini_api_key="g-test"), "Hello", None, Answer, None)
    with pytest.raises(ai.Locked):
        ai.list_models("openai")
    with pytest.raises(ai.Locked):
        ai.test("anthropic")
    assert sent == []


def test_nothing_reaches_the_fake_ai(lockdown_on, fake_structured, fake_ai):
    heard = []
    fake_structured.reply = lambda prompt, system, schema: heard.append(prompt) or Answer(text="hi")
    with pytest.raises(ai.Locked):
        ai.structured("Hello", None, Answer)
    with pytest.raises(ai.Locked):
        ai.complete("Hello")
    assert heard == []
    rows = db.query("SELECT provider, input_tokens, output_tokens, cost, failed FROM core_ai_usage ORDER BY at")
    assert [tuple(r.values()) for r in rows] == [("anthropic", None, None, 0, 1), ("fake", None, None, 0, 1)]


def test_a_fallback_on_this_mac_still_answers(lockdown_on):
    asked = []

    def answer(pid, meter):
        asked.append(pid)
        return "Done here"
    cfg = cloud_cfg(provider="anthropic", fallback="ollama")
    assert ai.run_chain("auto", cfg, "complete", answer) == ("Done here", "ollama")
    assert asked == ["ollama"]

    def down(pid, meter):
        raise ai.AIError("Ollama isn't running", provider_down=True)
    with pytest.raises(ai.Locked) as stopped:                         # Claude might answer once Lockdown is off: wait
        ai.run_chain("auto", cfg, "complete", down)
    assert str(stopped.value) == f"{ai.LOCKED_OUT}; Ollama: Ollama isn't running"


def test_the_usage_log_shows_stopped_calls_without_a_cost(lockdown_on, fake_structured, client):
    fake_structured.reply = Answer(text="hi")
    with pytest.raises(ai.Locked):
        ai.structured("Hello", None, Answer)
    usage = client.get("/api/ai/usage").json()
    [call] = usage["recent"]
    assert (call["stopped"], call["failed"], call["unknown"], call["cost"]) == (True, False, False, 0)
    assert call["error"].startswith(lockdown.REASON) and call["provider_label"] == "Claude (Anthropic)"
    month = usage["month"]
    assert (month["calls"], month["stopped"], month["failed"], month["unknown"], month["cost"]) == (1, 1, 0, 0, 0)

    settings.update({lockdown.KEY: False})
    ai.structured("Hello", None, Answer)                              # the same call goes, and costs, once it's off
    month = client.get("/api/ai/usage").json()["month"]
    assert (month["calls"], month["stopped"]) == (2, 1) and month["cost"] > 0


# ── Anything else: may I reach the cloud? ─────────────────────────────

def test_modules_ask_before_reaching_out(lockdown_on):
    assert not lockdown.may_reach() and not lockdown.may_reach("https://api.plane.so")
    for here in ("http://127.0.0.1:8765", "http://localhost:11434", "http://[::1]:8080", "http://127.0.0.2"):
        assert lockdown.may_reach(here), here
    with pytest.raises(lockdown.Blocked) as stopped:
        lockdown.check("https://api.plane.so")
    assert isinstance(stopped.value, jobs.Wait) and str(stopped.value) == lockdown.REASON
    lockdown.check("http://127.0.0.1:8765")
    settings.update({lockdown.KEY: False})
    assert lockdown.may_reach() and lockdown.may_reach("https://api.plane.so")


# ── Parked work goes again when it's off ─────────────────────────────

def _job(name: str, handler) -> str:
    jobs.register("probe", name, handler)
    job_id = jobs.enqueue("probe", name, "x")
    jobs.drain()
    return job_id


def _status(job_id: str) -> dict:
    return db.one("SELECT status, wait_reason, error FROM core_jobs WHERE id = ?", (job_id,))


def test_a_job_that_needs_cloud_ai_parks_and_resumes_when_its_off(lockdown_on, fake_structured, client):
    fake_structured.reply = Answer(text="Summed up")
    done = []
    job_id = _job("think", lambda job: done.append(ai.structured("Sum it up", None, Answer)[0].text))
    assert _status(job_id)["status"] == "waiting" and _status(job_id)["wait_reason"].startswith(lockdown.REASON)
    assert done == [] and client.get("/api/lockdown").json() == {"on": True, "parked": 1}

    assert client.put("/api/settings", json={lockdown.KEY: False}).status_code == 200    # resumes at once
    jobs.drain()
    assert _status(job_id) == {"status": "done", "wait_reason": None, "error": None} and done == ["Summed up"]
    assert client.get("/api/lockdown").json() == {"on": False, "parked": 0}


def test_any_job_that_reaches_out_parks_instead_of_failing(lockdown_on):
    reached = []

    def sync(job):
        lockdown.check(CLOUD)
        reached.append(job.target)
    job_id = _job("sync", sync)
    assert _status(job_id) == {"status": "waiting", "wait_reason": lockdown.REASON, "error": None} and reached == []
    assert lockdown.resume() == 0                                     # still on: nothing goes
    jobs.go(job_id)                                                   # pressing Go doesn't get past it
    jobs.drain()
    assert _status(job_id)["status"] == "waiting" and reached == []


def test_only_work_lockdown_parked_goes_again(lockdown_on):
    ran = []
    jobs.register("probe", "careful", lambda job: ran.append(job.target))
    yours = jobs.enqueue("probe", "careful", "mine", approve=True)               # "Needs you"
    parked = _job("cloudy", lambda job: lockdown.check(CLOUD) or ran.append("cloudy"))
    settings.update({lockdown.KEY: False})
    assert lockdown.resume() == 1
    jobs.drain()
    assert ran == ["cloudy"] and _status(parked)["status"] == "done" and _status(yours)["status"] == "waiting"


def test_a_request_to_the_app_that_would_reach_out_gets_409(lockdown_on):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from core.server.app import app
    probe = FastAPI()
    probe.exception_handlers.update(app.exception_handlers)
    probe.add_api_route("/reach", lambda: lockdown.check(CLOUD))
    r = TestClient(probe).get("/reach")
    assert r.status_code == 409 and r.json()["detail"] == lockdown.SENTENCE


# ── Shared with the family ───────────────────────────────────────────

def test_turning_it_on_here_turns_it_on_for_every_family_app():
    settings.update({lockdown.KEY: True})
    assert family.values()[lockdown.KEY] is True
    settings.update({lockdown.KEY: False})
    assert family.values()[lockdown.KEY] is False


def test_turning_it_on_in_another_app_stops_this_one_and_off_lets_its_work_go(client, fake_structured):
    another_app_saves({lockdown.KEY: True})
    assert client.get("/api/lockdown").json()["on"] is True
    assert client.get("/api/settings").json()["values"][lockdown.KEY] is True
    fake_structured.reply = Answer(text="ok")
    job_id = _job("later", lambda job: ai.structured("Hello", None, Answer))
    assert _status(job_id)["status"] == "waiting"

    another_app_saves({lockdown.KEY: False})
    assert lockdown.resume() == 1                                     # what the watch thread does every few seconds
    jobs.drain()
    assert _status(job_id)["status"] == "done"


def test_an_app_that_doesnt_share_keeps_its_own():
    settings.update({family.SHARING_KEY: False})
    another_app_saves({lockdown.KEY: True})
    assert not lockdown.on()
    settings.update({lockdown.KEY: True})
    assert lockdown.on() and family.values()[lockdown.KEY] is True     # (Faraway's own, unchanged by this app)


def test_two_family_apps_share_the_switch(tmp_path):
    """A second copy of the app, with its own data folder and the same family folder, sees the switch this one turns
    on, and turns it off for this one."""
    def other(code: str) -> str:
        env = {**os.environ, f"{config.PREFIX}_DATA_DIR": str(tmp_path / "other"), f"{config.PREFIX}_UI_DIR": "/nonexistent"}
        run = subprocess.run([sys.executable, "-c", f"from core.server import app, lockdown, settings\n{code}"], cwd=ROOT,
                             env=env, capture_output=True, text=True, timeout=120)
        assert run.returncode == 0, run.stderr[-2000:]
        return run.stdout.strip()

    assert other("print(lockdown.on())") == "False"
    settings.update({lockdown.KEY: True})
    assert other("print(lockdown.on(), settings.stored_here().get(lockdown.KEY))") == "True None"   # the family's
    other("settings.update({lockdown.KEY: False}); print(lockdown.on())")
    assert not lockdown.on()
