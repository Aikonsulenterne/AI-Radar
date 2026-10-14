"""Den forenklede radar: Til OK, Teknologier, Sådan gør andre og Kilder.

Alle læsevisninger bygger på synlige markedsfund (market/views.py). Til OK
er AI-sammenfattet; serveren slår hver henvisning op på ny ved læsning, så
et skjult eller slettet fund aldrig vises, og hver case vises højst én gang.
Status (Klar nu / Værd at afprøve / Hold øje med) beregnes af data.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
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
from app.enums import AccessClass, RunStatus, UserRole
from app.errors import ApiError
from app.mailer import send_brief
from app.market.catalog import AREA_LABELS, AREAS, OK_PROBLEMS
from app.market.views import (
    CaseCard,
    CaseSummary,
    TechnologyCard,
    TechnologyRef,
    VendorRow,
    case_cards,
    case_summary,
    technology_cards,
    vendor_rows,
    visible_rows,
)
from app.models import Document, Source
from app.models_market import MarketItem
from app.models_runs import WorkerRun
from app.models_settings import AppSetting
from app.pipeline.market import OK_BRIEF_KEY, generate_ok_brief
from app.routes.documents import ai_provider_dep

router = APIRouter(tags=["market"])

Area = Literal["salg", "kundeservice", "support"]
Region = Literal["danmark", "norden", "verden"]

_MONTHS = (
    "januar februar marts april maj juni juli august september oktober november december"
).split()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _brief_value(db: Session) -> dict[str, Any]:
    row = db.get(AppSetting, OK_BRIEF_KEY)
    return row.value if row else {}


class MeOut(BaseModel):
    user_id: uuid.UUID | None
    role: UserRole
    # Seneste gennemførte kørsel eller Til OK — vises som "Opdateret …".
    last_updated: datetime | None = None


@router.get("/me", response_model=MeOut)
def get_me(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> MeOut:
    """Den indloggede brugers rolle — frontend viser kun admin-værktøjer til Admin."""
    last_run = db.scalar(
        select(func.max(WorkerRun.finished_at)).where(WorkerRun.status == RunStatus.succeeded)
    )
    generated = _brief_value(db).get("generated_at")
    candidates = [_aware(v) for v in (last_run,) if v is not None]
    if generated:
        candidates.append(_aware(datetime.fromisoformat(generated)))
    return MeOut(
        user_id=user.user_id, role=user.role, last_updated=max(candidates) if candidates else None
    )


# --- Teknologier ---


class AreaCount(BaseModel):
    area: str
    label: str
    count: int


class NewOnMarket(BaseModel):
    technology: TechnologyCard
    why: str | None
    date_label: str


class TechnologiesOut(BaseModel):
    items: list[TechnologyCard]
    areas: list[AreaCount]
    new_on_market: list[NewOnMarket]
    vendors: list[VendorRow]


_NEW_WINDOW = timedelta(days=90)


def _month_label(value: datetime) -> str:
    return f"{_MONTHS[value.month - 1][:3]}. {value.year}"


def _new_on_market(cards: list[TechnologyCard], why: dict[str, str]) -> list[NewOnMarket]:
    """Højst tre: teknologier lanceret/annonceret eller fundet de seneste 90
    dage. Dem, Til OK-prompten har begrundet, først."""
    cutoff = datetime.now(UTC) - _NEW_WINDOW

    def recent(card: TechnologyCard) -> datetime | None:
        if card.launched:
            launched = datetime.fromisoformat(card.launched).replace(tzinfo=UTC)
            return launched if launched >= cutoff else None
        if card.is_new and card.first_seen_at and _aware(card.first_seen_at) >= cutoff:
            return _aware(card.first_seen_at)
        return None

    found = [(card, when) for card in cards if (when := recent(card)) is not None]
    found.sort(key=lambda pair: (str(pair[0].id) not in why, -pair[1].timestamp()))
    return [
        NewOnMarket(
            technology=card,
            why=why.get(str(card.id)),
            date_label=(
                f"Lanceret {_month_label(when)}"
                if card.launched
                else f"Fundet {_month_label(when)}"
            ),
        )
        for card, when in found[:3]
    ]


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
    why = {n["technology_id"]: n["why"] for n in _brief_value(db).get("new_tech", [])}
    return TechnologiesOut(
        items=cards,
        areas=counts,
        new_on_market=_new_on_market(cards, why),
        vendors=vendor_rows(cards),
    )


# --- Sådan gør andre ---


class CasesOut(BaseModel):
    items: list[CaseCard]
    total: int
    all_total: int
    danish_total: int
    technologies: list[TechnologyRef]


@router.get("/market/cases", response_model=CasesOut)
def list_market_cases(
    area: Area | None = Query(default=None),
    region: Region | None = Query(default=None),
    technology_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> CasesOut:
    """Sorteret efter lighed med OK. Norden omfatter Danmark."""
    all_cards = case_cards(db)
    options: dict[uuid.UUID, TechnologyRef] = {}
    for card in all_cards:
        if card.technology is not None:
            options.setdefault(card.technology.id, card.technology)
    cards = all_cards
    if area is not None:
        cards = [c for c in cards if area in c.areas]
    if region == "danmark":
        cards = [c for c in cards if c.region == "danmark"]
    elif region == "norden":
        cards = [c for c in cards if c.region in ("danmark", "norden")]
    elif region == "verden":
        cards = [c for c in cards if c.region == "verden"]
    if technology_id is not None:
        cards = [c for c in cards if c.technology and c.technology.id == technology_id]
    return CasesOut(
        items=cards,
        total=len(cards),
        all_total=len(all_cards),
        danish_total=sum(1 for c in all_cards if c.region == "danmark"),
        technologies=sorted(options.values(), key=lambda t: t.label.casefold()),
    )


# --- Kilder (kun admin) ---

_SOURCE_TYPE_LABELS = {
    "vendor_case": "Leverandør",
    "vendor_claim": "Leverandør",
    "primary": "Virksomhed",
    "media": "Fagmedie",
    "independent_analysis": "Fagmedie",
    "research": "Fagmedie",
    "early_signal": "Fagmedie",
}


class MarketSourceOut(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    active: bool
    last_checked_at: datetime | None
    relevant_articles: int


@router.get("/market/sources", response_model=list[MarketSourceOut])
def list_market_sources(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> list[MarketSourceOut]:
    """Hvor radaren henter sin viden. Interne kilder er aldrig markedsviden
    og vises ikke her."""
    relevant: dict[uuid.UUID, int] = {
        source_id: int(count)
        for source_id, count in db.execute(
            select(Document.source_id, func.count())
            .where(Document.market_relevant.is_(True))
            .group_by(Document.source_id)
        ).all()
    }
    sources = db.scalars(
        select(Source)
        .where(Source.access_class != AccessClass.restricted)
        .order_by(Source.active.desc(), Source.name)
    ).all()
    return [
        MarketSourceOut(
            id=source.id,
            name=source.name,
            type=_SOURCE_TYPE_LABELS.get(str(source.source_type), "Fagmedie"),
            active=source.active,
            last_checked_at=source.last_checked_at,
            relevant_articles=int(relevant.get(source.id, 0)),
        )
        for source in sources
    ]


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


class MustKnow(BaseModel):
    n: int
    text: str
    source_url: str | None
    href: str | None


class Recommendation(BaseModel):
    action: str
    owner: str
    duration: str


class StatusTechnology(BaseModel):
    id: uuid.UUID
    label: str
    status: str
    status_label: str


class MoreCase(BaseModel):
    id: uuid.UUID
    company: str
    country: str | None
    what: str
    source_url: str | None


class ProblemRow(BaseModel):
    key: str
    title: str
    technology: StatusTechnology | None
    proof: CaseSummary
    because: str
    next_step: str
    more: list[MoreCase]
    vendors: list[str]
    reference: str


class AreaRows(BaseModel):
    area: str
    label: str
    rows: list[ProblemRow]


class Undocumented(BaseModel):
    title: str
    area_label: str


class OkBriefOut(BaseModel):
    generated_at: datetime | None = None
    month_label: str | None = None
    prompt_version: str | None = None
    technology_count: int = 0
    case_count: int = 0
    must_know: list[MustKnow] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    areas: list[AreaRows] = Field(default_factory=list)
    undocumented: list[Undocumented] = Field(default_factory=list)
    # godkendt: direktøren ser denne version · kladde: ny version venter på
    # konsulentens godkendelse (kun Admin ser kladden) · ingen: intet godkendt.
    state: Literal["godkendt", "kladde", "ingen"] = "ingen"
    approved_at: datetime | None = None
    # Kun til Admin: hvad der skete med mailen ved seneste godkendelse.
    mail_status: str | None = None


# Rækkefølgen på Til OK.
_AREA_ORDER = ("kundeservice", "support", "salg")


def _brief_out(db: Session, value: dict[str, Any] | None) -> OkBriefOut:
    rows = visible_rows(db)
    cases = case_cards(db, rows)
    technologies = technology_cards(db, rows)
    # Et gemt fund kan siden være slået sammen med andre: slå op på alle id'er.
    case_by_item = {item_id: card for card in cases for item_id in card.item_ids}
    tech_by_id = {t.id: t for t in technologies}

    def find_case(raw: str | None) -> CaseCard | None:
        try:
            return case_by_item.get(uuid.UUID(raw)) if raw else None
        except ValueError:
            return None

    def find_tech(raw: str | None) -> TechnologyCard | None:
        try:
            return tech_by_id.get(uuid.UUID(raw)) if raw else None
        except ValueError:
            return None

    value = value or {}
    must_know: list[MustKnow] = []
    for point in value.get("must_know", []):
        case = find_case(point.get("case_id"))
        tech = find_tech(point.get("technology_id"))
        if case is None and tech is None:
            continue  # fundet bag punktet er skjult
        if case is not None:
            url, href = case.source.url, f"/cases#case-{case.id}"
        else:
            assert tech is not None
            first = next((v for v in tech.vendors if v.source and v.source.url), None)
            url = first.source.url if first and first.source else None
            href = f"/teknologier#tech-{tech.id}"
        must_know.append(
            MustKnow(n=len(must_know) + 1, text=point["text"], source_url=url, href=href)
        )

    shown: set[uuid.UUID] = set()  # hver case højst én gang på hele siden
    by_area: dict[str, list[ProblemRow]] = {a: [] for a in _AREA_ORDER}
    undocumented: list[Undocumented] = []
    stored = {p["key"]: p for p in value.get("problems", [])}
    for problem in OK_PROBLEMS:
        entry = stored.get(problem.key, {})
        best = find_case(entry.get("best_case_id"))
        if best is not None and best.id in shown:
            best = None
        if best is None:
            undocumented.append(
                Undocumented(title=problem.name, area_label=AREA_LABELS[problem.area])
            )
            continue
        shown.add(best.id)
        more: list[MoreCase] = []
        for raw in entry.get("more_case_ids", []):
            card = find_case(raw)
            if card is not None and card.id not in shown:
                shown.add(card.id)
                more.append(
                    MoreCase(
                        id=card.id,
                        company=card.company,
                        country=card.country_label,
                        what=card.what_they_did or card.effect or "",
                        source_url=card.source.url,
                    )
                )
        tech = find_tech(entry.get("technology_id"))
        if tech is None and best.technology is not None:
            tech = tech_by_id.get(best.technology.id)
        vendors = [v.name for v in (tech.vendors if tech else []) if not v.via_case][:3]
        if not vendors and best.vendor:
            vendors = [best.vendor]
        by_area[problem.area].append(
            ProblemRow(
                key=problem.key,
                title=problem.name,
                technology=StatusTechnology(
                    id=tech.id, label=tech.label, status=tech.status, status_label=tech.status_label
                )
                if tech
                else None,
                proof=case_summary(best),
                because=entry.get("why_comparable", ""),
                next_step=entry.get("next_step", ""),
                more=more,
                vendors=vendors,
                reference=best.company,
            )
        )

    generated = value.get("generated_at")
    generated_at = datetime.fromisoformat(generated) if generated else None
    return OkBriefOut(
        generated_at=generated_at,
        month_label=(
            f"{_MONTHS[generated_at.month - 1]} {generated_at.year}" if generated_at else None
        ),
        prompt_version=value.get("prompt_version"),
        technology_count=sum(1 for t in technologies if t.case_count or t.vendors),
        case_count=len(cases),
        must_know=must_know,
        recommendations=[Recommendation(**r) for r in value.get("recommendations", [])],
        decisions=list(value.get("decisions", [])),
        areas=[
            AreaRows(area=a, label=AREA_LABELS[a], rows=by_area[a])
            for a in _AREA_ORDER
            if by_area[a]
        ],
        undocumented=undocumented,
    )


OK_BRIEF_PUBLISHED_KEY = "ok_brief_published"


def _published_value(db: Session) -> dict[str, Any]:
    row = db.get(AppSetting, OK_BRIEF_PUBLISHED_KEY)
    return row.value if row else {}


def _with_state(db: Session, out: OkBriefOut, draft: dict[str, Any]) -> OkBriefOut:
    published = _published_value(db)
    approved = published.get("approved_at")
    if not published:
        state = "kladde" if draft else "ingen"
    elif draft.get("generated_at") != published.get("generated_at"):
        state = "kladde"
    else:
        state = "godkendt"
    return out.model_copy(
        update={
            "state": state,
            "approved_at": datetime.fromisoformat(approved) if approved else None,
            "mail_status": published.get("mail_status"),
        }
    )


@router.get("/ok-brief", response_model=OkBriefOut)
def get_ok_brief(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> OkBriefOut:
    """Admin ser den nyeste kladde; alle andre ser den senest godkendte version.
    Konsulenten godkender forsiden, før direktøren ser den (beslutning
    2026-10-14: én fejl på forsiden koster mere end fem minutters kontrol)."""
    if user.role == UserRole.admin:
        draft = _brief_value(db)
        return _with_state(db, _brief_out(db, draft), draft)
    published = _published_value(db)
    if not published:
        return OkBriefOut(state="ingen")
    out = _brief_out(db, published)
    approved = published.get("approved_at")
    return out.model_copy(
        update={
            "state": "godkendt",
            "approved_at": datetime.fromisoformat(approved) if approved else None,
        }
    )


class ApproveOut(BaseModel):
    approved_at: datetime
    mail: str


@router.post("/ok-brief/approve", response_model=ApproveOut)
def approve_ok_brief(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> ApproveOut:
    """Godkend den nyeste kladde: direktøren ser den, og den sendes som mail,
    hvis SMTP er sat op."""
    draft = _brief_value(db)
    if not draft:
        raise ApiError(409, "no_draft", "Der er ingen Til OK at godkende endnu.")
    approved_at = datetime.now(UTC)
    value = {
        **draft,
        "approved_at": approved_at.isoformat(),
        "approved_by_user_id": str(user.user_id) if user.user_id else None,
    }
    row = db.get(AppSetting, OK_BRIEF_PUBLISHED_KEY)
    if row is None:
        db.add(AppSetting(key=OK_BRIEF_PUBLISHED_KEY, value=value))
    else:
        row.value = value
        row.updated_at = approved_at
    record(
        db,
        entity_type=AuditEntity.setting,
        entity_id=_AUDIT_ID,
        action=AuditAction.published,
        actor_user_id=user.user_id,
        changes={"generated_at": draft.get("generated_at")},
    )
    db.commit()
    mail = send_brief(_brief_out(db, value).model_dump(mode="json"))
    stored = db.get(AppSetting, OK_BRIEF_PUBLISHED_KEY)
    if stored is not None:
        stored.value = {**stored.value, "mail_status": mail}
        db.commit()
    return ApproveOut(approved_at=approved_at, mail=mail)


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
        changes={"must_know": len(value["must_know"]), "discarded": value["discarded"]},
    )
    db.commit()
    return _with_state(db, _brief_out(db, value), value)
