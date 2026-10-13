"""Markedsudtræk og Til OK — den forenklede radar (2026-10-13).

Pr. dokument: relevans (billig model) → ét udtræk af teknologier og cases.
Hvert fund kræver et ordret citat fra dokumentet; tal i effekt og omfang
skal stå i dokumentet. AI-indhold publiceres automatisk og mærkes som
AI-sammenfattet; konsulenten kan skjule et forkert fund.

Til OK: en separat prompt får OK's problemliste og de synlige fund og
skriver forsiden. Serveren kasserer henvisninger til fund, der ikke findes.
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.prompts import (
    MARKET_PROMPT_ID,
    MARKET_PROMPT_VERSION,
    MARKET_SYSTEM,
    OK_BRIEF_PROMPT_ID,
    OK_BRIEF_PROMPT_VERSION,
    OK_BRIEF_SYSTEM,
    RELEVANCE_PROMPT_ID,
    RELEVANCE_PROMPT_VERSION,
    RELEVANCE_SYSTEM,
    market_user_message,
)
from app.ai.provider import AIDocumentRejected, AIProvider, AIRefusal
from app.ai.schemas import (
    AISchemaError,
    MarketCaseDraft,
    MarketExtractionResult,
    MarketTechnologyDraft,
    OkBriefResult,
    RelevanceResult,
    call_with_schema,
)
from app.enums import AccessClass, EntityType, ProcessingStatus
from app.market.catalog import AREA_LABELS, AREAS, OK_PROBLEMS, TECH_CATALOG
from app.market.views import (
    CaseCard,
    TechnologyCard,
    case_cards,
    technology_cards,
    visible_rows,
)
from app.models import Document, Source
from app.models_claims import Technology
from app.models_market import KIND_CASE, KIND_TECHNOLOGY, MarketItem
from app.models_settings import AppSetting
from app.pipeline.entities import (
    _add_alias,
    _alias_match,
    legal_base_name,
    normalize_alias,
    resolve_candidate_technology,
    resolve_company,
    slugify,
)

logger = logging.getLogger("ai_radar.market")

_MAX_PROMPT_CHARS = 60_000
OK_BRIEF_KEY = "ok_brief"

_AREA_ALIASES = {
    "salg": "salg",
    "sales": "salg",
    "kundeservice": "kundeservice",
    "customer service": "kundeservice",
    "kundecenter": "kundeservice",
    "contact center": "kundeservice",
    "support": "support",
    "kundesupport": "support",
}
_STAGES = {
    "idé": "idé",
    "ide": "idé",
    "idea": "idé",
    "pilot": "pilot",
    "drift": "drift",
    "i drift": "drift",
    "production": "drift",
    "skaleret": "skaleret",
    "scale": "skaleret",
    "scaled": "skaleret",
}
_KPIS = {
    "kontaktomkostning",
    "ventetid",
    "løst_ved_første_kontakt",
    "kundetilfredshed",
    "konvertering",
    "mersalg",
    "churn",
    "produktivitet",
    "andet",
}
_EFFECT_SOURCES = {"virksomheden", "leverandøren", "uafhængig"}
_COUNTRY_NAMES = {
    "denmark": "DK",
    "danmark": "DK",
    "sweden": "SE",
    "sverige": "SE",
    "norway": "NO",
    "norge": "NO",
    "finland": "FI",
    "iceland": "IS",
    "island": "IS",
    "germany": "DE",
    "tyskland": "DE",
    "united kingdom": "GB",
    "uk": "GB",
    "storbritannien": "GB",
    "united states": "US",
    "usa": "US",
    "netherlands": "NL",
    "holland": "NL",
}


def _squash(text: str) -> str:
    return " ".join(text.split())


def quote_in_text(quote: str, text: str) -> bool:
    return bool(quote.strip()) and _squash(quote) in _squash(text)


_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def numbers_in_text(value: str | None, text: str) -> bool:
    """Alle tal i en effekt eller et omfang skal stå i dokumentet — AI må
    ikke opfinde eller omregne tal. Decimaltegn kan skifte ved oversættelse."""
    if not value:
        return True
    haystack = _squash(text).replace(",", ".")
    return all(n.replace(",", ".") in haystack for n in _NUMBER.findall(value))


def _areas(values: list[str], fallback: tuple[str, ...]) -> list[str]:
    areas: list[str] = []
    for value in values:
        area = _AREA_ALIASES.get(normalize_alias(value))
        if area and area not in areas:
            areas.append(area)
    return areas or list(fallback)


def _country(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if len(cleaned) == 2 and cleaned.isalpha():
        return cleaned.upper()
    return _COUNTRY_NAMES.get(normalize_alias(cleaned))


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _squash(value)
    return cleaned or None


# --- Katalog ---


def ensure_catalog(db: Session) -> dict[str, Technology]:
    """Sørg for, at katalogets teknologier findes, og returnér et opslag fra
    navn, dansk betegnelse og aliaser til teknologien."""
    by_name = {normalize_alias(t.name): t for t in db.scalars(select(Technology)).all()}
    index: dict[str, Technology] = {}
    for entry in TECH_CATALOG:
        technology = by_name.get(normalize_alias(entry.name))
        if technology is None:
            base = slugify(entry.name)
            slug = base
            counter = 2
            while db.scalar(select(Technology).where(Technology.slug == slug)) is not None:
                slug = f"{base}-{counter}"
                counter += 1
            technology = Technology(
                name=entry.name, slug=slug, definition=entry.what, active=True, is_candidate=False
            )
            db.add(technology)
            db.flush()
        elif technology.is_candidate or not technology.active:
            technology.is_candidate = False
            technology.active = True
        for alias in (entry.name, entry.label, *entry.aliases):
            index[normalize_alias(alias)] = technology
            if _alias_match(db, EntityType.technology, alias) is None:
                _add_alias(db, EntityType.technology, technology.id, alias)
                db.flush()
    return index


def _resolve_technology(
    db: Session, name: str | None, index: dict[str, Technology]
) -> Technology | None:
    if not name:
        return None
    hit = index.get(normalize_alias(name))
    if hit is not None:
        return hit
    alias = _alias_match(db, EntityType.technology, name)
    if alias is not None:
        return db.get(Technology, alias)
    return resolve_candidate_technology(db, name)


# --- Udtræk pr. dokument ---


@dataclass
class MarketOutcome:
    relevant: bool = False
    technologies: int = 0
    cases: int = 0
    skipped: list[str] = field(default_factory=list)


def _finish(document: Document, status: ProcessingStatus) -> None:
    document.market_extracted_at = datetime.now(UTC)
    # Kun nye dokumenter får status her; ældre beholder deres historik.
    if document.processing_status in (
        ProcessingStatus.normalized,
        ProcessingStatus.extraction_pending,
    ):
        document.processing_status = status


def _fail(document: Document, code: str, message: str) -> MarketOutcome:
    document.error_code = code
    document.error_message_safe = message
    _finish(document, ProcessingStatus.failed)
    return MarketOutcome(skipped=[code])


def process_market_document(db: Session, provider: AIProvider, document: Document) -> MarketOutcome:
    """Relevans + markedsudtræk for ét dokument. AIProviderRejected (nøgle,
    model, kvote) kastes videre, så kørslen kan stoppe."""
    text = document.normalized_text
    source = db.get(Source, document.source_id)
    if not text or document.is_demo or source is None:
        _finish(document, ProcessingStatus.classified_irrelevant)
        return MarketOutcome(skipped=["ingen tekst"])
    if source.access_class == AccessClass.restricted:
        # Interne dokumenter er aldrig markedsviden.
        document.market_extracted_at = datetime.now(UTC)
        return MarketOutcome(skipped=["intern kilde"])

    prompt_text = text[:_MAX_PROMPT_CHARS]
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
        document.market_relevant = relevance.relevant
        if not relevance.relevant:
            _finish(document, ProcessingStatus.classified_irrelevant)
            return MarketOutcome()

        index = ensure_catalog(db)
        result = call_with_schema(
            provider,
            prompt_id=MARKET_PROMPT_ID,
            prompt_version=MARKET_PROMPT_VERSION,
            system=MARKET_SYSTEM,
            user=market_user_message([(e.name, e.what) for e in TECH_CATALOG], prompt_text),
            result_model=MarketExtractionResult,
            document_id=document.id,
        )
    except AIDocumentRejected:
        return _fail(document, "ai_request_rejected", "AI-udbyderen afviste dokumentet.")
    except AIRefusal:
        return _fail(document, "ai_refused", "Modellen afviste at behandle dokumentet.")
    except AISchemaError:
        return _fail(document, "ai_schema_error", "AI-output kunne ikke valideres mod schema.")

    db.execute(
        delete(MarketItem).where(
            MarketItem.document_id == document.id, MarketItem.hidden.is_(False)
        )
    )
    outcome = MarketOutcome(relevant=True)
    observed = document.published_at or document.retrieved_at
    seen: set[tuple[str, Any, Any]] = set()
    for draft in result.technologies:
        reason = _store_technology(db, document, text, draft, index, observed, seen)
        if reason:
            outcome.skipped.append(reason)
        else:
            outcome.technologies += 1
    for case in result.cases:
        reason = _store_case(db, document, text, case, index, observed, seen)
        if reason:
            outcome.skipped.append(reason)
        else:
            outcome.cases += 1
    _finish(document, ProcessingStatus.classified_relevant)
    db.flush()
    return outcome


def _store_technology(
    db: Session,
    document: Document,
    text: str,
    draft: MarketTechnologyDraft,
    index: dict[str, Technology],
    observed: datetime,
    seen: set[tuple[str, Any, Any]],
) -> str | None:
    if not quote_in_text(draft.quote, text):
        return "citat findes ikke ordret i dokumentet"
    technology = _resolve_technology(db, draft.technology, index)
    vendor = resolve_company(db, draft.vendor)
    key = (
        "technology",
        vendor.id,
        technology.id if technology else normalize_alias(draft.technology),
    )
    if key in seen:
        return "dublet i dokumentet"
    seen.add(key)
    catalog_areas = next(
        (e.areas for e in TECH_CATALOG if technology is not None and e.name == technology.name),
        ("kundeservice",),
    )
    db.add(
        MarketItem(
            kind=KIND_TECHNOLOGY,
            document_id=document.id,
            technology_id=technology.id if technology else None,
            vendor_company_id=vendor.id,
            areas=_areas(draft.area, catalog_areas),
            data={
                "technology_name": _clean(draft.technology),
                "product": _clean(draft.product),
                "what_it_does_da": _clean(draft.what_it_does_da),
                "business_value_da": _clean(draft.business_value_da),
                "danish_supported": draft.danish_supported,
            },
            quote=_squash(draft.quote),
            prompt_version=MARKET_PROMPT_VERSION,
            observed_at=observed,
        )
    )
    return None


def _store_case(
    db: Session,
    document: Document,
    text: str,
    draft: MarketCaseDraft,
    index: dict[str, Technology],
    observed: datetime,
    seen: set[tuple[str, Any, Any]],
) -> str | None:
    if not quote_in_text(draft.quote, text):
        return "citat findes ikke ordret i dokumentet"
    if draft.vendor and legal_base_name(draft.vendor) == legal_base_name(draft.company):
        return "leverandøren er ikke sin egen case"
    effect = _clean(draft.effect)
    scope = _clean(draft.scope)
    if not numbers_in_text(effect, text):
        effect = None  # tal, der ikke står i kilden, vises aldrig
    if not numbers_in_text(scope, text):
        scope = None
    technology = _resolve_technology(db, draft.technology, index)
    company = resolve_company(db, draft.company)
    vendor = resolve_company(db, draft.vendor) if draft.vendor else None
    key = (
        "case",
        company.id,
        technology.id if technology else normalize_alias(draft.technology or ""),
    )
    if key in seen:
        return "dublet i dokumentet"
    seen.add(key)
    kpi = draft.kpi if draft.kpi in _KPIS else ("andet" if effect else None)
    effect_source = draft.effect_source if draft.effect_source in _EFFECT_SOURCES else None
    db.add(
        MarketItem(
            kind=KIND_CASE,
            document_id=document.id,
            technology_id=technology.id if technology else None,
            company_id=company.id,
            vendor_company_id=vendor.id if vendor else None,
            areas=_areas(draft.area, ("kundeservice",)),
            data={
                "country": _country(draft.country),
                "industry": _clean(draft.industry),
                "what_they_did_da": _clean(draft.what_they_did_da),
                "technology_name": _clean(draft.technology),
                "adoption_stage": _STAGES.get(normalize_alias(draft.adoption_stage or "")),
                "scope": scope,
                "effect": effect,
                "kpi": kpi if effect else None,
                "effect_source": effect_source if effect else None,
                "lesson": _clean(draft.lesson),
            },
            quote=_squash(draft.quote),
            prompt_version=MARKET_PROMPT_VERSION,
            observed_at=observed,
        )
    )
    return None


def documents_for_market(db: Session, limit: int) -> list[Document]:
    """Allerede hentede dokumenter, som markedsudtrækket ikke har set endnu —
    nyeste først, så radaren fyldes med det aktuelle."""
    if limit <= 0:
        return []
    return list(
        db.scalars(
            select(Document)
            .join(Source, Source.id == Document.source_id)
            .where(
                Document.market_extracted_at.is_(None),
                Document.normalized_text.is_not(None),
                Document.is_demo.is_(False),
                Source.access_class != AccessClass.restricted,
                Document.processing_status.not_in(
                    (ProcessingStatus.normalized, ProcessingStatus.extraction_pending)
                ),
            )
            .order_by(Document.published_at.desc().nulls_last(), Document.retrieved_at.desc())
            .limit(limit)
        ).all()
    )


# --- Til OK ---


_MAX_BRIEF_TECHNOLOGIES = 60
_MAX_BRIEF_CASES = 120


def _line(value: str | None, limit: int = 240) -> str:
    return _squash(value or "")[:limit]


def _areas_text(areas: list[str]) -> str:
    return ", ".join(AREA_LABELS.get(a, a) for a in areas)


def _tech_line(i: int, t: TechnologyCard) -> str:
    vendors = ", ".join(v.name for v in t.vendors[:8]) or "ingen fundet"
    return (
        f"- [T{i}] {t.label} | områder: {_areas_text(t.areas)} | leverandører: {vendors} | "
        f"cases: {t.case_count} | {_line(t.what, 160)}"
    )


def _case_line(i: int, c: CaseCard) -> str:
    technology = c.technology.label if c.technology else c.technology_name or "ukendt"
    effect = _line(c.effect, 200) or "ikke oplyst"
    if c.effect:
        effect += f" ({c.kpi_label}; {c.effect_source_label or 'kilde ukendt'})"
    return (
        f"- [C{i}] {c.company} ({c.country or 'land ukendt'}, {c.industry or 'branche ukendt'}) "
        f"| {_areas_text(c.areas)} | {_line(c.what_they_did, 200)} | teknologi: {technology} "
        f"| leverandør: {c.vendor or 'ukendt'} | fase: {c.stage_label or 'ukendt'} "
        f"| effekt: {effect}"
    )


def _brief_input(technologies: list[TechnologyCard], cases: list[CaseCard]) -> str:
    problems = "\n".join(
        f"- [P{i}] ({AREA_LABELS[p.area]}) {p.name}: {p.description}"
        for i, p in enumerate(OK_PROBLEMS, start=1)
    )
    tech_lines = "\n".join(_tech_line(i, t) for i, t in enumerate(technologies, 1)) or "- (ingen)"
    case_lines = "\n".join(_case_line(i, c) for i, c in enumerate(cases, 1)) or "- (ingen)"
    return f"PROBLEMS:\n{problems}\n\nTECHNOLOGIES:\n{tech_lines}\n\nCASES:\n{case_lines}"


def _ref_map(prefix: str, ids: list[uuid.UUID]) -> dict[str, uuid.UUID]:
    return {f"{prefix}{i}": value for i, value in enumerate(ids, start=1)}


def generate_ok_brief(db: Session, provider: AIProvider) -> dict[str, Any]:
    """Generér og gem Til OK. Uden fund kaldes modellen ikke."""
    rows = visible_rows(db)
    technologies = [t for t in technology_cards(db, rows) if t.case_count or t.vendors][
        :_MAX_BRIEF_TECHNOLOGIES
    ]
    cases = case_cards(db, rows)[:_MAX_BRIEF_CASES]
    tech_refs = _ref_map("T", [t.id for t in technologies])
    case_refs = _ref_map("C", [c.id for c in cases])
    problem_refs = {f"P{i}": p.key for i, p in enumerate(OK_PROBLEMS, start=1)}

    top_now: list[dict[str, Any]] = []
    problems: dict[str, dict[str, Any]] = {}
    discarded = 0
    if technologies or cases:
        result = call_with_schema(
            provider,
            prompt_id=OK_BRIEF_PROMPT_ID,
            prompt_version=OK_BRIEF_PROMPT_VERSION,
            system=OK_BRIEF_SYSTEM,
            user=_brief_input(technologies, cases),
            result_model=OkBriefResult,
        )
        for point in result.top_now:
            case_ids = [str(case_refs[r]) for r in point.refs if r in case_refs]
            tech_ids = [str(tech_refs[r]) for r in point.refs if r in tech_refs]
            # Et punkt uden gyldig henvisning er ikke dokumenteret.
            if not case_ids and not tech_ids:
                discarded += 1
                continue
            if len(top_now) < 3:
                top_now.append(
                    {
                        "text": _line(point.text, 300),
                        "case_ids": case_ids,
                        "technology_ids": tech_ids,
                    }
                )
        for entry in result.problems:
            key = problem_refs.get(entry.problem)
            if key is None or key in problems:
                discarded += 1
                continue
            problems[key] = {
                "technology_ids": [
                    str(tech_refs[r]) for r in dict.fromkeys(entry.technologies) if r in tech_refs
                ][:3],
                "cases": [
                    {"item_id": str(case_refs[c.ref]), "why": _line(c.why, 200)}
                    for c in entry.cases
                    if c.ref in case_refs
                ][:3],
                "next_step": _line(entry.next_step, 300),
            }

    value: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "prompt_version": OK_BRIEF_PROMPT_VERSION,
        "technology_count": len(technologies),
        "case_count": len(cases),
        "discarded": discarded,
        "top_now": top_now,
        "problems": [
            {
                "key": p.key,
                **problems.get(p.key, {"technology_ids": [], "cases": [], "next_step": ""}),
            }
            for p in OK_PROBLEMS
        ],
    }
    row = db.get(AppSetting, OK_BRIEF_KEY)
    if row is None:
        db.add(AppSetting(key=OK_BRIEF_KEY, value=value))
    else:
        row.value = value
        row.updated_at = datetime.now(UTC)
    db.flush()
    logger.info(
        "ok_brief_generated technologies=%d cases=%d top=%d discarded=%d",
        len(technologies),
        len(cases),
        len(top_now),
        discarded,
    )
    return value


__all__ = [
    "AREAS",
    "MarketOutcome",
    "documents_for_market",
    "ensure_catalog",
    "generate_ok_brief",
    "process_market_document",
]
