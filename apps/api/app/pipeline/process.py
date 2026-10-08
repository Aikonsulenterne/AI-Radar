"""Pipeline-trin 3–5: relevans, claim extraction og entity resolution.

Kører synkront pr. dokument. AI udfylder aldrig manglende information;
uddrag der ikke findes ordret i dokumentet, kasseres. Ved schemafejl efter
retry går dokumentet til manuel opfølgning (processing_status=failed).
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.prompts import (
    EXTRACTION_PROMPT_ID,
    EXTRACTION_PROMPT_VERSION,
    EXTRACTION_SYSTEM,
    RELEVANCE_PROMPT_ID,
    RELEVANCE_PROMPT_VERSION,
    RELEVANCE_SYSTEM,
    extraction_user_message,
)
from app.ai.provider import AIDocumentRejected, AIProvider, AIProviderRejected, AIRefusal
from app.ai.schemas import (
    AISchemaError,
    ExtractedClaim,
    ExtractionResult,
    RelevanceResult,
    call_with_schema,
)
from app.config import get_settings
from app.enums import (
    ADOPTION_STAGES,
    PREDICATES_BY_CLAIM_TYPE,
    ClaimCreatedBy,
    ClaimType,
    EntityType,
    Predicate,
    ProcessingStatus,
)
from app.errors import ApiError
from app.models import Document, Source
from app.models_claims import Claim, ClaimEvidence, Technology
from app.pipeline.entities import (
    resolve_candidate_technology,
    resolve_company,
    resolve_object_entity,
)

# Dokumenter afkortes til denne længde i prompten; fulde tekster ligger i DB.
_MAX_PROMPT_CHARS = 60_000

# Statusser et dokument kan (gen)behandles fra.
PROCESSABLE_STATUSES = frozenset(
    {ProcessingStatus.normalized, ProcessingStatus.classified_relevant, ProcessingStatus.failed}
)
# En kørsel, der dør midtvejs (fx genstart af serveren), efterlader
# extraction_pending. Efter dette tidsrum må dokumentet køres igen.
STALE_PROCESSING_AFTER = timedelta(minutes=15)


def _processing_is_stale(document: Document) -> bool:
    updated = document.updated_at
    if updated.tzinfo is None:  # SQLite gemmer uden tidszone
        updated = updated.replace(tzinfo=UTC)
    return datetime.now(UTC) - updated > STALE_PROCESSING_AFTER


def begin_processing(db: Session, document_id: uuid.UUID) -> tuple[Document, ProcessingStatus]:
    """Markér dokumentet som under behandling og commit, før AI kaldes.

    Rækkelåsen (FOR UPDATE) serialiserer samtidige kald: det andet venter,
    ser extraction_pending og afvises med 409. Så behandles samme dokument
    aldrig to gange (dobbelte claims og dobbelt AI-forbrug). Returnerer den
    status, der skal genskabes, hvis kørslen afbrydes.
    """
    document = db.get(Document, document_id, with_for_update=True)
    if document is None:
        raise ApiError(404, "not_found", "Dokumentet findes ikke.")
    status = document.processing_status
    if status == ProcessingStatus.extraction_pending:
        if not _processing_is_stale(document):
            raise ApiError(
                409,
                "already_processing",
                "Dokumentet er allerede under AI-behandling. Vent, til kørslen er færdig.",
            )
        status = ProcessingStatus.normalized
    elif status not in PROCESSABLE_STATUSES:
        raise ApiError(
            409,
            "invalid_status",
            f"Dokumentet kan ikke behandles i status '{status}'.",
        )
    if not document.normalized_text:
        raise ApiError(
            409,
            "no_text",
            "Dokumentet har ingen normaliseret tekst, så der kan ikke udtrækkes claims.",
        )
    document.processing_status = ProcessingStatus.extraction_pending
    db.commit()
    return document, status


def abort_processing(db: Session, document: Document, previous: ProcessingStatus) -> None:
    """Rul en afbrudt kørsel tilbage, så dokumentet kan køres igen."""
    db.rollback()
    document.processing_status = previous
    db.commit()


@dataclass
class ProcessOutcome:
    document_id: str
    status: ProcessingStatus
    claims_created: int = 0
    claims_skipped: int = 0
    skipped_reasons: list[str] = field(default_factory=list)


def create_claim(
    db: Session,
    document: Document,
    source: Source | None,
    text: str,
    extracted: ExtractedClaim,
) -> Claim:
    """Gem et valideret claim med dets ordrette evidensuddrag."""
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
    return claim


def capabilities(db: Session) -> list[tuple[str, str]]:
    technologies = db.scalars(
        select(Technology).where(Technology.active.is_(True)).order_by(Technology.name)
    ).all()
    return [(technology.name, technology.definition) for technology in technologies]


def validate_claim(text: str, claim: ExtractedClaim) -> str | None:
    """Returnér årsag til at kassere claimet, ellers None."""
    if claim.predicate not in PREDICATES_BY_CLAIM_TYPE[claim.claim_type]:
        return f"predicate {claim.predicate} passer ikke til claim_type {claim.claim_type}"
    if claim.claim_type == ClaimType.stage:
        if claim.object_text not in ADOPTION_STAGES:
            return "ugyldigt adoption stage"
    if claim.supporting_excerpt not in text:
        return "evidensuddrag findes ikke ordret i dokumentet"
    return None


# Predicates hvis objekt er en capability. En capability uden for radarens
# liste er netop det nye i markedet, radaren skal fange.
_CAPABILITY_PREDICATES = frozenset({Predicate.OFFERS_CAPABILITY, Predicate.USES_CAPABILITY})


def _object_fields(
    db: Session, claim: ExtractedClaim
) -> tuple[EntityType | None, uuid.UUID | None, str | None]:
    if claim.object_name:
        resolved = resolve_object_entity(db, claim.object_name)
        if resolved is not None:
            return resolved[0], resolved[1], claim.object_text
        if claim.predicate in _CAPABILITY_PREDICATES:
            candidate = resolve_candidate_technology(db, claim.object_name)
            if candidate is not None:
                return EntityType.technology, candidate.id, claim.object_text
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
            user=extraction_user_message(capabilities(db), prompt_text),
            result_model=ExtractionResult,
            document_id=document.id,
        )
    except AIProviderRejected as exc:
        # Konfigurationsfejl (nøgle, model, kvote): dokumentet har intet gjort
        # galt, så dets status røres ikke, og det kan køres igen efter rettelse.
        raise ApiError(502, "ai_provider_rejected", str(exc)) from exc
    except AIDocumentRejected:
        document.processing_status = ProcessingStatus.failed
        document.error_code = "ai_request_rejected"
        document.error_message_safe = (
            "AI-udbyderen afviste forespørgslen for dokumentet; kræver manuel opfølgning."
        )
        db.flush()
        return ProcessOutcome(
            document_id=str(document.id),
            status=ProcessingStatus.failed,
            skipped_reasons=["ai_request_rejected"],
        )
    except AIRefusal:
        document.processing_status = ProcessingStatus.failed
        document.error_code = "ai_refused"
        document.error_message_safe = (
            "Modellen afviste at behandle dokumentet; kræver manuel opfølgning."
        )
        db.flush()
        return ProcessOutcome(
            document_id=str(document.id),
            status=ProcessingStatus.failed,
            skipped_reasons=["ai_refused"],
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
        reason = validate_claim(text, extracted)
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

        create_claim(db, document, source, text, extracted)
        created += 1

    document.vendor_extracted_at = datetime.now(UTC)
    document.processing_status = (
        ProcessingStatus.review_pending if created > 0 else ProcessingStatus.classified_relevant
    )
    db.flush()
    if created > 0 and get_settings().auto_publish:
        # Fuldt automatisk: AI godkender og publicerer (pipeline/autopublish.py).
        from app.pipeline.autopublish import autopublish_document

        autopublish_document(db, provider, document)
    return ProcessOutcome(
        document_id=str(document.id),
        status=document.processing_status,
        claims_created=created,
        claims_skipped=len(skipped),
        skipped_reasons=skipped,
    )
