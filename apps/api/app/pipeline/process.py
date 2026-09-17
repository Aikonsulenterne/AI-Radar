"""Pipeline-trin 3–5: relevans, claim extraction og entity resolution.

Kører synkront pr. dokument. AI udfylder aldrig manglende information;
uddrag der ikke findes ordret i dokumentet, kasseres. Ved schemafejl efter
retry går dokumentet til manuel opfølgning (processing_status=failed).
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.ai.prompts import (
    EXTRACTION_PROMPT_ID,
    EXTRACTION_PROMPT_VERSION,
    EXTRACTION_SYSTEM,
    RELEVANCE_PROMPT_ID,
    RELEVANCE_PROMPT_VERSION,
    RELEVANCE_SYSTEM,
)
from app.ai.provider import AIProvider
from app.ai.schemas import (
    AISchemaError,
    ExtractedClaim,
    ExtractionResult,
    RelevanceResult,
    call_with_schema,
)
from app.enums import (
    ADOPTION_STAGES,
    PREDICATES_BY_CLAIM_TYPE,
    ClaimCreatedBy,
    ClaimType,
    EntityType,
    Predicate,
    ProcessingStatus,
)
from app.models import Document, Source
from app.models_claims import Claim, ClaimEvidence
from app.pipeline.entities import resolve_company, resolve_object_entity

# Dokumenter afkortes til denne længde i prompten; fulde tekster ligger i DB.
_MAX_PROMPT_CHARS = 60_000


@dataclass
class ProcessOutcome:
    document_id: str
    status: ProcessingStatus
    claims_created: int = 0
    claims_skipped: int = 0
    skipped_reasons: list[str] = field(default_factory=list)


def _validate_claim(text: str, claim: ExtractedClaim) -> str | None:
    """Returnér årsag til at kassere claimet, ellers None."""
    if claim.predicate not in PREDICATES_BY_CLAIM_TYPE[claim.claim_type]:
        return f"predicate {claim.predicate} passer ikke til claim_type {claim.claim_type}"
    if claim.claim_type == ClaimType.stage:
        if claim.object_text not in ADOPTION_STAGES:
            return "ugyldigt adoption stage"
    if claim.supporting_excerpt not in text:
        return "evidensuddrag findes ikke ordret i dokumentet"
    return None


def _object_fields(
    db: Session, claim: ExtractedClaim
) -> tuple[EntityType | None, uuid.UUID | None, str | None]:
    if claim.object_name:
        resolved = resolve_object_entity(db, claim.object_name)
        if resolved is not None:
            return resolved[0], resolved[1], claim.object_text
        # Intet deterministisk match: objektet forbliver tekst.
        return None, None, claim.object_text or claim.object_name
    return None, None, claim.object_text


def process_document(db: Session, provider: AIProvider, document: Document) -> ProcessOutcome:
    text = document.normalized_text
    if not text:
        return ProcessOutcome(
            document_id=str(document.id),
            status=document.processing_status,
            skipped_reasons=["dokumentet har ingen normaliseret tekst"],
        )

    prompt_text = text[:_MAX_PROMPT_CHARS]
    source = db.get(Source, document.source_id)

    try:
        relevance = call_with_schema(
            provider,
            prompt_id=RELEVANCE_PROMPT_ID,
            prompt_version=RELEVANCE_PROMPT_VERSION,
            system=RELEVANCE_SYSTEM,
            user=prompt_text,
            result_model=RelevanceResult,
            document_id=document.id,
        )
        if not relevance.relevant:
            document.processing_status = ProcessingStatus.classified_irrelevant
            db.flush()
            return ProcessOutcome(
                document_id=str(document.id),
                status=ProcessingStatus.classified_irrelevant,
            )

        extraction = call_with_schema(
            provider,
            prompt_id=EXTRACTION_PROMPT_ID,
            prompt_version=EXTRACTION_PROMPT_VERSION,
            system=EXTRACTION_SYSTEM,
            user=prompt_text,
            result_model=ExtractionResult,
            document_id=document.id,
        )
    except AISchemaError:
        document.processing_status = ProcessingStatus.failed
        document.error_code = "ai_schema_error"
        document.error_message_safe = (
            "AI-output kunne ikke valideres mod schema; kræver manuel opfølgning."
        )
        db.flush()
        return ProcessOutcome(
            document_id=str(document.id),
            status=ProcessingStatus.failed,
            skipped_reasons=["ai_schema_error"],
        )

    created = 0
    skipped: list[str] = []
    seen: set[tuple[ClaimType, Predicate, str, str | None, str | None]] = set()

    for extracted in extraction.claims:
        reason = _validate_claim(text, extracted)
        if reason is not None:
            skipped.append(reason)
            continue

        dedupe_key = (
            extracted.claim_type,
            extracted.predicate,
            extracted.subject_name.casefold(),
            (extracted.object_name or "").casefold() or None,
            (extracted.object_text or "").casefold() or None,
        )
        if dedupe_key in seen:
            skipped.append("dublet inden for dokumentet")
            continue
        seen.add(dedupe_key)

        company = resolve_company(db, extracted.subject_name)
        object_type, object_id, object_text = _object_fields(db, extracted)

        claim = Claim(
            claim_type=extracted.claim_type,
            subject_entity_type=EntityType.company,
            subject_entity_id=company.id,
            predicate=extracted.predicate,
            object_entity_type=object_type,
            object_entity_id=object_id,
            object_text=object_text,
            observed_at=document.published_at or document.retrieved_at,
            created_by=ClaimCreatedBy.ai,
        )
        db.add(claim)
        db.flush()

        start = text.find(extracted.supporting_excerpt)
        db.add(
            ClaimEvidence(
                claim_id=claim.id,
                document_id=document.id,
                supporting_excerpt=extracted.supporting_excerpt,
                excerpt_start=start,
                excerpt_end=start + len(extracted.supporting_excerpt),
                source_type_snapshot=source.source_type if source else None,
                independent_origin_key=document.canonical_url,
            )
        )
        created += 1

    document.processing_status = (
        ProcessingStatus.review_pending if created > 0 else ProcessingStatus.classified_relevant
    )
    db.flush()
    return ProcessOutcome(
        document_id=str(document.id),
        status=document.processing_status,
        claims_created=created,
        claims_skipped=len(skipped),
        skipped_reasons=skipped,
    )
