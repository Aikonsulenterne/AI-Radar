"""RSS/Atom-parsing (Technical Master §8: rss er en af de tre hentemetoder).

Feedet er kildemateriale og dermed untrusted data (Technical Master §9): der
læses kun de felter, schemaet definerer, og intet i feedet kan instruere
systemet. Derfor afvises dokumenter med DTD (entity-expansion) før parsing,
og hvert entry-link valideres, før det hentes.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

from app.errors import ApiError

_ATOM = "{http://www.w3.org/2005/Atom}"
# Et DTD er ikke nødvendigt i hverken RSS 2.0 eller Atom, men er vejen til
# entity-expansion-angreb ("billion laughs") mod stdlib-parseren.
_DTD_MARKERS = (b"<!doctype", b"<!entity")


@dataclass(frozen=True)
class FeedEntry:
    title: str | None
    link: str | None
    published_at: datetime | None


def _text(element: ElementTree.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    stripped = element.text.strip()
    return stripped or None


def _rfc822(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _rfc3339(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _rss_entries(root: ElementTree.Element) -> list[FeedEntry]:
    return [
        FeedEntry(
            title=_text(item.find("title")),
            link=_text(item.find("link")),
            published_at=_rfc822(_text(item.find("pubDate"))),
        )
        for item in root.findall("./channel/item")
    ]


def _atom_link(entry: ElementTree.Element) -> str | None:
    for link in entry.findall(f"{_ATOM}link"):
        href = link.get("href")
        if href and link.get("rel", "alternate") == "alternate":
            return href
    return None


def _atom_entries(root: ElementTree.Element) -> list[FeedEntry]:
    entries = []
    for entry in root.findall(f"{_ATOM}entry"):
        published = _text(entry.find(f"{_ATOM}published")) or _text(entry.find(f"{_ATOM}updated"))
        entries.append(
            FeedEntry(
                title=_text(entry.find(f"{_ATOM}title")),
                link=_atom_link(entry),
                published_at=_rfc3339(published),
            )
        )
    return entries


def parse_feed(data: bytes) -> list[FeedEntry]:
    """Parser RSS 2.0 og Atom. Andre formater afvises frem for at gætte."""
    head = data[:2048].lower()
    if any(marker in head for marker in _DTD_MARKERS):
        raise ApiError(502, "feed_invalid", "Feedet indeholder en DTD og behandles ikke.")

    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ApiError(502, "feed_invalid", "Feedet kunne ikke læses som XML.") from exc

    if root.tag == "rss":
        return _rss_entries(root)
    if root.tag == f"{_ATOM}feed":
        return _atom_entries(root)
    raise ApiError(502, "feed_invalid", "Feedet er hverken RSS 2.0 eller Atom.")
