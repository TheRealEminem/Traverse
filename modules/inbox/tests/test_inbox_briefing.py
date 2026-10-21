"""The inbox's part of the day's briefing: captures with proposals waiting for you, and the meetings Trailmix brought
in, today's and those since a moment."""
from datetime import date, datetime, time, timedelta

from modules.inbox.server import briefing, store

TODAY = date(2026, 10, 21)


def _capture(source: str, title: str, proposals: int, origin_at: str | None = None, status: str = "review") -> str:
    capture_id = store.create(source, title, "Some text", title_auto=False, origin_at=origin_at,
                              origin_title=title if origin_at else None,
                              origin_url="http://127.0.0.1:8765/#meeting-4" if origin_at else None)
    store.replace_proposed(capture_id, [{"text": f"Thing {n}"} for n in range(proposals)])
    store.update(capture_id, status=status)
    return capture_id


def _local(day: date, hour: int) -> str:
    """A moment on this computer's clock, as Trailmix writes them (no zone)."""
    return datetime.combine(day, time(hour)).isoformat()


def test_captures_with_proposals_waiting_wait_on_you():
    waiting = _capture("paste", "Slack thread", 3)
    _capture("paste", "All decided", 0, status="done")
    _capture("paste", "Still being read", 0, status="new")
    found = briefing.brief("2026-10-20T00:00:00.000Z", TODAY)["waiting"]
    assert [(e["id"], e["title"], e["what"], e["tone"], e["href"]) for e in found] == \
        [(waiting, "Slack thread", "3 proposals to review", "sun", f"#/inbox/{waiting}")]


def test_meetings_from_trailmix_are_todays_or_moved():
    today = _capture("trailmix", "Hardware stand-up", 2, _local(TODAY, 10))
    yesterday = _capture("trailmix", "Grant call", 1, _local(TODAY - timedelta(days=1), 15), status="done")
    _capture("trailmix", "Last month", 1, _local(TODAY - timedelta(days=30), 9), status="done")
    since = (datetime.combine(TODAY - timedelta(days=1), time(8)).astimezone()).isoformat()
    found = briefing.brief(since, TODAY)
    assert [(e["id"], e["title"], e["what"], e["kind"]) for e in found["today"]] == \
        [(today, "Hardware stand-up", "Meeting · 2 action items", "meeting")]
    assert found["today"][0]["url"] == "http://127.0.0.1:8765/#meeting-4"
    assert [(e["id"], e["what"]) for e in found["moved"]] == [(yesterday, "Meeting · 1 action item")]
