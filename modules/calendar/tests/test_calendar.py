"""The calendar module: reading a private iCal address (time zones, repeats, moved and skipped times, cancelled,
declined, free and all-day events), what a failed read says (never the address), the API (which never sends the
address back), this Mac's Calendar as the app's window sends it, the briefing, and forgetting what's over."""
from datetime import timedelta

import httpx
import pytest

from core.server import jobs
from modules.calendar.server import briefing, feeds, mac, store
from modules.calendar.tests.conftest import TODAY

SECRET = "https://calendar.example.com/calendar/ical/me%40example.com/private-5ecr3t/basic.ics"

FEED = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Example//Test//EN
X-WR-CALNAME:me@example.com
BEGIN:VTIMEZONE
TZID:America/New_York
BEGIN:DAYLIGHT
TZOFFSETFROM:-0500
TZOFFSETTO:-0400
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0400
TZOFFSETTO:-0500
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
UID:standup
SUMMARY:Standup
DTSTART:20261019T230000Z
DTEND:20261019T231500Z
RRULE:FREQ=DAILY;COUNT=10
EXDATE:20261023T230000Z
END:VEVENT
BEGIN:VEVENT
UID:standup
RECURRENCE-ID:20261022T230000Z
SUMMARY:Standup (moved)
DTSTART:20261022T233000Z
DTEND:20261022T234500Z
END:VEVENT
BEGIN:VEVENT
UID:review
SUMMARY:Design review
DTSTART;TZID=America/New_York:20261020T230000
DTEND;TZID=America/New_York:20261021T000000
END:VEVENT
BEGIN:VEVENT
UID:offsite
SUMMARY:Offsite
DTSTART;VALUE=DATE:20261021
DTEND;VALUE=DATE:20261023
TRANSP:TRANSPARENT
END:VEVENT
BEGIN:VEVENT
UID:focus
SUMMARY:Focus time
DTSTART:20261021T000000Z
DURATION:PT1H
TRANSP:TRANSPARENT
END:VEVENT
BEGIN:VEVENT
UID:cancelled
SUMMARY:Called off
STATUS:CANCELLED
DTSTART:20261021T020000Z
DTEND:20261021T030000Z
END:VEVENT
BEGIN:VEVENT
UID:declined
SUMMARY:Vendor pitch
DTSTART:20261021T040000Z
DTEND:20261021T050000Z
ATTENDEE;PARTSTAT=DECLINED:mailto:me@example.com
ATTENDEE;PARTSTAT=ACCEPTED:mailto:ana@example.com
END:VEVENT
BEGIN:VEVENT
UID:floating
SUMMARY:Lunch with Ana
DTSTART:20261021T123000
DTEND:20261021T133000
ATTENDEE;PARTSTAT=ACCEPTED:mailto:me@example.com
END:VEVENT
BEGIN:VEVENT
UID:later
SUMMARY:Next month
DTSTART:20261121T090000Z
DTEND:20261121T100000Z
END:VEVENT
BEGIN:VEVENT
UID:gone
SUMMARY:Last week
DTSTART:20261014T090000Z
DTEND:20261014T100000Z
END:VEVENT
END:VCALENDAR
"""


def calendar_server(body: bytes = FEED, status: int = 200):
    """A stand-in for the calendar's server, which records what was asked."""
    asked = []

    def answer(request: httpx.Request) -> httpx.Response:
        asked.append(str(request.url))
        return httpx.Response(status, content=body)
    feeds._transport = httpx.MockTransport(answer)
    return asked


def _when(events):
    return [(e["title"], e["starts"], e["ends"], e["all_day"], e["free"]) for e in sorted(events, key=lambda e: (e["starts"], e["title"]))]


def test_a_feed_reads_in_this_computers_time_with_repeats_and_without_what_isnt_yours(melbourne):
    events = feeds.parse(FEED, TODAY)
    on_today = _when(e for e in events if e["starts"].startswith("2026-10-21"))
    assert on_today == [
        ("Offsite", "2026-10-21", "2026-10-23", True, True),                         # two days, all day
        ("Standup", "2026-10-21T10:00", "2026-10-21T10:15", False, False),          # 23:00 UTC the day before
        ("Focus time", "2026-10-21T11:00", "2026-10-21T12:00", False, True),        # DURATION, shown as free
        ("Lunch with Ana", "2026-10-21T12:30", "2026-10-21T13:30", False, False),   # floating: this computer's time
        ("Design review", "2026-10-21T14:00", "2026-10-21T15:00", False, False),    # New York's 11 pm on the 20th
    ]
    standups = [(e["starts"], e["title"]) for e in sorted(events, key=lambda e: e["starts"]) if e["title"].startswith("Standup")]
    assert standups == [("2026-10-21T10:00", "Standup"), ("2026-10-22T10:00", "Standup"),
                        ("2026-10-23T10:30", "Standup (moved)"),                     # the 23rd's, moved half an hour
                        ("2026-10-25T10:00", "Standup"), ("2026-10-26T10:00", "Standup"),   # the 24th's skipped
                        ("2026-10-27T10:00", "Standup"), ("2026-10-28T10:00", "Standup")]   # the window ends on the 29th
    titles = [e["title"] for e in events]
    assert "Called off" not in titles and "Vendor pitch" not in titles               # cancelled; declined by you
    assert "Next month" not in titles and "Last week" not in titles                  # outside today and the week ahead
    assert {e["calendar"] for e in events} == {"me@example.com"}
    with pytest.raises(ValueError):
        feeds.parse(b"this is not a calendar", TODAY)


