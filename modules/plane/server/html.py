"""Plane keeps descriptions as HTML (its editor's); Traverse keeps notes as Markdown. to_markdown turns the one into
the other, for the linked copy, and to_html turns your notes back into HTML Plane's editor reads, for sending them
(chunk 7). Both are deterministic, and they're each other's inverse for the Markdown to_markdown writes: notes that
went out come back the same, so sending them doesn't make them look changed."""
import re
from html import escape
from html.parser import HTMLParser

HEADINGS = {f"h{n}": n for n in range(1, 7)}
INLINE = {"strong": "**", "b": "**", "em": "*", "i": "*", "s": "~~", "del": "~~", "code": "`"}


class _ToMarkdown(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self.line = ""             # the line being written
        self.fresh = True          # nothing but its prefix written on this line yet
        self.gap = False           # a blank line before the next block
        self.lists: list[list] = []    # [kind, count, is_task_list] for each open list
        self.quote = 0
        self.pre = 0
        self.hrefs: list[str | None] = []

    # Lines and blocks
    def _prefix(self) -> str:
        return "> " * self.quote + "  " * max(0, len(self.lists) - 1)

    def _end_line(self) -> None:
        if not self.fresh or self.pre:
            self.lines.append(self.line.rstrip() if not self.pre else self.line)
        self.line, self.fresh = "", True

    def _new_line(self, marker: str = "", gap: bool = False) -> None:
        self._end_line()
        if (gap or self.gap) and self.lines and self.lines[-1] != "":
            self.lines.append("")
        self.gap = False
        self.line = self._prefix() + marker
        self.fresh = True

    def _write(self, text: str) -> None:
        if not text:
            return
        if self.fresh and not self.line:
            self.line = self._prefix()
        self.line += text
        self.fresh = False

    # The parser's calls
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("p", "div"):
            if not (self.fresh and self.lists and self.line.endswith(" ")):   # a paragraph inside a list item
                self._new_line(gap=True)
        elif tag in HEADINGS:
            self._new_line(gap=True)
            self._write("#" * HEADINGS[tag] + " ")
            self.fresh = True
        elif tag in ("ul", "ol"):
            self.lists.append([tag, 0, a.get("data-type") == "taskList"])
            if len(self.lists) == 1:
                self.gap = True
        elif tag == "li":
            kind, n, tasks = self.lists[-1] if self.lists else ["ul", 0, False]
            if self.lists:
                self.lists[-1][1] += 1
            if kind == "ol":
                marker = f"{n + 1}. "
            elif tasks or "data-checked" in a:
                marker = "- [x] " if a.get("data-checked") == "true" else "- [ ] "
            else:
                marker = "- "
            if n or len(self.lists) > 1:
                self.gap = False              # items of a list sit together (a blank line comes before the list)
            self._new_line()
            self.line += marker
        elif tag == "br":
            self._new_line()
        elif tag == "hr":
            self._new_line(gap=True)
            self._write("---")
            self.gap = True
        elif tag == "pre":
            self._new_line(gap=True)
            self._write("```")
            self._end_line()
            self.pre += 1
        elif tag == "blockquote":
            self.quote += 1
            self._new_line(gap=True)
        elif tag == "a":
            self.hrefs.append(a.get("href"))
            self._write("[")
        elif tag == "img" or tag == "image-component":
            if a.get("src"):
                self._write(f"![{a.get('alt') or ''}]({a['src']})")
        elif tag in INLINE and not (tag == "code" and self.pre):
            self._write(INLINE[tag])

    def handle_endtag(self, tag):
        if tag in ("p", "div") or tag in HEADINGS:
            self.gap = True
        elif tag in ("ul", "ol"):
            if self.lists:
                self.lists.pop()
            if not self.lists:
                self.gap = True
        elif tag == "pre":
            self.pre = max(0, self.pre - 1)
            self._end_line()
            self._write("```")
            self.gap = True
        elif tag == "blockquote":
            self.quote = max(0, self.quote - 1)
            self.gap = True
        elif tag == "a":
            href = self.hrefs.pop() if self.hrefs else None
            self._write(f"]({href})" if href else "]")
        elif tag in INLINE and not (tag == "code" and self.pre):
            self._write(INLINE[tag])

    def handle_data(self, data):
        if self.pre:
            for n, part in enumerate(data.split("\n")):
                if n:
                    self.lines.append(self.line)
                    self.line = ""
                self.line += part
                self.fresh = False
            return
        text = " ".join(data.split())
        if data[:1].isspace() and not self.fresh and not self.line.endswith(" "):
            text = " " + text
        if data[-1:].isspace() and text.strip():
            text += " "
        self._write(text if not self.fresh else text.lstrip())

    def result(self) -> str:
        self._end_line()
        out = "\n".join(self.lines).strip("\n")
        while "\n\n\n" in out:
            out = out.replace("\n\n\n", "\n\n")
        return "\n".join(line.rstrip() for line in out.split("\n")).strip()


def to_markdown(html: str | None) -> str:
    """Plane's description_html as Markdown ("" for an empty one)."""
    if not html or not html.strip():
        return ""
    parser = _ToMarkdown()
    parser.feed(html)
    parser.close()
    return parser.result()


# ── Markdown to HTML, for sending notes ───────────────────────────────

_LIST = re.compile(r"^( *)([-*+]|\d+[.)]) (\[[ xX]\] )?(.*)$")
_HEADING = re.compile(r"^(#{1,6}) +(.*?)#*\s*$")
_RULE = re.compile(r"^ {0,3}([-*_])( *\1){2,} *$")
_FENCE = re.compile(r"^ {0,3}```")
_INLINE = [
    (re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)"), lambda m: f'<img src="{m[2]}" alt="{m[1]}">'),
    (re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)"), lambda m: f'<a href="{m[2]}">{m[1]}</a>'),
    (re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*|__(?=\S)(.+?)(?<=\S)__"), lambda m: f"<strong>{m[1] or m[2]}</strong>"),
    (re.compile(r"(?<![*\w])\*(?=\S)(.+?)(?<=\S)\*(?![*\w])|(?<![_\w])_(?=\S)(.+?)(?<=\S)_(?![_\w])"),
     lambda m: f"<em>{m[1] or m[2]}</em>"),
    (re.compile(r"~~(?=\S)(.+?)(?<=\S)~~"), lambda m: f"<s>{m[1]}</s>"),
]


def _inline(text: str) -> str:
    """One line's inline Markdown as HTML: code spans first (their insides stay as written), then the rest."""
    out = []
    for n, part in enumerate(re.split(r"(`[^`]+`)", text)):
        if n % 2:
            out.append(f"<code>{escape(part[1:-1], quote=False)}</code>")
            continue
        part = escape(part, quote=False).replace('"', "&quot;")
        for pattern, swap in _INLINE:
            part = pattern.sub(swap, part)
        out.append(part)
    return "".join(out)


def _list(lines: list[str]) -> str:
    """Consecutive list lines (with deeper ones nested under the item before them) as <ul>/<ol>."""
    html: list[str] = []
    stack: list[tuple[int, str]] = []          # (indent, closing tag) for each open list
    for line in lines:
        m = _LIST.match(line)
        if not m:                              # a continuation line: it joins the item before it
            if html and html[-1].endswith("</p>"):
                html[-1] = html[-1][:-4] + "<br>" + _inline(line.strip()) + "</p>"
            continue
        indent, marker, box, text = len(m[1]), m[2], m[3], m[4]
        ordered = marker[0].isdigit()
        tag = "ol" if ordered else "ul"
        while stack and indent < stack[-1][0]:
            html.append(f"</li></{stack.pop()[1]}>")
        if not stack or indent > stack[-1][0]:
            attrs = ' data-type="taskList"' if box else ""
            html.append(f"<{tag}{attrs}>")
            stack.append((indent, tag))
        else:
            html.append("</li>")
        item = f' data-type="taskItem" data-checked="{"true" if box.strip("[ ]") else "false"}"' if box else ""
        html.append(f"<li{item}><p>{_inline(text)}</p>")
    while stack:
        html.append(f"</li></{stack.pop()[1]}>")
    return "".join(html)


def _blocks(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif _FENCE.match(line):
            end = next((j for j in range(i + 1, len(lines)) if _FENCE.match(lines[j])), len(lines))
            out.append(f"<pre><code>{escape(chr(10).join(lines[i + 1:end]), quote=False)}</code></pre>")
            i = end + 1
        elif _HEADING.match(line):
            m = _HEADING.match(line)
            out.append(f"<h{len(m[1])}>{_inline(m[2])}</h{len(m[1])}>")
            i += 1
        elif _RULE.match(line):
            out.append("<hr>")
            i += 1
        elif line.lstrip().startswith(">"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith(">"):
                j += 1
            inner = [re.sub(r"^\s*> ?", "", q) for q in lines[i:j]]
            out.append(f"<blockquote>{''.join(_blocks(inner))}</blockquote>")
            i = j
        elif _LIST.match(line):
            j = i + 1
            while j < len(lines) and lines[j].strip() and (_LIST.match(lines[j]) or lines[j].startswith(" ")):
                j += 1
            out.append(_list(lines[i:j]))
            i = j
        else:
            j = i + 1
            while j < len(lines) and lines[j].strip() and not (_FENCE.match(lines[j]) or _HEADING.match(lines[j])
                                                               or _RULE.match(lines[j]) or _LIST.match(lines[j])
                                                               or lines[j].lstrip().startswith(">")):
                j += 1
            out.append("<p>" + "<br>".join(_inline(t.strip()) for t in lines[i:j]) + "</p>")
            i = j
    return out


def to_html(markdown: str | None) -> str:
    """Your notes as HTML for Plane's description ("<p></p>", Plane's own empty one, for no notes)."""
    if not markdown or not markdown.strip():
        return "<p></p>"
    return "".join(_blocks(markdown.replace("\r\n", "\n").split("\n")))
