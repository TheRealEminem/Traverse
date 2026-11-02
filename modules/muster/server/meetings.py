"""The day's meetings as Muster plans around them: briefing lines that say when they start ("when", a moment in this
computer's time) and how long they take ("minutes"). Traverse's calendar module gives them; Muster doesn't know or
care where they come from.

    kind "meeting" with minutes  takes your time
    kind "event"                 doesn't: all day ("when" is a day) or shown as free
A meeting without minutes (one Trailmix recorded) has happened; nothing is planned around it.
"""
from datetime import date, datetime, time

DAY_MINUTES = 24 * 60
SHORTEST_GAP = 5                 # minutes: anything shorter isn't free time


def hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def minutes_of(hhmm_text: str) -> int:
    h, _, m = hhmm_text.partition(":")
    return int(h) * 60 + int(m or 0)


def all_day(entries: list[dict]) -> list[dict]:
    return [e for e in entries if e.get("kind") == "event" and len(e.get("when") or "") == 10]


def busy(entries: list[dict], day: str) -> list[tuple[int, int, dict]]:
    """The meetings that take time on `day`, as (start, end, entry) in minutes since its midnight, cut to the day."""
    midnight = datetime.combine(date.fromisoformat(day), time())
    out = []
    for e in entries:
        when = e.get("when") or ""
        if e.get("kind") != "meeting" or not e.get("minutes") or len(when) <= 10:
            continue
        start = int((datetime.fromisoformat(when) - midnight).total_seconds() // 60)
        a, b = max(0, start), min(DAY_MINUTES, start + e["minutes"])
        if b > a:
            out.append((a, b, e))
    return sorted(out, key=lambda m: m[:2])


def free_blocks(entries: list[dict], day: str, hours: tuple[str, str], now: datetime | None = None) -> list[tuple[int, int]]:
    """The free stretches of the working day, (start, end) in minutes since midnight: working hours less the meetings
    that take time, and on the day itself less what's already gone by (`now`)."""
    begin, finish = minutes_of(hours[0]), minutes_of(hours[1])
    if now is not None and now.date().isoformat() == day:
        begin = max(begin, now.hour * 60 + now.minute)
    blocks, at = [], begin
    for start, end, _ in busy(entries, day):
        if start > at:
            blocks.append((at, min(start, finish)))
        at = max(at, end)
        if at >= finish:
            break
    if at < finish:
        blocks.append((at, finish))
    return [(a, b) for a, b in blocks if b - a >= SHORTEST_GAP]
