"""Indsigter på tværs af radarens fund (pipeline/insights.py).

GET viser seneste generering med evidensen slået op på læsetidspunktet, så
et claim, der siden er afvist, ikke længere bærer en indsigt. POST
genererer på ny (Admin); kørslerne gør det også automatisk.
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.provider import (
    AIDocumentRejected,
    AIProvider,
    AIProviderError,
    AIProviderRejected,
    AIRefusal,
)
from app.ai.schemas import AISchemaError
from app.audit import AuditAction, AuditEntity, record
from app.auth import CurrentUser, require_role
from app.db import get_db
from app.enums import UserRole
from app.errors import ApiError
from app.models_claims import Claim
from app.models_settings import AppSetting
from app.pipeline.entities import entity_name, preload_entities
from app.pipeline.insights import SETTING_KEY, VENDOR_SOURCE_TYPES, generate_insights, strength
from app.routes.catalog import _APPROVED, _offering_out, prefetch_offering_sources
from app.routes.documents import ai_provider_dep

router = APIRouter(prefix="/insights", tags=["insights"])

_AUDIT_ID = uuid.uuid5(uuid.NAMESPACE_URL, "ai-radar:setting:insights")


class InsightEvidenceOut(BaseModel):
    claim_id: uuid.UUID
    document_id: uuid.UUID | None
    statement: str
    excerpt: str | None
    source_name: str | None
    source_url: str | None
    vendor_source: bool


class InsightOut(BaseModel):
    id: str
    type: str
    title: str
    finding: str
    implication: str
    recommendation: str
    problem: str | None
    strength: str
    vendor_only: bool
    document_count: int
    evidence: list[InsightEvidenceOut]


class InsightsOut(BaseModel):
    generated_at: datetime | None = None
    prompt_version: str | None = None
    evidence_count: int = 0
    discarded: int = 0
    items: list[InsightOut] = Field(default_factory=list)


def _evidence(db: Session, claim_ids: list[str]) -> list[InsightEvidenceOut]:
    out: list[InsightEvidenceOut] = []
    for raw in claim_ids:
        claim = db.get(Claim, uuid.UUID(raw))
        if claim is None or claim.review_status not in _APPROVED:
            continue
        subject = entity_name(db, claim.subject_entity_type, claim.subject_entity_id) or "?"
        obj = entity_name(db, claim.object_entity_type, claim.object_entity_id)
        obj_text = " — ".join(part for part in (obj, claim.object_text) if part)
        offering = _offering_out(db, claim)
        out.append(
            InsightEvidenceOut(
                claim_id=claim.id,
                document_id=offering.document_id,
                statement=f"{subject}: {obj_text}" if obj_text else subject,
                excerpt=offering.excerpt,
                source_name=offering.source_name,
                source_url=offering.source_url,
                vendor_source=(offering.source_type or "") in VENDOR_SOURCE_TYPES,
            )
        )
    return out


def _preload(db: Session, value: dict[str, Any]) -> None:
    """Alle indsigters claims, entities og kilder i få forespørgsler."""
    ids = {uuid.UUID(raw) for item in value.get("items", []) for raw in item.get("claim_ids", [])}
    if not ids:
        return
    claims = db.scalars(select(Claim).where(Claim.id.in_(ids))).all()
    preload_entities(db, claims)
    prefetch_offering_sources(db, claims)


def _to_out(db: Session, value: dict[str, Any]) -> InsightsOut:
    _preload(db, value)
    items: list[InsightOut] = []
    for item in value.get("items", []):
        evidence = _evidence(db, item.get("claim_ids", []))
        documents = {e.document_id for e in evidence if e.document_id is not None}
        if len(documents) < 2:
            continue  # bærende claims er siden afvist: ikke længere en indsigt
        vendor_only = all(e.vendor_source for e in evidence)
        items.append(
            InsightOut(
                id=item["id"],
                type=item["type"],
                title=item["title"],
                finding=item["finding"],
                implication=item.get("implication", ""),
                recommendation=item.get("recommendation", ""),
                problem=item.get("problem"),
                strength=strength(len(documents), vendor_only),
                vendor_only=vendor_only,
                document_count=len(documents),
                evidence=evidence,
            )
        )
    return InsightsOut(
        generated_at=value.get("generated_at"),
        prompt_version=value.get("prompt_version"),
        evidence_count=value.get("evidence_count", 0),
        discarded=value.get("discarded", 0),
        items=items,
    )


@router.get("", response_model=InsightsOut)
def get_insights(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> InsightsOut:
    row = db.get(AppSetting, SETTING_KEY)
    return InsightsOut() if row is None else _to_out(db, row.value)


@router.post("/generate", response_model=InsightsOut)
def post_generate_insights(
    db: Session = Depends(get_db),
    provider: AIProvider = Depends(ai_provider_dep),
    user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> InsightsOut:
    try:
        value = generate_insights(db, provider)
    except AIProviderRejected as exc:
        raise ApiError(502, "ai_provider_rejected", str(exc)) from exc
    except (AISchemaError, AIRefusal, AIDocumentRejected, AIProviderError) as exc:
        raise ApiError(
            502, "ai_insights_failed", "Indsigterne kunne ikke genereres. Prøv igen."
        ) from exc
    record(
        db,
        entity_type=AuditEntity.setting,
        entity_id=_AUDIT_ID,
        action=AuditAction.created,
        actor_user_id=user.user_id,
        changes={"insights": len(value["items"]), "discarded": value["discarded"]},
    )
    db.commit()
    return _to_out(db, value)
