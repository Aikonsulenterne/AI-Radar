"""Kørsel af en kilde: web_fetch henter ét dokument, rss henter feedets artikler.

Samme domænelag bruges af API-endpointet og workeren (Technical Master §2:
API og worker deler codebase). Feed-niveau-fejl afbryder kørslen; fejl på et
enkelt artikellink samles op, så resten af feedet stadig hentes.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.enums import RetrievalMethod
from app.errors import ApiError
from app.ingestion.feed import parse_feed
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
            outcome.failures.append(RunFailure(url=entry.link, code=exc.code, message=exc.message))
            continue

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
