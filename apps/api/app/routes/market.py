"""Den forenklede radar: Til OK, Teknologier og Sådan gør andre.

Alle læsevisninger bygger på synlige markedsfund (market/views.py). Til OK
er AI-sammenfattet; serveren slår hver henvisning op på ny ved læsning, så
et skjult eller slettet fund aldrig vises.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
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
from app.market.catalog import AREA_LABELS, AREAS, OK_PROBLEMS
from app.market.views import (
    CaseCard,
    TechnologyCard,
    TechnologyRef,
    case_cards,
    technology_cards,
    visible_rows,
)
from app.models_market import MarketItem
from app.models_settings import AppSetting
from app.pipeline.market import OK_BRIEF_KEY, generate_ok_brief
from app.routes.documents import ai_provider_dep

router = APIRouter(tags=["market"])

Area = Literal["salg", "kundeservice", "support"]
Region = Literal["danmark", "norden", "verden"]


class AreaCount(BaseModel):
    area: str
    label: str
    count: int


class TechnologiesOut(BaseModel):
    items: list[TechnologyCard]
    areas: list[AreaCount]


@router.get("/market/technologies", response_model=TechnologiesOut)
def list_market_technologies(
    area: Area | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> TechnologiesOut:
    cards = technology_cards(db)
    counts = [
        AreaCount(area=a, label=AREA_LABELS[a], count=sum(1 for c in cards if a in c.areas))
        for a in AREAS
    ]
    if area is not None:
        cards = [c for c in cards if area in c.areas]
    return TechnologiesOut(items=cards, areas=counts)


class CasesOut(BaseModel):
    items: list[CaseCard]
    total: int
    technologies: list[TechnologyRef]


@router.get("/market/cases", response_model=CasesOut)
def list_market_cases(
    area: Area | None = Query(default=None),
    region: Region | None = Query(default=None),
    technology_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> CasesOut:
    cards = case_cards(db)
    # Filtermuligheder: teknologier, der faktisk har cases.
    options: dict[uuid.UUID, TechnologyRef] = {}
    for card in cards:
        if card.technology is not None:
            options.setdefault(card.technology.id, card.technology)
    if area is not None:
        cards = [c for c in cards if area in c.areas]
    if region is not None:
        cards = [c for c in cards if c.region == region]
    if technology_id is not None:
        cards = [c for c in cards if c.technology and c.technology.id == technology_id]
    return CasesOut(
        items=cards,
        total=len(cards),
        technologies=sorted(options.values(), key=lambda t: t.label.casefold()),
    )


class ItemUpdate(BaseModel):
    hidden: bool


class ItemOut(BaseModel):
    id: uuid.UUID
    hidden: bool


@router.patch("/market/items/{item_id}", response_model=ItemOut)
def update_market_item(
    item_id: uuid.UUID,
    body: ItemUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> ItemOut:
    """Skjul (eller vis igen) et forkert fund. Intet slettes."""
    item = db.get(MarketItem, item_id)
    if item is None:
        raise ApiError(404, "not_found", "Fundet findes ikke.")
    if item.hidden != body.hidden:
        record(
            db,
            entity_type=AuditEntity.market_item,
            entity_id=item.id,
            action=AuditAction.updated,
            actor_user_id=user.user_id,
            changes={"hidden": {"fra": item.hidden, "til": body.hidden}},
        )
        item.hidden = body.hidden
        item.hidden_at = datetime.now(UTC) if body.hidden else None
        item.hidden_by_user_id = user.user_id if body.hidden else None
    db.commit()
    return ItemOut(id=item.id, hidden=item.hidden)


# --- Til OK ---


class CaseRef(BaseModel):
    id: uuid.UUID
    company: str
    source_url: str | None


class TopPoint(BaseModel):
    text: str
    cases: list[CaseRef]
    technologies: list[TechnologyRef]


class BriefCase(BaseModel):
    case: CaseCard
    why: str


class Effect(BaseModel):
    company: str
    effect: str
    kpi_label: str | None
    effect_source_label: str | None
    source_url: str | None


class Contact(BaseModel):
    name: str
    kind: Literal["leverandør", "reference"]
    danish_supported: bool | None = None


class ProblemOut(BaseModel):
    key: str
    area: str
    area_label: str
    name: str
    description: str
    technologies: list[TechnologyRef]
    cases: list[BriefCase]
    effects: list[Effect]
    contacts: list[Contact]
    next_step: str


class OkBriefOut(BaseModel):
    generated_at: datetime | None = None
    prompt_version: str | None = None
    technology_count: int = 0
    case_count: int = 0
    top_now: list[TopPoint] = Field(default_factory=list)
    problems: list[ProblemOut] = Field(default_factory=list)


def _brief_out(db: Session, value: dict[str, Any] | None, area: str | None) -> OkBriefOut:
    rows = visible_rows(db)
    cases = case_cards(db, rows)
    technologies = technology_cards(db, rows)
    # Et gemt fund kan siden være slået sammen med andre: slå op på alle id'er.
    case_by_item = {item_id: card for card in cases for item_id in card.item_ids}
    tech_by_id = {t.id: t for t in technologies}

    def find_case(raw: str) -> CaseCard | None:
        try:
            return case_by_item.get(uuid.UUID(raw))
        except ValueError:
            return None

    def find_tech(raw: str) -> TechnologyCard | None:
        try:
            return tech_by_id.get(uuid.UUID(raw))
        except ValueError:
            return None

    def tech_ref(card: TechnologyCard) -> TechnologyRef:
        return TechnologyRef(id=card.id, label=card.label)

    value = value or {}
    top: list[TopPoint] = []
    for point in value.get("top_now", []):
        point_cases = [c for raw in point.get("case_ids", []) if (c := find_case(raw))]
        point_techs = [t for raw in point.get("technology_ids", []) if (t := find_tech(raw))]
        if not point_cases and not point_techs:
            continue  # fundet bag punktet er skjult
        top.append(
            TopPoint(
                text=point["text"],
                cases=[
                    CaseRef(id=c.id, company=c.company, source_url=c.source.url)
                    for c in point_cases
                ],
                technologies=[tech_ref(t) for t in point_techs],
            )
        )

    stored = {p["key"]: p for p in value.get("problems", [])}
    problems: list[ProblemOut] = []
    for problem in OK_PROBLEMS:
        if area is not None and problem.area != area:
            continue
        entry = stored.get(problem.key, {})
        techs = [t for raw in entry.get("technology_ids", []) if (t := find_tech(raw))]
        brief_cases: list[BriefCase] = []
        for ref in entry.get("cases", []):
            card = find_case(ref.get("item_id", ""))
            if card is not None and all(b.case.id != card.id for b in brief_cases):
                brief_cases.append(BriefCase(case=card, why=ref.get("why", "")))
        effects = [
            Effect(
                company=b.case.company,
                effect=b.case.effect,
                kpi_label=b.case.kpi_label,
                effect_source_label=b.case.effect_source_label,
                source_url=b.case.source.url,
            )
            for b in brief_cases
            if b.case.effect
        ]
        contacts: list[Contact] = []
        for t in techs:
            for vendor in t.vendors:
                if not vendor.via_case and all(c.name != vendor.name for c in contacts):
                    contacts.append(
                        Contact(
                            name=vendor.name,
                            kind="leverandør",
                            danish_supported=vendor.danish_supported,
                        )
                    )
        contacts = sorted(contacts, key=lambda c: c.danish_supported is not True)[:5]
        for b in brief_cases:
            if all(c.name != b.case.company for c in contacts):
                contacts.append(Contact(name=b.case.company, kind="reference"))
        problems.append(
            ProblemOut(
                key=problem.key,
                area=problem.area,
                area_label=AREA_LABELS[problem.area],
                name=problem.name,
                description=problem.description,
                technologies=[tech_ref(t) for t in techs],
                cases=brief_cases,
                effects=effects,
                contacts=contacts,
                next_step=entry.get("next_step", ""),
            )
        )
    generated = value.get("generated_at")
    return OkBriefOut(
        generated_at=datetime.fromisoformat(generated) if generated else None,
        prompt_version=value.get("prompt_version"),
        technology_count=sum(1 for t in technologies if t.case_count or t.vendors),
        case_count=len(cases),
        top_now=top,
        problems=problems,
    )


@router.get("/ok-brief", response_model=OkBriefOut)
def get_ok_brief(
    area: Area | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> OkBriefOut:
    row = db.get(AppSetting, OK_BRIEF_KEY)
    return _brief_out(db, row.value if row else None, area)


_AUDIT_ID = uuid.uuid5(uuid.NAMESPACE_URL, "ai-radar:setting:ok_brief")


@router.post("/ok-brief/generate", response_model=OkBriefOut)
def post_generate_ok_brief(
    db: Session = Depends(get_db),
    provider: AIProvider = Depends(ai_provider_dep),
    user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> OkBriefOut:
    try:
        value = generate_ok_brief(db, provider)
    except AIProviderRejected as exc:
        raise ApiError(502, "ai_provider_rejected", str(exc)) from exc
    except (AISchemaError, AIRefusal, AIDocumentRejected, AIProviderError) as exc:
        raise ApiError(502, "ok_brief_failed", "Til OK kunne ikke opdateres. Prøv igen.") from exc
    record(
        db,
        entity_type=AuditEntity.setting,
        entity_id=_AUDIT_ID,
        action=AuditAction.created,
        actor_user_id=user.user_id,
        changes={"top_now": len(value["top_now"]), "discarded": value["discarded"]},
    )
    db.commit()
    return _brief_out(db, value, None)
