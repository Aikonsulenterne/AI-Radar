"""Kørsel af en kilde: web_fetch henter ét dokument, rss henter feedets artikler.

Samme domænelag bruges af API-endpointet og workeren (Technical Master §2:
API og worker deler codebase). Feed-niveau-fejl afbryder kørslen; fejl på et
enkelt artikellink samles op, så resten af feedet stadig hentes.
"""

import html
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.enums import RetrievalMethod
from app.errors import ApiError
from app.ingestion.feed import FeedEntry, parse_feed
from app.ingestion.fetch import ensure_public_http_url, fetch_url
from app.ingestion.service import ingest_bytes
from app.models import Document, Source
from app.storage import StorageAdapter


@dataclass(frozen=True)
class RunDocument:
    document: Document
    created: bool


@dataclass(frozen=True)
class RunFailure:
    url: str
    code: str
    message: str


@dataclass
class SourceRunOutcome:
    documents: list[RunDocument] = field(default_factory=list)
    failures: list[RunFailure] = field(default_factory=list)

    @property
    def created_count(self) -> int:
        return sum(1 for item in self.documents if item.created)

    @property
    def unchanged_count(self) -> int:
        return sum(1 for item in self.documents if not item.created)


def _fetch_and_ingest(
    db: Session,
    storage: StorageAdapter,
    source: Source,
    url: str,
    *,
    timeout_seconds: float,
    max_bytes: int,
    title: str | None = None,
) -> RunDocument:
    fetched = fetch_url(url, timeout_seconds=timeout_seconds, max_bytes=max_bytes)
    result = ingest_bytes(
        db,
        storage,
        source,
        fetched.data,
        fetched.content_type,
        canonical_url=fetched.final_url,
        title=title,
    )
    return RunDocument(document=result.document, created=result.created)


# Fejl, hvor udgiverens egen tekst i feedet kan bruges i stedet for siden
# (fx 403 fra bot-beskyttelse). unsafe_url er aldrig en af dem.
_FALLBACK_CODES = {"fetch_failed", "fetch_too_large"}
# Et resumé kortere end dette er typisk kun en teaser uden fakta.
_MIN_FEED_TEXT_CHARS = 200


def _ingest_feed_text(
    db: Session, storage: StorageAdapter, source: Source, entry: FeedEntry
) -> RunDocument | None:
    """Gem feedets egen tekst for et entry, hvis artikelsiden ikke kan hentes.

    Det er udgiverens offentliggjorte tekst i deres eget feed — ingen omgåelse
    af adgangskontrol. Linket bevares som kanonisk URL, så evidensen kan
    spores til artiklen.
    """
    summary = entry.summary or ""
    if len(summary) < _MIN_FEED_TEXT_CHARS:
        return None
    title = html.escape(entry.title or "")
    document = (
        f"<html><head><title>{title}</title></head><body><h1>{title}</h1>{summary}</body></html>"
    ).encode()
    result = ingest_bytes(
        db,
        storage,
        source,
        document,
        "text/html; charset=utf-8",
        canonical_url=entry.link,
        title=entry.title,
    )
    return RunDocument(document=result.document, created=result.created)


def _run_rss(
    db: Session,
    storage: StorageAdapter,
    source: Source,
    endpoint_url: str,
    *,
    timeout_seconds: float,
    max_bytes: int,
    max_items: int,
) -> SourceRunOutcome:
    feed = fetch_url(endpoint_url, timeout_seconds=timeout_seconds, max_bytes=max_bytes)
    outcome = SourceRunOutcome()

    for entry in parse_feed(feed.data)[:max_items]:
        if not entry.link:
            outcome.failures.append(
                RunFailure(url="", code="missing_link", message="Entry uden link springes over.")
            )
            continue
        try:
            ensure_public_http_url(entry.link)
            run_document = _fetch_and_ingest(
                db,
                storage,
                source,
                entry.link,
                timeout_seconds=timeout_seconds,
                max_bytes=max_bytes,
                title=entry.title,
            )
        except ApiError as exc:
            fallback = (
                _ingest_feed_text(db, storage, source, entry)
                if exc.code in _FALLBACK_CODES
                else None
            )
            if fallback is None:
                outcome.failures.append(
                    RunFailure(url=entry.link, code=exc.code, message=exc.message)
                )
                continue
            run_document = fallback

        # Udgivelsestidspunktet er et dokumenteret faktum fra feedet; mangler
        # det, forbliver feltet null frem for at blive gættet.
        if run_document.created and entry.published_at is not None:
            run_document.document.published_at = entry.published_at
        outcome.documents.append(run_document)

    db.flush()
    return outcome


def run_source_fetch(
    db: Session,
    storage: StorageAdapter,
    source: Source,
    *,
    timeout_seconds: float,
    max_bytes: int,
    max_items: int,
) -> SourceRunOutcome:
    """Henter kilden. Kalderen har ansvaret for rolle- og tilstandstjek."""
    if not source.endpoint_url:
        raise ApiError(422, "validation_error", "Kilden mangler endpoint_url.")

    if source.retrieval_method == RetrievalMethod.rss:
        return _run_rss(
            db,
            storage,
            source,
            source.endpoint_url,
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
            max_items=max_items,
        )

    run_document = _fetch_and_ingest(
        db,
        storage,
        source,
        source.endpoint_url,
        timeout_seconds=timeout_seconds,
        max_bytes=max_bytes,
    )
    db.flush()
    return SourceRunOutcome(documents=[run_document])
