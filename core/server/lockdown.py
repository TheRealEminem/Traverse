"""Lockdown: one switch that stops every call to the cloud, for when nothing should leave this Mac.

`core.lockdown` is one of the settings shared with the other family apps (family.py), so turning it on in one app
turns it on in every family app on this Mac that shares keys and preferences. While it's on:

- **AI:** only models on this Mac answer (Ollama, or an OpenAI-compatible server, at a local address). ai.configured()
  says the others aren't ready, and ai.attempt() stops them before anything is sent; the usage log shows each stop,
  at no cost.
- **Updates:** the Mac app asks GET /api/lockdown before it checks for or downloads an update, and doesn't while it's
  on (or while the server can't say).
- **Modules:** anything else that reaches out asks first: `may_reach(url)` to know, `check(url)` right before the
  request leaves. Plane's client checks before every request, so pulls and pushes stop.

An address on this Mac (localhost) is never the cloud, so a local Ollama, Plane or Trailmix keeps working.

Work stopped by Lockdown isn't an error. check() raises Blocked, a jobs.Wait, so a job that meets it parks with the
reason "Lockdown is on" (wait_reason starts with REASON) and goes again by itself once Lockdown is off: resume(), run
when the setting is saved here and every few seconds by watch(), which also notices another app turning it off.
"""
import ipaddress
import logging
import threading
import time
from urllib.parse import urlparse

from . import db, jobs, settings

log = logging.getLogger("core.lockdown")

KEY = "core.lockdown"
REASON = "Lockdown is on"
SENTENCE = f"{REASON}, so nothing leaves this Mac. Turn it off in Settings → Lockdown to go ahead."
WATCH_SECONDS = 5


class Blocked(jobs.Wait):
    """Lockdown stopped a request before it was sent. A job that meets it parks until Lockdown is off; a request to
    the app's API gets 409 with SENTENCE (app.py)."""

    def __init__(self, message: str = REASON):
        super().__init__(message)


def on() -> bool:
    return settings.get_all().get(KEY) is True


def local(url: str | None) -> bool:
    """The address is this Mac: localhost, or a loopback IP (127.x.x.x, ::1)."""
    host = (urlparse(url or "").hostname or "").lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def may_reach(url: str | None = None) -> bool:
    """"May I reach the cloud?": whether this app may send a request to `url` now (with no url, anywhere beyond this
    Mac). Yes when Lockdown is off, or the address is this Mac."""
    return local(url) or not on()


def check(url: str | None = None) -> None:
    """Raises Blocked unless may_reach(url). Call it right before a request leaves the app."""
    if not may_reach(url):
        raise Blocked()


# ── Parked work ───────────────────────────────────────────────────────

def parked() -> list[dict]:
    """The jobs waiting for Lockdown to be off, oldest first."""
    return db.query("SELECT id, module, kind, target FROM core_jobs WHERE status = 'waiting' AND wait_reason LIKE ? "
                    "ORDER BY created_at", (REASON + "%",))


def resume() -> int:
    """Lockdown is off: everything it parked goes again. Returns how many jobs went."""
    waiting = parked()
    if not waiting or on():
        return 0
    for job in waiting:
        jobs.release(job["id"])
    log.info("Lockdown is off: %s parked jobs go again", len(waiting))
    return len(waiting)


_watching = False


def watch() -> None:
    """Notices Lockdown turned off, here or in another family app, and lets the work it parked go."""
    global _watching
    if _watching:
        return
    _watching = True

    def loop():
        while True:
            time.sleep(WATCH_SECONDS)
            try:
                resume()
            except Exception:  # noqa: BLE001 - one missed look only delays the work a few seconds
                log.exception("couldn't resume the work Lockdown parked")

    threading.Thread(target=loop, daemon=True, name="lockdown-watch").start()


def status() -> dict:
    """For the app's chrome, Settings and the Mac app's updater (GET /api/lockdown)."""
    return {"on": on(), "parked": len(parked())}


# ── The family's names for the same questions ─────────────────────────
# Shared code written against the family's lockdown.py (ollama_setup.py, and the other family apps' modules) asks
# these; here they answer from the same switch.

WHY = SENTENCE


def blocked(what: str) -> str | None:
    """Why `what` can't happen now, in words for a person, or None when it may. For work that is simply switched
    off while Lockdown is on (a download, a sync started by hand); a job that should wait for it uses check()."""
    return f"{what} is off while Lockdown is on (Settings → Lockdown)." if on() else None


def on_this_computer(url: str) -> bool:
    """The family's name for local()."""
    return local(url)