def test_a_failed_read_says_why_in_words_and_never_the_address(caplog):
    caplog.set_level("INFO")
    source = store.add("ical", "Work", SECRET)
    for status, body, words in [(404, b"", "turned its address down (404)"), (500, b"", "answered 500"),
                                (200, b"<html>Sign in</html>", "doesn't give a calendar")]:
        calendar_server(body, status)
        feeds.read_one(source["id"])
        error = store.source(source["id"])["error"]
        assert words in error and "5ecr3t" not in error and "example.com" not in error

    def timeout(request):
        raise httpx.ConnectTimeout("timed out connecting to " + str(request.url))
    feeds._transport = httpx.MockTransport(timeout)
    feeds.read_one(source["id"])
    assert store.source(source["id"])["error"] == "The calendar didn't answer in time. It's tried again in a few minutes."
    calendar_server()
    feeds.read_one(source["id"])
    assert store.source(source["id"])["error"] is None
    assert "HTTP Request: GET https://calendar.example.com/…" in caplog.text           # the log names the host only
    assert "5ecr3t" not in caplog.text


def test_the_api_reads_a_feed_and_never_sends_its_address_back(client, melbourne):
    asked = calendar_server()
    for bad in ["http://calendar.example.com/x.ics", "calendar.example.com/x.ics", "", "ftp://x/y.ics"]:
        assert client.post("/api/calendar/sources", json={"kind": "ical", "url": bad}).status_code == 400
    made = client.post("/api/calendar/sources", json={"kind": "ical", "name": " Work ", "url": SECRET.replace("https", "webcal")})
    assert made.status_code == 201 and made.json()["name"] == "Work" and made.json()["host"] == "calendar.example.com"
    jobs.drain()
    assert asked == [SECRET]                                                        # webcal:// is read as https://
    listed = client.get("/api/calendar/sources")
    assert "5ecr3t" not in listed.text and "url" not in listed.json()[0]
    shown = listed.json()[0]
    assert shown["error"] is None and shown["read_at"] and shown["events"] == 11

    brief = briefing.brief("", TODAY)
    today = {e["title"]: e for e in brief["today"]}
    assert today["Standup"] == {"id": today["Standup"]["id"], "title": "Standup", "href": None, "when": "2026-10-21T10:00",
                                "minutes": 15, "kind": "meeting", "what": "Meeting", "project": "me@example.com", "tone": "neutral"}
    assert (today["Offsite"]["when"], today["Offsite"]["minutes"], today["Offsite"]["kind"]) == ("2026-10-21", None, "event")
    assert (today["Focus time"]["kind"], today["Focus time"]["what"]) == ("event", "Shown as free")
    assert [e["when"] for e in brief["ahead"]][:2] == ["2026-10-22T10:00", "2026-10-23T10:30"]
    assert "Offsite" not in [e["title"] for e in brief["ahead"]]                    # it began today: it's on today
    assert brief["waiting"] == []

    source_id = shown["id"]
    first_ids = sorted(e["id"] for e in brief["today"])
    client.post(f"/api/calendar/sources/{source_id}/read")
    jobs.drain()
    assert sorted(e["id"] for e in briefing.brief("", TODAY)["today"]) == first_ids   # the same refs read after read

    calendar_server(b"", 404)
    client.post(f"/api/calendar/sources/{source_id}/read")
    jobs.drain()
    waiting = briefing.brief("", TODAY)["waiting"]
    assert [(w["title"], w["tone"], w["href"]) for w in waiting] == [("Work", "sun", "#/settings")]
    assert waiting[0]["what"].startswith("Couldn't be read: The calendar turned its address down (404)")
    assert len(briefing.brief("", TODAY)["today"]) == 5                             # the last good read stays

    client.patch(f"/api/calendar/sources/{source_id}", json={"enabled": False})
    assert briefing.brief("", TODAY) == {"today": [], "waiting": [], "ahead": []}
    assert "5ecr3t" not in str(store.export()) and store.export()["sources"][0]["name"] == "Work"
    assert client.delete(f"/api/calendar/sources/{source_id}").status_code == 204
    assert store.events_between(*store.window()) == [] and client.delete(f"/api/calendar/sources/{source_id}").status_code == 404


