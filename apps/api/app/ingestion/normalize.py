"""Normalisering (Technical Master §8, trin 2).

Udtræk tekst, bevar metadata, normalisér whitespace uden betydningsændring.
Råfil og normaliseret tekst gemmes separat (storage hhv. database).
Kildemateriale er untrusted data — der udtrækkes kun tekst, aldrig
instruktioner eller aktiv kode.
"""

import io
import re
from dataclasses import dataclass
from html.parser import HTMLParser

from pypdf import PdfReader

_SKIPPED_TAGS = {"script", "style", "noscript", "template"}
_BLOCK_TAGS = {
    "p",
    "div",
    "br",
    "li",
    "ul",
    "ol",
    "table",
    "tr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "section",
    "article",
    "header",
    "footer",
    "blockquote",
}


@dataclass(frozen=True)
class NormalizedContent:
    text: str | None
    title: str | None


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._title_chunks: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIPPED_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag == "title":
            self._in_title = False
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if self._in_title:
            self._title_chunks.append(data)
        else:
            self._chunks.append(data)

    @property
    def text(self) -> str:
        return "".join(self._chunks)

    @property
    def title(self) -> str | None:
        title = " ".join("".join(self._title_chunks).split())
        return title or None


def normalize_whitespace(text: str) -> str:
    """Kollapser gentaget whitespace uden at ændre indholdets betydning."""
    lines = [re.sub(r"[ \t\f\v]+", " ", line).strip() for line in text.splitlines()]
    collapsed = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return collapsed.strip()


def _extract_html(data: bytes) -> NormalizedContent:
    parser = _HtmlTextExtractor()
    parser.feed(data.decode("utf-8", errors="replace"))
    text = normalize_whitespace(parser.text)
    return NormalizedContent(text=text or None, title=parser.title)


def _extract_pdf(data: bytes) -> NormalizedContent:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception:
        return NormalizedContent(text=None, title=None)
    text = normalize_whitespace("\n\n".join(pages))
    return NormalizedContent(text=text or None, title=None)


def extract_text(mime_type: str, data: bytes) -> NormalizedContent:
    """Udtræk normaliseret tekst. Ukendte formater giver text=None (ikke et gæt)."""
    mime = mime_type.split(";")[0].strip().lower()
    if mime == "text/plain":
        text = normalize_whitespace(data.decode("utf-8", errors="replace"))
        return NormalizedContent(text=text or None, title=None)
    if mime in ("text/html", "application/xhtml+xml"):
        return _extract_html(data)
    if mime == "application/pdf":
        return _extract_pdf(data)
    return NormalizedContent(text=None, title=None)
