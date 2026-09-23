"""Ingestion/AI-worker — samme codebase og domænelag som API'et.

Kørsel: `uv run python -m app.worker --once` (eller `--interval 300` for
loop). Én kørsel gør to ting:

1. Henter forfaldne, aktive rss- og web_fetch-kilder med access_class=public
   (next_check_at null eller passeret; frekvens manual springes over).
2. Kører relevans + claim extraction på normaliserede dokumenter, hvis en
   AI-provider er konfigureret.

Workeren har bevidst ingen adgang til mail, Teams, CRM eller write actions
i forretningssystemer (Technical Master §9).
"""

import argparse
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.ai.provider import get_ai_provider
from app.config import get_settings
from app.db import get_engine
from app.enums import AccessClass, Frequency, ProcessingStatus, RetrievalMethod
from app.errors import ApiError
from app.ingestion.run import run_source_fetch
from app.models import Document, Source
from app.pipeline.process import process_document
from app.storage import get_storage

logger = logging.getLogger("ai_radar.worker")

_FREQUENCY_INTERVAL: dict[Frequency, timedelta] = {
    Frequency.daily: timedelta(days=1),
    Frequency.weekly: timedelta(days=7),
    Frequency.monthly: timedelta(days=30),
}


@dataclass
class WorkerRunResult:
    sources_checked: int = 0
    documents_created: int = 0
    documents_unchanged: int = 0
    fetch_failures: int = 0
    documents_processed: int = 0
    processing_skipped_no_ai: bool = False


def _due_sources(db: Session, now: datetime) -> list[Source]:
    rows = db.scalars(
        select(Source).where(
            Source.active.is_(True),
            Source.retrieval_method.in_((RetrievalMethod.rss, RetrievalMethod.web_fetch)),
            Source.access_class == AccessClass.public,
            Source.frequency != Frequency.manual,
        )
    ).all()
    return [s for s in rows if s.next_check_at is None or s.next_check_at <= now]


def _check_source(db: Session, source: Source, result: WorkerRunResult) -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    try:
        outcome = run_source_fetch(
            db,
            get_storage(),
            source,
            timeout_seconds=settings.fetch_timeout_seconds,
            max_bytes=settings.fetch_max_bytes,
            max_items=settings.rss_max_items,
        )
        result.documents_created += outcome.created_count
        result.documents_unchanged += outcome.unchanged_count
        result.fetch_failures += len(outcome.failures)
        for failure in outcome.failures:
            logger.warning("entry_fetch_failed source=%s code=%s", source.id, failure.code)
    except ApiError as exc:
        result.fetch_failures += 1
        logger.warning("source_check_failed source=%s code=%s", source.id, exc.code)
    finally:
        source.last_checked_at = now
        interval = _FREQUENCY_INTERVAL.get(source.frequency)
        if interval is not None:
            source.next_check_at = now + interval
        result.sources_checked += 1


def run_once() -> WorkerRunResult:
    result = WorkerRunResult()
    factory = sessionmaker(bind=get_engine())
    provider = get_ai_provider()

    with factory() as db:
        for source in _due_sources(db, datetime.now(UTC)):
            _check_source(db, source, result)
            db.commit()

        if provider is None:
            result.processing_skipped_no_ai = True
        else:
            pending = db.scalars(
                select(Document).where(Document.processing_status == ProcessingStatus.normalized)
            ).all()
            for document in pending:
                try:
                    process_document(db, provider, document)
                except ApiError as exc:
                    if exc.code != "ai_provider_rejected":
                        raise
                    # Nøgle/model/kvote er forkert: alle dokumenter vil fejle ens,
                    # så kørslen stopper i stedet for at gentage fejlen pr. dokument.
                    db.rollback()
                    logger.error("ai_provider_rejected message=%s", exc.message)
                    break
                db.commit()
                result.documents_processed += 1

    logger.info(
        "worker_run sources=%d created=%d unchanged=%d failures=%d processed=%d",
        result.sources_checked,
        result.documents_created,
        result.documents_unchanged,
        result.fetch_failures,
        result.documents_processed,
    )
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="AI Radar ingestion/AI-worker")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--once", action="store_true", help="Kør én gang og stop")
    group.add_argument("--interval", type=int, metavar="SEKUNDER", help="Kør i loop med interval")
    args = parser.parse_args()

    if args.once:
        run_once()
        return
    while True:
        run_once()
        time.sleep(max(args.interval, 30))


if __name__ == "__main__":
    main()
