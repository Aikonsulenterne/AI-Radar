"""Indsigter: mønstre på tværs af radarens godkendte claims.

Et signal bygger på ét dokument; en indsigt kræver claims fra mindst to
forskellige dokumenter. Modellen foreslår indsigter ud fra en nummereret
evidensliste; serveren kasserer alt, der citerer ukendte claims eller færre
end to dokumenter, og beregner selv evidensstyrken ud fra kilderne — det
vurderer modellen ikke. Interne kilder (access class restricted) indgår
aldrig: Indsigter er markedsviden.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.prompts import INSIGHT_PROMPT_ID, INSIGHT_PROMPT_VERSION, INSIGHT_SYSTEM
from app.ai.provider import AIProvider
from app.ai.schemas import InsightResult, call_with_schema
from app.enums import AccessClass, ReviewStatus
from app.models import Document, Source
from app.models_claims import Claim, ClaimEvidence
from app.models_opportunities import ProblemTaxonomy
from app.models_settings import AppSetting
from app.pipeline.entities import entity_name

logger = logging.getLogger("ai_radar.insights")

SETTING_KEY = "insights"
# Seneste godkendte claims, der sendes med. Afgrænser prompt og pris.
MAX_EVIDENCE = 250
_EXCERPT_CHARS = 220
_APPROVED = (ReviewStatus.approved, ReviewStatus.approved_with_edits)
VENDOR_SOURCE_TYPES = {"vendor_case", "vendor_claim"}


@dataclass
class EvidenceItem:
    number: int
    claim_id: uuid.UUID
    document_id: uuid.UUID
    source_type: str | None
    line: str


def collect_evidence(db: Session, limit: int = MAX_EVIDENCE) -> list[EvidenceItem]:
    """Godkendte claims fra ikke-interne kilder, nyeste først, nummereret."""
    rows = db.execute(
        select(Claim, ClaimEvidence, Document, Source)
        .join(ClaimEvidence, ClaimEvidence.claim_id == Claim.id)
        .join(Document, Document.id == ClaimEvidence.document_id)
        .join(Source, Source.id == Document.source_id)
        .where(
            Claim.review_status.in_(_APPROVED),
            Source.access_class != AccessClass.restricted,
            Document.is_demo.is_(False),
        )
        .order_by(Claim.observed_at.desc().nulls_last(), Claim.id)
    ).all()

    items: list[EvidenceItem] = []
    seen: set[uuid.UUID] = set()
    doc_numbers: dict[uuid.UUID, int] = {}
    for claim, evidence, document, source in rows:
        if claim.id in seen:
            continue
        seen.add(claim.id)
        number = len(items) + 1
        doc_number = doc_numbers.setdefault(document.id, len(doc_numbers) + 1)
        subject = entity_name(db, claim.subject_entity_type, claim.subject_entity_id) or "?"
        obj = entity_name(db, claim.object_entity_type, claim.object_entity_id)
        obj_text = " — ".join(part for part in (obj, claim.object_text) if part) or "-"
        excerpt = " ".join(evidence.supporting_excerpt.split())[:_EXCERPT_CHARS]
        observed = claim.observed_at.date().isoformat() if claim.observed_at else "ukendt dato"
        items.append(
            EvidenceItem(
                number=number,
                claim_id=claim.id,
                document_id=document.id,
                source_type=str(source.source_type) if source.source_type else None,
                line=(
                    f"[{number}] {subject} | {claim.predicate} | {obj_text} | "
                    f'"{excerpt}" | {source.name} ({source.source_type}) | {observed} | '
                    f"doc {doc_number}"
                ),
            )
        )
        if len(items) >= limit:
            break
    return items


def _user_message(problems: list[ProblemTaxonomy], evidence: list[EvidenceItem]) -> str:
    problem_lines = "\n".join(f"- {p.name}: {p.description}" for p in problems) or "- (ingen)"
    evidence_lines = "\n".join(item.line for item in evidence)
    return f"OK'S PROBLEMS:\n{problem_lines}\n\nEVIDENCE:\n{evidence_lines}"


def strength(document_count: int, vendor_only: bool) -> str:
    """Evidensstyrke beregnet af serveren — ikke af modellen."""
    if document_count >= 3 and not vendor_only:
        return "stærk"
    if document_count >= 2:
        return "moderat"
    return "svag"


def generate_insights(db: Session, provider: AIProvider) -> dict[str, Any]:
    """Generér og gem indsigter. Returnerer den gemte værdi."""
    evidence = collect_evidence(db)
    problems = list(
        db.scalars(select(ProblemTaxonomy).where(ProblemTaxonomy.active.is_(True))).all()
    )
    problem_names = {p.name for p in problems}
    by_number = {item.number: item for item in evidence}

    items: list[dict[str, Any]] = []
    discarded = 0
    if len(evidence) >= 2:
        result = call_with_schema(
            provider,
            prompt_id=INSIGHT_PROMPT_ID,
            prompt_version=INSIGHT_PROMPT_VERSION,
            system=INSIGHT_SYSTEM,
            user=_user_message(problems, evidence),
            result_model=InsightResult,
        )
        for draft in result.insights:
            cited = [by_number[n] for n in dict.fromkeys(draft.claims) if n in by_number]
            documents = {item.document_id for item in cited}
            # Ukendte numre eller kun ét dokument: ikke en indsigt.
            if len(cited) != len(set(draft.claims)) or len(documents) < 2:
                discarded += 1
                continue
            vendor_only = all(item.source_type in VENDOR_SOURCE_TYPES for item in cited)
            items.append(
                {
                    "id": str(uuid.uuid4()),
                    "type": draft.type,
                    "title": draft.title,
                    "finding": draft.finding,
                    "implication": draft.implication,
                    "recommendation": draft.recommendation,
                    "problem": draft.problem if draft.problem in problem_names else None,
                    "claim_ids": [str(item.claim_id) for item in cited],
                    "document_count": len(documents),
                    "vendor_only": vendor_only,
                    "strength": strength(len(documents), vendor_only),
                }
            )

    value: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "prompt_version": INSIGHT_PROMPT_VERSION,
        "evidence_count": len(evidence),
        "discarded": discarded,
        "items": items,
    }
    row = db.get(AppSetting, SETTING_KEY)
    if row is None:
        db.add(AppSetting(key=SETTING_KEY, value=value))
    else:
        row.value = value
        row.updated_at = datetime.now(UTC)
    db.flush()
    logger.info(
        "insights_generated evidence=%d insights=%d discarded=%d",
        len(evidence),
        len(items),
        discarded,
    )
    return value
