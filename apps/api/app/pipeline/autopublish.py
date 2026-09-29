"""Fuldt automatisk publicering (AUTO_PUBLISH).

Besluttet af produktejeren 2026-09-29: AI godkender sine egne claims og
publicerer uden menneskelig kontrol. Det erstatter human-in-the-loop for
claims, cases og signaler, når AUTO_PUBLISH er slået til; slået fra gælder
masterfilernes review-flow uændret.

Evidensreglerne gælder stadig: kun claims med ordret evidensuddrag når
hertil (kasseres i process.py), og signalets faktaafsnit må kun gengive
claims. Alt, der publiceres her, markeres auto_approved/auto_published, så
UI'et altid viser, at intet menneske har kontrolleret det.
"""

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.prompts import SIGNAL_PROMPT_ID, SIGNAL_PROMPT_VERSION, SIGNAL_SYSTEM
from app.ai.provider import AIProvider, AIProviderError, AIRefusal
from app.ai.schemas import AISchemaError, SignalDraft, call_with_schema
from app.audit import AuditAction, AuditEntity, record
from app.enums import (
    CaseStatus,
    DocumentationLevel,
    EntityType,
    ProcessingStatus,
    ReviewStatus,
    SignalStatus,
    SourceType,
)
from app.models import Document, Source
from app.models_cases import AdoptionCase, AdoptionCaseClaim
from app.models_claims import Claim, ClaimEvidence, Company
from app.models_signals import Signal, SignalClaim
from app.pipeline.entities import entity_name

logger = logging.getLogger("ai_radar.autopublish")

_OPEN = (ReviewStatus.proposed, ReviewStatus.needs_corroboration)
_APPROVED = (ReviewStatus.approved, ReviewStatus.approved_with_edits)

# Én kilde er aldrig "stærk" dokumentation; leverandørens egne ord er tidlige.
_EARLY_SOURCES = {SourceType.vendor_case, SourceType.vendor_claim, SourceType.early_signal}


@dataclass
class AutoPublishOutcome:
    claims_approved: int = 0
    cases_published: int = 0
    signal_published: bool = False
    skipped_reasons: list[str] = field(default_factory=list)


def _document_claims(db: Session, document_id: uuid.UUID) -> list[Claim]:
    claim_ids = db.scalars(
        select(ClaimEvidence.claim_id).where(ClaimEvidence.document_id == document_id).distinct()
    ).all()
    claims = [db.get(Claim, claim_id) for claim_id in claim_ids]
    return [claim for claim in claims if claim is not None]


def _approve(db: Session, claim: Claim) -> None:
    claim.review_status = ReviewStatus.approved
    claim.auto_approved = True
    claim.reviewed_by_user_id = None
    claim.reviewed_at = datetime.now(UTC)
    for evidence in db.scalars(
        select(ClaimEvidence).where(ClaimEvidence.claim_id == claim.id)
    ).all():
        evidence.review_status = ReviewStatus.approved
    record(
        db,
        entity_type=AuditEntity.claim,
        entity_id=claim.id,
        action=AuditAction.approved,
        actor_user_id=None,
        changes={"status": ReviewStatus.approved.value, "automatisk": True},
    )


def _claim_line(db: Session, index: int, claim: Claim) -> str:
    subject = entity_name(db, claim.subject_entity_type, claim.subject_entity_id) or "?"
    obj = (
        (
            entity_name(db, claim.object_entity_type, claim.object_entity_id)
            if claim.object_entity_type is not None and claim.object_entity_id is not None
            else None
        )
        or claim.object_text
        or ""
    )
    excerpt = db.scalar(
        select(ClaimEvidence.supporting_excerpt).where(ClaimEvidence.claim_id == claim.id)
    )
    return f'{index}. {subject} {claim.predicate} {obj}\n   Evidens: "{excerpt}"'


