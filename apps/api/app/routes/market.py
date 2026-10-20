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
from app.config import get_settings
from app.db import get_db
from app.enums import AccessClass, Frequency, RetrievalMethod, RunStatus, SourceType, UserRole
from app.errors import ApiError
from app.ingestion.fetch import ensure_public_http_url, fetch_url
from app.ingestion.service import ingest_bytes
from app.market.catalog import AREA_LABELS, AREAS, PEERS
from app.market.views import (
    CaseCard,
    TechnologyCard,
    TechnologyRef,
    VendorRow,
    case_cards,
    technology_cards,
    vendor_rows,
)
from app.models import Document, Source
from app.models_market import MarketItem
from app.models_runs import WorkerRun
from app.models_settings import AppSetting
from app.pipeline.market import OK_BRIEF_KEY, process_market_document
from app.routes.documents import ai_provider_dep
from app.storage import get_storage

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
    # De selskaber, der ligner OK, som radaren endnu ikke har en AI-case fra.
    peers_without_cases: list[str] = Field(default_factory=list)


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
        peers_without_cases=[p.name for p in PEERS if not any(c.peer == p.name for c in all_cards)],
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


# --- Tilføj case fra link (kun admin) ---

_LINK_SOURCES = {
    False: ("Manuelt tilføjede links", SourceType.media),
    True: ("Manuelt tilføjede leverandørsider", SourceType.vendor_case),
}


class LinkIn(BaseModel):
    url: str = Field(min_length=8, max_length=2000)
    vendor: bool = False


class LinkOut(BaseModel):
    title: str | None
    already_known: bool
    relevant: bool
    technologies: int
    cases: int
    message: str


def _link_source(db: Session, vendor: bool) -> Source:
    name, source_type = _LINK_SOURCES[vendor]
    source = db.scalar(select(Source).where(Source.name == name))
    if source is None:
        source = Source(
            name=name,
            source_type=source_type,
            retrieval_method=RetrievalMethod.manual_upload,
            frequency=Frequency.manual,
            access_class=AccessClass.public,
            active=True,
            notes="Offentlige links, som konsulenten selv har tilføjet (fx LinkedIn-opslag, "
            "konferenceoplæg og kundecases).",
        )
        db.add(source)
        db.flush()
    return source


@router.post("/market/links", response_model=LinkOut)
def add_market_link(
    body: LinkIn,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.admin)),
    provider: AIProvider = Depends(ai_provider_dep),
) -> LinkOut:
    """Hent ét offentligt link og læs det med det samme. Den stærkeste viden
    om danske kundecentre står ofte i opslag og oplæg, ikke i nyhederne. Samme
    regler som alle andre fund: ordret citat, tal skal stå i kilden."""
    url = body.url.strip()
    ensure_public_http_url(url)
    settings = get_settings()
    source = _link_source(db, body.vendor)
    fetched = fetch_url(
        url, timeout_seconds=settings.fetch_timeout_seconds, max_bytes=settings.fetch_max_bytes
    )
    result = ingest_bytes(
        db,
        get_storage(),
        source,
        fetched.data,
        fetched.content_type,
        canonical_url=fetched.final_url,
    )
    document = result.document
    if document.market_extracted_at is not None:
        db.commit()
        return LinkOut(
            title=document.title,
            already_known=True,
            relevant=bool(document.market_relevant),
            technologies=0,
            cases=0,
            message="Linket er allerede læst af radaren.",
        )
    try:
        outcome = process_market_document(db, provider, document)
    except AIProviderRejected as exc:
        raise ApiError(502, "ai_provider_rejected", str(exc)) from exc
    except (AISchemaError, AIRefusal, AIDocumentRejected, AIProviderError) as exc:
        raise ApiError(502, "link_failed", "Linket kunne ikke læses. Prøv igen.") from exc
    record(
        db,
        entity_type=AuditEntity.source,
        entity_id=source.id,
        action=AuditAction.created,
        actor_user_id=user.user_id,
        changes={"link": fetched.final_url, "cases": outcome.cases},
    )
    db.commit()
    if not outcome.relevant:
        message = "Radaren fandt ikke AI i kundeservice, salg eller support i linket."
    elif outcome.cases or outcome.technologies:
        message = (
            f"Fundet: {outcome.cases} case(s) og {outcome.technologies} teknologi(er). "
            "Tryk “Opdatér Til OK” for at tage dem med."
        )
    else:
        message = "Linket er relevant, men radaren fandt ingen case med citat i det."
    return LinkOut(
        title=document.title,
        already_known=False,
        relevant=outcome.relevant,
        technologies=outcome.technologies,
        cases=outcome.cases,
        message=message,
    )
