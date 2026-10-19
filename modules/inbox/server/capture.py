"""Turning what you bring in into a capture's title and text: pasted text, or a .txt, .md or .eml file.

The page reads a file itself and sends its text, so the server needs no upload handling. An email keeps the lines
that say who wrote to whom and when, because who and when are what the reading looks for.
"""
import html
import re
from email import policy
from email.parser import Parser
from email.utils import parsedate_to_datetime

from . import store

FILE_KINDS = (".txt", ".md", ".eml")
TITLE_CHARS = 80


def _first_line(text: str) -> str:
    line = next((l.strip(" #*->\t") for l in text.splitlines() if l.strip(" #*->\t")), "")
    return line if len(line) <= TITLE_CHARS else line[: TITLE_CHARS - 1].rstrip() + "…"


def _checked(text: str) -> str:
    text = text.replace("\r\n", "\n").strip()
    if not text:
        raise ValueError("There's nothing to read in that.")
    if len(text) > store.MAX_CHARS:
        raise ValueError(f"That's longer than the inbox reads at once ({store.MAX_CHARS:,} characters). "
                         "Bring in the part with the work in it.")
    return text


def pasted(text: str, title: str = "") -> dict:
    text = _checked(text)
    return {"source": "paste", "title": title.strip() or _first_line(text) or "Pasted text", "raw_text": text,
            "title_auto": not title.strip()}


def from_file(name: str, text: str) -> dict:
    name = name.strip() or "file.txt"
    kind = name[name.rfind("."):].lower() if "." in name else ""
    if kind not in FILE_KINDS:
        raise ValueError("The inbox reads .txt, .md and .eml files.")
    if kind == ".eml":
        sent = email_date(text)
        title, text = _email(text)
        return {"source": "file", "title": title or name, "raw_text": _checked(text), "title_auto": not title,
                "origin_title": name, "origin_at": sent}
    text = _checked(text)
    return {"source": "file", "title": _first_line(text) or name, "raw_text": text, "origin_title": name}


def _email(raw: str) -> tuple[str, str]:
    """(subject, the email as plain text with its From, To, Cc and Date lines on top)."""
    msg = Parser(policy=policy.default).parsestr(raw)
    head = [f"{key}: {msg[key]}" for key in ("From", "To", "Cc", "Date") if msg[key]]
    body = msg.get_body(preferencelist=("plain", "html"))
    text = ""
    if body is not None:
        try:
            text = body.get_content()
        except (LookupError, ValueError):
            text = body.get_payload(decode=True).decode("utf-8", "replace") if body.get_payload(decode=True) else ""
        if body.get_content_type() == "text/html":
            text = _html_text(text)
    elif not msg.is_multipart():
        text = str(msg.get_payload())
    return str(msg["Subject"] or "").strip(), "\n".join(head) + "\n\n" + text.strip()


def email_date(raw: str) -> str | None:
    """The day an email was sent (YYYY-MM-DD), for reading "Friday" in it, or None."""
    try:
        sent = Parser(policy=policy.default).parsestr(raw, headersonly=True)["Date"]
        return parsedate_to_datetime(str(sent)).date().isoformat() if sent else None
    except (TypeError, ValueError):
        return None


def _html_text(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style).*?</\1>", "", markup)
    markup = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>", "\n", markup)
    text = html.unescape(re.sub(r"<[^>]+>", "", markup))
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()
