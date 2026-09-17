"""Schemas for claims, evidens og review-handlinger."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.enums import (
    ClaimCreatedBy,
    ClaimLifecycle,
    ClaimType,
    EntityType,
    EvidenceRelationship,
    Predicate,
    ProcessingStatus,
    ReviewStatus,
    SourceType,
)


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    supporting_excerpt: str
    excerpt_start: int | None
    excerpt_end: int | None
    relationship: EvidenceRelationship
    source_type_snapshot: SourceType | None
    review_status: ReviewStatus


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    claim_type: ClaimType
    predicate: Predicate
    subject_entity_type: EntityType
    subject_entity_id: uuid.UUID
    # Navne slås op ved serialisering, så revieweren ser entiteter, ikke id'er.
    subject_name: str | None = None
    object_entity_type: EntityType | None
    object_entity_id: uuid.UUID | None
    object_name: str | None = None
    object_text: str | None
    normalized_value: dict[str, Any] | None
    valid_from: date | None
    valid_to: date | None
    observed_at: datetime
    review_status: ReviewStatus
    lifecycle_status: ClaimLifecycle
    created_by: ClaimCreatedBy
    reviewed_at: datetime | None
    evidence: list[EvidenceOut] = Field(default_factory=list)
    # Deterministisk fundne kandidater (samme subjekt+predicate+objekt) —
    # reviewer afgør relationen (Technical Master §15).
    possible_duplicate_ids: list[uuid.UUID] = Field(default_factory=list)


class ClaimEdit(BaseModel):
    """Reviewer-rettelser. Kun felter, en reviewer må ændre."""

    claim_type: ClaimType | None = None
    predicate: Predicate | None = None
    object_text: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    review_status: ReviewStatus | None = Field(
        default=None,
        description="Kun 'proposed' eller 'needs_corroboration' via PATCH.",
    )


class ApproveRequest(BaseModel):
    """Approve, evt. med rettelser (Edit and approve)."""

    edits: ClaimEdit | None = None


class ProcessResult(BaseModel):
    document_id: uuid.UUID
    status: ProcessingStatus
    claims_created: int
    claims_skipped: int
    skipped_reasons: list[str]


class DocumentReviewOut(BaseModel):
    """Dokumentdetalje til review-fladen: metadata, tekst og claims."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    canonical_url: str | None
    title: str | None
    language_code: str | None
    published_at: datetime | None
    retrieved_at: datetime
    content_hash: str
    mime_type: str | None
    processing_status: ProcessingStatus
    is_demo: bool
    error_code: str | None
    normalized_text: str | None
    raw_storage_path: str | None
    raw_url: str | None = None
    claims: list[ClaimOut] = Field(default_factory=list)