def test_this_macs_calendar_is_what_the_apps_window_sends(client, melbourne):
    made = client.post("/api/calendar/sources", json={"kind": "mac"}).json()
    assert made["name"] == "This Mac’s Calendar" and made["host"] is None
    assert client.post("/api/calendar/sources", json={"kind": "mac"}).status_code == 400   # one is enough
    assert client.post(f"/api/calendar/sources/{made['id']}/read").status_code == 400
    sent = [
        {"id": "a@1", "title": "Standup", "start": "2026-10-21T10:00:00+11:00", "end": "2026-10-21T10:15:00+11:00",
         "all_day": False, "calendar": "Work", "free": False},
        {"id": "b@1", "title": "Design review", "start": "2026-10-21T03:00:00Z", "end": "2026-10-21T04:00:00Z",
         "all_day": False, "calendar": "Work", "free": False},
        {"id": "c@1", "title": "Offsite", "start": "2026-10-21T00:00:00+11:00", "end": "2026-10-22T23:59:59+11:00",
         "all_day": True, "calendar": "Home", "free": True},                          # EventKit's two-day all-day
        {"id": "d@1", "title": "  ", "start": "2026-10-21T16:00:00+11:00", "end": "2026-10-21T16:30:00+11:00",
         "all_day": False, "calendar": "Work", "free": False},
        {"id": "e@1", "title": "Too far", "start": "2026-11-21T10:00:00+11:00", "end": "2026-11-21T11:00:00+11:00",
         "all_day": False, "calendar": "Work", "free": False},
    ]
    assert client.put(f"/api/calendar/sources/{made['id']}/events", json={"events": sent}).json() == {"kept": 4}
    today = {e["title"]: (e["when"], e["minutes"], e["kind"], e["project"]) for e in briefing.brief("", TODAY)["today"]}
    assert today == {"Standup": ("2026-10-21T10:00", 15, "meeting", "Work"),
                     "Design review": ("2026-10-21T14:00", 60, "meeting", "Work"),
                     "Offsite": ("2026-10-21", None, "event", "Home"),
                     "Busy": ("2026-10-21T16:00", 30, "meeting", "Work")}
    assert store.events_between(*store.window())[0]["ends"] == "2026-10-23"            # through the 22nd
    for bad, words in [({"events": "nope"}, "list of up to"), ({"events": [{"start": "soon", "end": "later"}]}, "moment like"),
                       ({"events": [{**sent[0], "end": "2026-10-21T09:00:00+11:00"}]}, "end before")]:
        answer = client.put(f"/api/calendar/sources/{made['id']}/events", json=bad)
        assert answer.status_code in (400, 422) and (answer.status_code == 422 or words in answer.json()["detail"])
    feed = store.add("ical", "Work", SECRET)
    assert client.put(f"/api/calendar/sources/{feed['id']}/events", json={"events": []}).status_code == 400
    assert client.put("/api/calendar/sources/nope/events", json={"events": []}).status_code == 404


def test_events_are_kept_for_their_day_only(monkeypatch, melbourne):
    assert feeds.every() == 0                                                       # nothing to read: paused
    source = store.add("mac")
    assert feeds.every() == feeds.EVERY_SECONDS
    mac.take(source["id"], [
        {"id": "a", "title": "Yesterday late", "start": "2026-10-20T22:00:00+11:00", "end": "2026-10-20T23:00:00+11:00"},
        {"id": "b", "title": "Over midnight", "start": "2026-10-20T23:30:00+11:00", "end": "2026-10-21T00:30:00+11:00"},
        {"id": "c", "title": "Today", "start": "2026-10-21T09:00:00+11:00", "end": "2026-10-21T09:30:00+11:00"},
    ])
    assert sorted(e["title"] for e in store.events_between(*store.window())) == ["Over midnight", "Today"]
    monkeypatch.setattr(store, "today", lambda: TODAY + timedelta(days=1))
    jobs.enqueue("calendar", feeds.KIND, "scheduled")                               # the schedule's read
    jobs.drain()
    assert store.events_between(*store.window(TODAY)) == []                         # yesterday's are gone
    assert [e["title"] for e in store.events_between(*store.window())] == []        # (and "over midnight" ended)
