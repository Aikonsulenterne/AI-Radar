"""Source Registry-endpoints (Technical Master §11).

Læsning kræver Reader; administration kræver Admin. Authorization håndhæves
eksplicit server-side, uanset at backenden bruger en server-credential.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import AuditAction, AuditEntity, field_changes, record
from app.auth import CurrentUser, require_role
from app.config import get_settings
from app.db import get_db
from app.enums import AccessClass, RetrievalMethod, UserRole
from app.errors import ApiError
from app.ingestion.run import run_source_fetch
from app.ingestion.service import ingest_bytes
from app.models import Source
from app.schemas import (
    DocumentOut,
    IngestOutcome,
    Paginated,
    RunDocumentOut,
    RunFailureOut,
    RunResult,
    SourceCreate,
    SourceOut,
    SourceUpdate,
)
from app.storage import get_storage

router = APIRouter(prefix="/sources", tags=["sources"])

_ALLOWED_UPLOAD_MIME = {"text/plain", "text/html", "application/pdf"}


def _get_source_or_404(db: Session, source_id: uuid.UUID) -> Source:
    source = db.get(Source, source_id)
    if source is None:
        raise ApiError(404, "not_found", "Kilden findes ikke.")
    return source


@router.get("", response_model=Paginated[SourceOut])
def list_sources(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: object = Depends(require_role(UserRole.reader)),
) -> Paginated[SourceOut]:
    stmt = select(Source).order_by(Source.name)
    if active is not None:
        stmt = stmt.where(Source.active == active)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.limit(limit).offset(offset)).all()
    return Paginated[SourceOut](
        items=[SourceOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=SourceOut, status_code=201)
def create_source(
    body: SourceCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> SourceOut:
    source = Source(
        name=body.name,
        base_url=body.base_url,
        source_type=body.source_type,
        retrieval_method=body.retrieval_method,
        endpoint_url=body.endpoint_url,
        country_code=body.country_code,
        frequency=body.frequency,
        access_class=body.access_class,
        active=body.active,
        notes=body.notes,
    )
    db.add(source)
    db.flush()
    record(
        db,
        entity_type=AuditEntity.source,
        entity_id=source.id,
        action=AuditAction.created,
        actor_user_id=user.user_id,
        changes={"name": source.name, "retrieval_method": source.retrieval_method.value},
    )
    return SourceOut.model_validate(source)


@router.patch("/{source_id}", response_model=SourceOut)
def update_source(
    source_id: uuid.UUID,
    body: SourceUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> SourceOut:
    source = _get_source_or_404(db, source_id)
    updates = body.model_dump(exclude_unset=True)
    before = {field: getattr(source, field) for field in updates}
    for field, value in updates.items():
        setattr(source, field, value)
    if source.retrieval_method in (RetrievalMethod.rss, RetrievalMethod.web_fetch):
        if not source.endpoint_url:
            raise ApiError(422, "validation_error", "endpoint_url er påkrævet for rss/web_fetch.")
    db.flush()
    changed = field_changes(before, updates)
    if changed:
        record(
            db,
            entity_type=AuditEntity.source,
            entity_id=source.id,
            action=AuditAction.updated,
            actor_user_id=user.user_id,
            changes=changed,
        )
    return SourceOut.model_validate(source)


@router.post("/{source_id}/run", response_model=RunResult)
def run_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> RunResult:
    settings = get_settings()
    source = _get_source_or_404(db, source_id)

    if not source.active:
        raise ApiError(409, "source_inactive", "Kilden er deaktiveret.")
    if source.retrieval_method == RetrievalMethod.manual_upload:
        raise ApiError(409, "manual_source", "Kilden bruger manuel upload — brug upload i stedet.")
    if source.access_class != AccessClass.public:
        # Licensed/restricted: snapshot-lagring afventer afklaring af vilkår
        # (Technical Master §14). Håndteres manuelt indtil da.
        raise ApiError(
            409, "access_restricted", "Kun public kilder kan hentes automatisk i denne version."
        )
    try:
        outcome = run_source_fetch(
            db,
            get_storage(),
            source,
            timeout_seconds=settings.fetch_timeout_seconds,
            max_bytes=settings.fetch_max_bytes,
            max_items=settings.rss_max_items,
        )
    except ApiError:
        source.last_checked_at = datetime.now(UTC)
        db.commit()
        raise

    source.last_checked_at = datetime.now(UTC)
    db.flush()
    record(
        db,
        entity_type=AuditEntity.source,
        entity_id=source.id,
        action=AuditAction.fetched,
        actor_user_id=user.user_id,
        changes={
            "nye_dokumenter": outcome.created_count,
            "uændrede": outcome.unchanged_count,
            "fejlede_links": len(outcome.failures),
        },
    )
    return RunResult(
        source_id=source.id,
        documents=[
            RunDocumentOut(document=DocumentOut.model_validate(item.document), created=item.created)
            for item in outcome.documents
        ],
        created_count=outcome.created_count,
        unchanged_count=outcome.unchanged_count,
        failures=[
            RunFailureOut(url=failure.url, code=failure.code, message=failure.message)
            for failure in outcome.failures
        ],
    )


@router.post("/{source_id}/documents", response_model=IngestOutcome)
def upload_document(
    source_id: uuid.UUID,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    db: Session = Depends(get_db),
    _user: object = Depends(require_role(UserRole.admin)),
) -> IngestOutcome:
    """Manuel upload (Technical Master §8). Filtype og størrelse valideres."""
    settings = get_settings()
    source = _get_source_or_404(db, source_id)
    if not source.active:
        raise ApiError(409, "source_inactive", "Kilden er deaktiveret.")

    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise ApiError(413, "upload_too_large", "Filen overskrider størrelsesgrænsen.")
    if not data:
        raise ApiError(422, "validation_error", "Filen er tom.")

    content_type = (file.content_type or "application/octet-stream").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_UPLOAD_MIME:
        raise ApiError(
            415,
            "unsupported_media_type",
            "Kun text/plain, text/html og application/pdf understøttes.",
        )

    result = ingest_bytes(
        db,
        get_storage(),
        source,
        data,
        content_type,
        title=title or file.filename,
    )
    return IngestOutcome(
        document=DocumentOut.model_validate(result.document),
        created=result.created,
    )
