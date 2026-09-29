"""Ingestion/AI-worker — samme codebase og domænelag som API'et.

Kørsel: `uv run python -m app.worker --once` (eller `--interval 300` for
loop; `--all` henter alle aktive kilder nu). I drift på free tier udløses
kørsler via `POST /api/v1/runs` — ugentligt fra GitHub Actions og on demand
fra admin. Hver kørsel logges i worker_runs. Én kørsel gør to ting:

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
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.ai.provider import AIProvider, get_ai_provider
from app.config import get_settings
from app.db import get_engine
from app.enums import (
    AccessClass,
    Frequency,
    ProcessingStatus,
    RetrievalMethod,
    RunStatus,
    RunTrigger,
)
from app.errors import ApiError
from app.ingestion.run import run_source_fetch
from app.models import Document, Source
from app.models_runs import WorkerRun
from app.pipeline.autopublish import autopublish_document
from app.pipeline.process import abort_processing, begin_processing, process_document
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
    # Dokumenter publiceret automatisk (AUTO_PUBLISH), inkl. ventende backlog.
    documents_published: int = 0
    processing_skipped_no_ai: bool = False


def _due_sources(db: Session, now: datetime, *, force_all: bool = False) -> list[Source]:
    """Kilder der skal hentes nu.

    Planlagt kørsel: aktive kilder, hvis frekvens er forfalden. force_all
    ("Kør nu"): alle aktive kilder, også manuelle, uanset næste kontrol.
    """
    stmt = select(Source).where(
        Source.active.is_(True),
        Source.retrieval_method.in_((RetrievalMethod.rss, RetrievalMethod.web_fetch)),
        Source.access_class == AccessClass.public,
    )
    if force_all:
        return list(db.scalars(stmt).all())
    rows = db.scalars(stmt.where(Source.frequency != Frequency.manual)).all()
    return [s for s in rows if s.next_check_at is None or _aware(s.next_check_at) <= now]


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


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


class RunAborted(Exception):
    """Kørslen stoppede af en årsag, der kan vises (ingen secrets)."""


def run_once(
    session_factory: sessionmaker[Session] | None = None,
    provider: AIProvider | None = None,
    *,
    force_all: bool = False,
    use_configured_provider: bool = True,
    result: WorkerRunResult | None = None,
) -> WorkerRunResult:
    """Hent kilder og AI-behandl nye dokumenter. Kaster RunAborted, hvis
    AI-udbyderen afviser kaldet (nøgle, model eller kvote). Tællingerne
    ligger i result, også hvis kørslen stopper undervejs."""
    result = result if result is not None else WorkerRunResult()
    factory = session_factory or sessionmaker(bind=get_engine())
    if provider is None and use_configured_provider:
        provider = get_ai_provider()

    with factory() as db:
        for source in _due_sources(db, datetime.now(UTC), force_all=force_all):
            _check_source(db, source, result)
            db.commit()

        if provider is None:
            result.processing_skipped_no_ai = True
        else:
            pending = db.scalars(
                select(Document).where(Document.processing_status == ProcessingStatus.normalized)
            ).all()
            for document_id in [document.id for document in pending]:
                try:
                    document, previous = begin_processing(db, document_id)
                except ApiError:
                    # Behandles allerede fra admin-UI'et, eller status er ændret.
                    db.rollback()
                    continue
                try:
                    process_document(db, provider, document)
                except ApiError as exc:
                    abort_processing(db, document, previous)
                    if exc.code != "ai_provider_rejected":
                        raise
                    # Nøgle/model/kvote er forkert: alle dokumenter vil fejle ens,
                    # så kørslen stopper i stedet for at gentage fejlen pr. dokument.
                    logger.error("ai_provider_rejected message=%s", exc.message)
                    raise RunAborted(exc.message) from exc
                db.commit()
                result.documents_processed += 1

            if get_settings().auto_publish:
                _publish_backlog(db, provider, result)

    logger.info(
        "worker_run sources=%d created=%d unchanged=%d failures=%d processed=%d",
        result.sources_checked,
        result.documents_created,
        result.documents_unchanged,
        result.fetch_failures,
        result.documents_processed,
    )
    return result


def _publish_backlog(db: Session, provider: AIProvider, result: WorkerRunResult) -> None:
    """Med AUTO_PUBLISH: publicér dokumenter, hvis claims venter på review —
    fx dem, der blev behandlet, før automatisk publicering blev slået til."""
    waiting = db.scalars(
        select(Document.id).where(
            Document.processing_status.in_(
                (ProcessingStatus.review_pending, ProcessingStatus.partially_reviewed)
            )
        )
    ).all()
    for document_id in waiting:
        document = db.get(Document, document_id)
        if document is None:
            continue
        outcome = autopublish_document(db, provider, document)
        db.commit()
        if outcome.claims_approved:
            result.documents_published += 1


# En kørsel, der stadig står som running efter dette, er død undervejs
# (fx genstart af serveren) og blokerer ikke en ny.
STALE_RUN_AFTER = timedelta(hours=2)


def start_run(
    db: Session,
    *,
    trigger: RunTrigger,
    force_all: bool,
    started_by: uuid.UUID | None = None,
) -> WorkerRun:
    """Opret og commit en kørsel. 409, hvis en anden kørsel er i gang."""
    cutoff = datetime.now(UTC) - STALE_RUN_AFTER
    running = db.scalars(select(WorkerRun).where(WorkerRun.status == RunStatus.running)).all()
    if any(_aware(run.started_at) > cutoff for run in running):
        raise ApiError(
            409,
            "run_in_progress",
            "En kørsel er allerede i gang. Vent, til den er færdig.",
        )
    for stale in running:
        stale.status = RunStatus.failed
        stale.finished_at = datetime.now(UTC)
        stale.error_message_safe = "Kørslen blev afbrudt (fx genstart af serveren)."

    run = WorkerRun(
        trigger=trigger,
        force_all=force_all,
        status=RunStatus.running,
        started_at=datetime.now(UTC),
        started_by_user_id=started_by,
    )
    db.add(run)
    db.commit()
    return run


def execute_run(
    session_factory: sessionmaker[Session],
    provider: AIProvider | None,
    run_id: uuid.UUID,
) -> None:
    """Udfør en oprettet kørsel og gem resultatet. Kaster aldrig."""
    with session_factory() as db:
        run = db.get(WorkerRun, run_id)
        if run is None:
            return
        force_all = run.force_all

    status = RunStatus.succeeded
    error: str | None = None
    result = WorkerRunResult()
    try:
        run_once(
            session_factory,
            provider,
            force_all=force_all,
            use_configured_provider=False,
            result=result,
        )
    except RunAborted as exc:
        status, error = RunStatus.failed, f"AI-udbyderen afviste kaldet: {exc}"
    except Exception as exc:  # noqa: BLE001 — kørslen skal altid afsluttes i loggen
        logger.exception("worker_run_failed run=%s", run_id)
        status, error = RunStatus.failed, f"Uventet fejl ({exc.__class__.__name__})."

    with session_factory() as db:
        run = db.get(WorkerRun, run_id)
        if run is None:
            return
        run.status = status
        run.finished_at = datetime.now(UTC)
        run.error_message_safe = error
        run.sources_checked = result.sources_checked
        run.documents_created = result.documents_created
        run.documents_unchanged = result.documents_unchanged
        run.fetch_failures = result.fetch_failures
        run.documents_processed = result.documents_processed
        run.documents_published = result.documents_published
        run.processing_skipped_no_ai = result.processing_skipped_no_ai
        db.commit()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="AI Radar ingestion/AI-worker")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--once", action="store_true", help="Kør én gang og stop")
    group.add_argument("--interval", type=int, metavar="SEKUNDER", help="Kør i loop med interval")
    parser.add_argument(
        "--all", action="store_true", help="Hent alle aktive kilder nu, uanset frekvens"
    )
    args = parser.parse_args()

    factory = sessionmaker(bind=get_engine())
    provider = get_ai_provider()

    def run() -> None:
        with factory() as db:
            try:
                created = start_run(db, trigger=RunTrigger.cli, force_all=args.all)
            except ApiError as exc:
                logger.warning("worker_run_skipped reason=%s", exc.code)
                return
        execute_run(factory, provider, created.id)

    if args.once:
        run()
        return
    while True:
        run()
        time.sleep(max(args.interval, 30))


if __name__ == "__main__":
    main()
