"""Review-endpoints (Technical Master §11).

Review samles pr. dokument: metadata, normaliseret tekst, foreslåede claims
med evidensuddrag og duplicate-kandidater. Kun godkendte claims kan senere
publiceres som fakta.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.provider import AIProvider, get_ai_provider
from app.auth import CurrentUser, require_role
from app.db import get_db
from app.enums import (
    PREDICATES_BY_CLAIM_TYPE,
    ProcessingStatus,
    ReviewStatus,
    UserRole,
)
from app.errors import ApiError
from app.models import Document
from app.models_claims import Claim, ClaimEvidence
from app.pipeline.entities import entity_name
from app.pipeline.process import process_document
from app.schemas import DocumentOut, Paginated
from app.schemas_claims import (
    ApproveRequest,
    ClaimEdit,
    ClaimOut,
    DocumentReviewOut,
    EvidenceOut,
    ProcessResult,
)
from app.storage import get_storage

router = APIRouter(prefix="/review", tags=["review"])

_PATCHABLE_REVIEW_STATUSES = {ReviewStatus.proposed, ReviewStatus.needs_corroboration}


def ai_provider_dep() -> AIProvider:
    provider = get_ai_provider()
    if provider is None:
        raise ApiError(
            503,
            "ai_not_configured",
            "AI-provider er ikke konfigureret (AI_PROVIDER_BASE_URL/AI_MODEL_ID).",
        )
    return provider


def _possible_duplicates(db: Session, claim: Claim) -> list[uuid.UUID]:
    stmt = select(Claim.id).where(
        Claim.id != claim.id,
        Claim.subject_entity_type == claim.subject_entity_type,
        Claim.subject_entity_id == claim.subject_entity_id,
        Claim.predicate == claim.predicate,
        Claim.review_status != ReviewStatus.rejected,
    )
    if claim.object_entity_id is not None:
        stmt = stmt.where(Claim.object_entity_id == claim.object_entity_id)
    elif claim.object_text is not None:
        stmt = stmt.where(func.lower(Claim.object_text) == claim.object_text.casefold())
    else:
        return []
    return list(db.scalars(stmt).all())


def _claim_out(db: Session, claim: Claim) -> ClaimOut:
    evidence_rows = db.scalars(
        select(ClaimEvidence).where(ClaimEvidence.claim_id == claim.id)
    ).all()
    out = ClaimOut.model_validate(claim)
    return out.model_copy(
        update={
            "subject_name": entity_name(db, claim.subject_entity_type, claim.subject_entity_id),
            "object_name": entity_name(db, claim.object_entity_type, claim.object_entity_id),
            "evidence": [EvidenceOut.model_validate(row) for row in evidence_rows],
            "possible_duplicate_ids": _possible_duplicates(db, claim),
        }
    )


def _get_claim_or_404(db: Session, claim_id: uuid.UUID) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise ApiError(404, "not_found", "Claimet findes ikke.")
    return claim


def _apply_edits(db: Session, claim: Claim, edits: ClaimEdit) -> bool:
    """Anvend reviewer-rettelser; returnér om noget blev ændret."""
    updates = edits.model_dump(exclude_unset=True)
    status_update = updates.pop("review_status", None)
    if status_update is not None:
        if status_update not in _PATCHABLE_REVIEW_STATUSES:
            raise ApiError(
                422,
                "validation_error",
                "review_status kan kun sættes til proposed eller needs_corroboration her.",
            )
        claim.review_status = status_update

    changed = False
    for field_name, value in updates.items():
        if getattr(claim, field_name) != value:
            setattr(claim, field_name, value)
            changed = True

    if claim.predicate not in PREDICATES_BY_CLAIM_TYPE[claim.claim_type]:
        raise ApiError(
            422, "validation_error", "predicate passer ikke til claim_type efter rettelsen."
        )
    db.flush()
    return changed


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


@router.get("/claims", response_model=Paginated[ClaimOut])
def list_claims(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    review_status: ReviewStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: object = Depends(require_role(UserRole.reviewer)),
) -> Paginated[ClaimOut]:
    """Claims på tværs af dokumenter — bl.a. til signalbyggerens claim-valg."""
    stmt = select(Claim).order_by(Claim.created_at.desc())
    if review_status is not None:
        stmt = stmt.where(Claim.review_status == review_status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.limit(limit).offset(offset)).all()
    return Paginated[ClaimOut](
        items=[_claim_out(db, row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/documents/{document_id}", response_model=DocumentReviewOut)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: object = Depends(require_role(UserRole.reviewer)),
) -> DocumentReviewOut:
    document = db.get(Document, document_id)
    if document is None:
        raise ApiError(404, "not_found", "Dokumentet findes ikke.")

    claim_ids = db.scalars(
        select(ClaimEvidence.claim_id).where(ClaimEvidence.document_id == document.id).distinct()
    ).all()
    claims = [
        _claim_out(db, claim)
        for claim_id in claim_ids
        if (claim := db.get(Claim, claim_id)) is not None
    ]

    detail = DocumentReviewOut.model_validate(document)
    raw_url = (
        get_storage().signed_url(document.raw_storage_path) if document.raw_storage_path else None
    )
    return detail.model_copy(update={"raw_url": raw_url, "claims": claims})


@router.post("/documents/{document_id}/process", response_model=ProcessResult)
def process_document_endpoint(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    provider: AIProvider = Depends(ai_provider_dep),
    _user: object = Depends(require_role(UserRole.admin)),
) -> ProcessResult:
    """Kør relevans + claim extraction for et normaliseret dokument.

    Lokalt implementeringsvalg: synkron kørsel i API'et; planlagt/asynkron
    behandling via worker kommer senere (docs/05_Implementation_Notes.md).
    """
    document = db.get(Document, document_id)
    if document is None:
        raise ApiError(404, "not_found", "Dokumentet findes ikke.")
    allowed = {
        ProcessingStatus.normalized,
        ProcessingStatus.classified_relevant,
        ProcessingStatus.failed,
    }
    if document.processing_status not in allowed:
        raise ApiError(
            409,
            "invalid_status",
            f"Dokumentet kan ikke behandles i status '{document.processing_status}'.",
        )

    outcome = process_document(db, provider, document)
    return ProcessResult(
        document_id=document.id,
        status=outcome.status,
        claims_created=outcome.claims_created,
        claims_skipped=outcome.claims_skipped,
        skipped_reasons=outcome.skipped_reasons,
    )


@router.post("/documents/{document_id}/complete", response_model=DocumentOut)
def complete_document_review(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: object = Depends(require_role(UserRole.reviewer)),
) -> DocumentOut:
    document = db.get(Document, document_id)
    if document is None:
        raise ApiError(404, "not_found", "Dokumentet findes ikke.")
    if document.processing_status not in {
        ProcessingStatus.review_pending,
        ProcessingStatus.partially_reviewed,
    }:
        raise ApiError(409, "invalid_status", "Dokumentet er ikke i review.")

    open_claims = db.scalar(
        select(func.count())
        .select_from(Claim)
        .join(ClaimEvidence, ClaimEvidence.claim_id == Claim.id)
        .where(
            ClaimEvidence.document_id == document.id,
            Claim.review_status == ReviewStatus.proposed,
        )
    )
    document.processing_status = (
        ProcessingStatus.partially_reviewed if open_claims else ProcessingStatus.reviewed
    )
    db.flush()
    return DocumentOut.model_validate(document)


@router.patch("/claims/{claim_id}", response_model=ClaimOut)
def edit_claim(
    claim_id: uuid.UUID,
    body: ClaimEdit,
    db: Session = Depends(get_db),
    _user: object = Depends(require_role(UserRole.reviewer)),
) -> ClaimOut:
    claim = _get_claim_or_404(db, claim_id)
    if claim.review_status not in _PATCHABLE_REVIEW_STATUSES:
        raise ApiError(409, "invalid_status", "Kun åbne claims kan rettes.")
    _apply_edits(db, claim, body)
    return _claim_out(db, claim)


@router.post("/claims/{claim_id}/approve", response_model=ClaimOut)
def approve_claim(
    claim_id: uuid.UUID,
    body: ApproveRequest | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reviewer)),
) -> ClaimOut:
    """Approve betyder: revieweren har vurderet claimet som korrekt gengivelse
    af evidensuddraget — ikke uafhængigt bevist sandhed (Technical Master §6)."""
    claim = _get_claim_or_404(db, claim_id)
    if claim.review_status not in _PATCHABLE_REVIEW_STATUSES:
        raise ApiError(409, "invalid_status", "Claimet er allerede afgjort.")

    edited = False
    if body is not None and body.edits is not None:
        edited = _apply_edits(db, claim, body.edits)

    claim.review_status = ReviewStatus.approved_with_edits if edited else ReviewStatus.approved
    claim.reviewed_by_user_id = user.user_id
    claim.reviewed_at = datetime.now(UTC)
    for evidence in db.scalars(
        select(ClaimEvidence).where(ClaimEvidence.claim_id == claim.id)
    ).all():
        evidence.review_status = claim.review_status
    db.flush()
    return _claim_out(db, claim)


@router.post("/claims/{claim_id}/reject", response_model=ClaimOut)
def reject_claim(
    claim_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reviewer)),
) -> ClaimOut:
    claim = _get_claim_or_404(db, claim_id)
    if claim.review_status not in _PATCHABLE_REVIEW_STATUSES:
        raise ApiError(409, "invalid_status", "Claimet er allerede afgjort.")
    claim.review_status = ReviewStatus.rejected
    claim.reviewed_by_user_id = user.user_id
    claim.reviewed_at = datetime.now(UTC)
    for evidence in db.scalars(
        select(ClaimEvidence).where(ClaimEvidence.claim_id == claim.id)
    ).all():
        evidence.review_status = ReviewStatus.rejected
    db.flush()
    return _claim_out(db, claim)
