"""Dokumentvisning til review (Technical Master §11: GET /review/documents).

Review-handlinger på claims kommer i Slice 2; her vises pipeline-status og
provenance (original fil via kortvarig signeret URL).
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_role
from app.db import get_db
from app.enums import ProcessingStatus, UserRole
from app.errors import ApiError
from app.models import Document
from app.schemas import DocumentDetailOut, DocumentOut, Paginated
from app.storage import get_storage

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/documents", response_model=Paginated[DocumentOut])
def list_documents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    source_id: uuid.UUID | None = Query(default=None),
    processing_status: ProcessingStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: object = Depends(require_role(UserRole.reviewer)),
) -> Paginated[DocumentOut]:
    stmt = select(Document).order_by(Document.retrieved_at.desc())
    if source_id is not None:
        stmt = stmt.where(Document.source_id == source_id)
    if processing_status is not None:
        stmt = stmt.where(Document.processing_status == processing_status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.limit(limit).offset(offset)).all()
    return Paginated[DocumentOut](
        items=[DocumentOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/documents/{document_id}", response_model=DocumentDetailOut)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: object = Depends(require_role(UserRole.reviewer)),
) -> DocumentDetailOut:
    document = db.get(Document, document_id)
    if document is None:
        raise ApiError(404, "not_found", "Dokumentet findes ikke.")
    detail = DocumentDetailOut.model_validate(document)
    if document.raw_storage_path:
        raw_url = get_storage().signed_url(document.raw_storage_path)
        detail = detail.model_copy(update={"raw_url": raw_url})
    return detail