def _publish_cases(
    db: Session, document: Document, claims: list[Claim], outcome: AutoPublishOutcome
) -> None:
    by_company: dict[uuid.UUID, list[Claim]] = defaultdict(list)
    for claim in claims:
        if claim.subject_entity_type == EntityType.company:
            by_company[claim.subject_entity_id].append(claim)

    for company_id, company_claims in by_company.items():
        company = db.get(Company, company_id)
        if company is None:
            continue
        title = f"{company.name}: {document.title or 'dokumenteret AI-anvendelse'}"
        case = AdoptionCase(
            company_id=company_id,
            title=title[:300],
            summary=(
                f"Automatisk publiceret af AI ud fra {len(company_claims)} claims i "
                f"«{document.title or 'dokumentet'}». Fakta ligger i de tilknyttede "
                "claims med ordrette evidensuddrag; intet menneske har kontrolleret dem."
            ),
            status=CaseStatus.published,
            auto_published=True,
        )
        db.add(case)
        db.flush()
        for claim in company_claims:
            db.add(AdoptionCaseClaim(case_id=case.id, claim_id=claim.id))
        record(
            db,
            entity_type=AuditEntity.adoption_case,
            entity_id=case.id,
            action=AuditAction.published,
            actor_user_id=None,
            changes={"claims": len(company_claims), "automatisk": True},
        )
        outcome.cases_published += 1


def _publish_signal(
    db: Session,
    provider: AIProvider,
    document: Document,
    claims: list[Claim],
    outcome: AutoPublishOutcome,
) -> None:
    source = db.get(Source, document.source_id)
    lines = "\n".join(_claim_line(db, i, claim) for i, claim in enumerate(claims, 1))
    user = (
        f"Dokument: {document.title or '(uden titel)'}\n"
        f"Kilde: {source.name if source else 'ukendt'}"
        f" ({source.source_type if source else 'ukendt type'})\n\n"
        f"Claims:\n{lines}"
    )
    try:
        draft = call_with_schema(
            provider,
            prompt_id=SIGNAL_PROMPT_ID,
            prompt_version=SIGNAL_PROMPT_VERSION,
            system=SIGNAL_SYSTEM,
            user=user,
            result_model=SignalDraft,
            document_id=document.id,
        )
    except (AIProviderError, AIRefusal, AISchemaError) as exc:
        # Cases og claims er allerede publiceret; signalet springes over.
        logger.warning("signal_draft_skipped document=%s reason=%s", document.id, type(exc))
        outcome.skipped_reasons.append("signal kunne ikke skrives af AI")
        return

    level = (
        DocumentationLevel.early
        if source is not None and source.source_type in _EARLY_SOURCES
        else DocumentationLevel.limited
    )
    signal = Signal(
        title=draft.title[:300],
        summary=draft.summary,
        analysis=draft.analysis or None,
        recommendation=draft.recommendation or None,
        documentation_level=level,
        status=SignalStatus.published,
        published_at=datetime.now(UTC),
        auto_published=True,
    )
    db.add(signal)
    db.flush()
    for claim in claims:
        db.add(SignalClaim(signal_id=signal.id, claim_id=claim.id))
    record(
        db,
        entity_type=AuditEntity.signal,
        entity_id=signal.id,
        action=AuditAction.published,
        actor_user_id=None,
        changes={"claims": len(claims), "automatisk": True},
    )
    outcome.signal_published = True


def autopublish_document(
    db: Session, provider: AIProvider, document: Document
) -> AutoPublishOutcome:
    """Godkend dokumentets åbne claims og publicér case(s) og signal.

    Idempotent pr. dokument: claims, der allerede er afgjort, røres ikke, og
    et dokument uden åbne claims får ingen nye cases eller signaler.
    """
    outcome = AutoPublishOutcome()
    claims = _document_claims(db, document.id)
    open_claims = [claim for claim in claims if claim.review_status in _OPEN]
    if not open_claims:
        return outcome

    for claim in open_claims:
        _approve(db, claim)
    outcome.claims_approved = len(open_claims)
    db.flush()

    approved = [claim for claim in claims if claim.review_status in _APPROVED]
    _publish_cases(db, document, approved, outcome)
    _publish_signal(db, provider, document, approved, outcome)

    document.processing_status = ProcessingStatus.reviewed
    db.flush()
    record(
        db,
        entity_type=AuditEntity.document,
        entity_id=document.id,
        action=AuditAction.review_completed,
        actor_user_id=None,
        changes={
            "automatisk": True,
            "claims_godkendt": outcome.claims_approved,
            "cases": outcome.cases_published,
            "signal": outcome.signal_published,
        },
    )
    return outcome
