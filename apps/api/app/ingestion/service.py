"""Ingestion-service: raw bytes → gemt råfil + normaliseret Document-række.

Idempotency: kendt (source_id, content_hash) stopper ingestion og returnerer
den eksisterende række (Technical Master §5, §8).
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import ProcessingStatus
from app.ingestion.hashing import sha256_hex
from app.ingestion.normalize import extract_text
from app.models import Document, Source
from app.storage import StorageAdapter

_EXTENSIONS = {
    "text/plain": ".txt",
    "text/html": ".html",
    "application/xhtml+xml": ".html",
    "application/pdf": ".pdf",
}


@dataclass(frozen=True)
class IngestResult:
    document: Document
    created: bool


def ingest_bytes(
    db: Session,
    storage: StorageAdapter,
    source: Source,
    data: bytes,
    content_type: str,
    *,
    canonical_url: str | None = None,
    title: str | None = None,
) -> IngestResult:
    content_hash = sha256_hex(data)

    existing = db.scalar(
        select(Document).where(
            Document.source_id == source.id, Document.content_hash == content_hash
        )
    )
    if existing is not None:
        return IngestResult(document=existing, created=False)

    mime = content_type.split(";")[0].strip().lower()
    raw_path = f"{source.id}/{content_hash}{_EXTENSIONS.get(mime, '.bin')}"
    storage.save(raw_path, data, mime)

    normalized = extract_text(mime, data)
    status = ProcessingStatus.normalized if normalized.text else ProcessingStatus.fetched

    document = Document(
        source_id=source.id,
        canonical_url=canonical_url,
        title=title or normalized.title,
        retrieved_at=datetime.now(UTC),
        content_hash=content_hash,
        raw_storage_path=raw_path,
        normalized_text=normalized.text,
        mime_type=mime,
        processing_status=status,
    )
    db.add(document)
    db.flush()
    return IngestResult(document=document, created=True)
