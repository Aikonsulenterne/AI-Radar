"""Genlæsning af dokumenter, der blev behandlet før leverandørprompten.

Extraction 1.3.0 udtrækker leverandørtilbud, marked og sprog, som ældre
udtræk sprang over. Dokumenterne er allerede hentet (og springes over af
RSS-dedupe), så uden genlæsning ville leverandørlandskabet kun fyldes af nye
artikler. Genlæsningen tilføjer kun leverandørclaims, springer claims over,
som dokumentet allerede har, og laver hverken signaler eller cases — de
findes i forvejen for dokumentet.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.prompts import (
    EXTRACTION_PROMPT_ID,
    EXTRACTION_PROMPT_VERSION,
    EXTRACTION_SYSTEM,
    extraction_user_message,
)
from app.ai.provider import AIDocumentRejected, AIProvider, AIProviderRejected, AIRefusal
from app.ai.schemas import AISchemaError, ExtractedClaim, ExtractionResult, call_with_schema
from app.config import get_settings
from app.enums import VENDOR_PREDICATES, Predicate, ProcessingStatus
from app.errors import ApiError
from app.models import Document, Source
from app.models_claims import Claim, ClaimEvidence
from app.pipeline.entities import entity_name, legal_base_name, normalize_alias
from app.pipeline.process import _MAX_PROMPT_CHARS, capabilities, create_claim, validate_claim

logger = logging.getLogger("ai_radar.backfill")

# Leverandørclaims samt kundens brug af en leverandør (kobler kunder på).
_KEEP = VENDOR_PREDICATES | {Predicate.USES_VENDOR}

# Dokumenter, der blev vurderet relevante og fik (eller kunne få) claims.
_REREAD_STATUSES = (
    ProcessingStatus.classified_relevant,
    ProcessingStatus.review_pending,
    ProcessingStatus.partially_reviewed,
    ProcessingStatus.reviewed,
)


def documents_to_reread(db: Session, limit: int) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .where(
                Document.vendor_extracted_at.is_(None),
                Document.processing_status.in_(_REREAD_STATUSES),
                Document.normalized_text.is_not(None),
                Document.is_demo.is_(False),
            )
            .order_by(Document.retrieved_at.desc())
            .limit(limit)
        ).all()
    )


def _key(predicate: Predicate, subject: str, obj: str | None) -> tuple[str, str, str]:
    return (predicate.value, legal_base_name(subject), normalize_alias(obj or ""))


def _existing_keys(db: Session, document: Document) -> set[tuple[str, str, str]]:
    claim_ids = db.scalars(
        select(ClaimEvidence.claim_id).where(ClaimEvidence.document_id == document.id)
    ).all()
    keys: set[tuple[str, str, str]] = set()
    for claim_id in claim_ids:
        claim = db.get(Claim, claim_id)
        if claim is None or claim.predicate not in _KEEP:
            continue
        subject = entity_name(db, claim.subject_entity_type, claim.subject_entity_id) or ""
        obj = entity_name(db, claim.object_entity_type, claim.object_entity_id)
        keys.add(_key(claim.predicate, subject, obj or claim.object_text))
    return keys


def _extracted_key(extracted: ExtractedClaim) -> tuple[str, str, str]:
    return _key(
        extracted.predicate,
        extracted.subject_name,
        extracted.object_name or extracted.object_text,
    )


def reread_document(db: Session, provider: AIProvider, document: Document) -> int:
    """Udtræk leverandørclaims fra et allerede behandlet dokument.

    Returnerer antal nye claims. Kaster ApiError(ai_provider_rejected), når
    nøgle/model/kvote er forkert, så kørslen kan stoppe; andre AI-fejl
    markerer dokumentet som genlæst og går videre.
    """
    text = document.normalized_text or ""
    source = db.get(Source, document.source_id)
    try:
        extraction = call_with_schema(
            provider,
            prompt_id=EXTRACTION_PROMPT_ID,
            prompt_version=EXTRACTION_PROMPT_VERSION,
            system=EXTRACTION_SYSTEM,
            user=extraction_user_message(
                capabilities(db), text[:_MAX_PROMPT_CHARS], vendor_only=True
            ),
            result_model=ExtractionResult,
            document_id=document.id,
        )
    except AIProviderRejected as exc:
        raise ApiError(502, "ai_provider_rejected", str(exc)) from exc
    except (AIDocumentRejected, AIRefusal, AISchemaError):
        logger.warning("reread_skipped document=%s", document.id)
        document.vendor_extracted_at = datetime.now(UTC)
        return 0

    seen = _existing_keys(db, document)
    created: list[Claim] = []
    for extracted in extraction.claims:
        if extracted.predicate not in _KEEP or validate_claim(text, extracted) is not None:
            continue
        key = _extracted_key(extracted)
        if key in seen:
            continue
        seen.add(key)
        created.append(create_claim(db, document, source, text, extracted))

    if created and get_settings().auto_publish:
        # Godkend uden ny case eller nyt signal: dokumentet har dem allerede.
        from app.pipeline.autopublish import approve_automatically

        for claim in created:
            approve_automatically(db, claim)
    document.vendor_extracted_at = datetime.now(UTC)
    db.flush()
    return len(created)
