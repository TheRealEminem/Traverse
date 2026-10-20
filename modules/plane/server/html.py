"""Plane keeps descriptions as HTML (its editor's); Traverse keeps notes as Markdown. This turns the one into the
other, for the linked copy. It's deterministic, so the same description always reads the same and a pull that
changes nothing changes no notes. (Markdown back to HTML is chunk 7's, for pushing.)"""
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
