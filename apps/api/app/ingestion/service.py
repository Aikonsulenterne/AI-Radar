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


# Andel af tekstlinjer, der skal være ens, før en ny hentning af samme URL
# regnes for samme indhold.
_SAME_CONTENT_THRESHOLD = 0.9


def _materially_same(old: str | None, new: str) -> bool:
    """Linjebaseret Jaccard-lighed mellem to normaliserede tekster."""
    if not old:
        return False
    old_lines = {line.strip() for line in old.splitlines() if line.strip()}
    new_lines = {line.strip() for line in new.splitlines() if line.strip()}
    if not old_lines or not new_lines:
        return old.strip() == new.strip()
    overlap = len(old_lines & new_lines) / len(old_lines | new_lines)
    return overlap >= _SAME_CONTENT_THRESHOLD


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
    normalized = extract_text(mime, data)

    if canonical_url and normalized.text:
        previous = db.scalars(
            select(Document)
            .where(Document.source_id == source.id, Document.canonical_url == canonical_url)
            .order_by(Document.retrieved_at.desc())
            .limit(1)
        ).first()
        if previous is not None and _materially_same(previous.normalized_text, normalized.text):
            # Samme side med ny markup (scripts, tokens, tidsstempler): ikke et
            # nyt dokument. Ellers ville en produktside blive genbehandlet og
            # give dublerede claims hver uge.
            return IngestResult(document=previous, created=False)

    raw_path = f"{source.id}/{content_hash}{_EXTENSIONS.get(mime, '.bin')}"
    storage.save(raw_path, data, mime)

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
