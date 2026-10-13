"""Markedsfund samlet til kort: teknologier og cases.

Bruges af API'et (routes/market.py) og af Til OK-syntesen, så direktøren
og AI'en ser de samme data. Kun synlige fund: ikke skjult, ikke demo og
aldrig fra interne kilder.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import AccessClass
from app.market.catalog import (
    AREA_LABELS,
    CATALOG_BY_NAME,
    REGION_LABELS,
    TECH_CATALOG,
    region,
)
from app.models import Document, Source
from app.models_claims import Company, Technology
from app.models_market import KIND_CASE, KIND_TECHNOLOGY, MarketItem
from app.pipeline.entities import normalize_alias, preload

VENDOR_SOURCE_TYPES = {"vendor_case", "vendor_claim"}

KPI_LABELS = {
    "kontaktomkostning": "Kontaktomkostning",
    "ventetid": "Ventetid",
    "løst_ved_første_kontakt": "Løst ved første kontakt",
    "kundetilfredshed": "Kundetilfredshed",
    "konvertering": "Konvertering",
    "mersalg": "Mersalg",
    "churn": "Fastholdelse/churn",
    "produktivitet": "Produktivitet",
    "andet": "Andet",
}
STAGE_LABELS = {"idé": "Idé", "pilot": "Pilot", "drift": "I drift", "skaleret": "Skaleret"}
EFFECT_SOURCE_LABELS = {
    "virksomheden": "Virksomhedens egne tal",
    "leverandøren": "Leverandørens tal",
    "uafhængig": "Uafhængig kilde",
}


@dataclass
class Row:
    item: MarketItem
    document: Document
    source: Source


def visible_rows(db: Session, kind: str | None = None) -> list[Row]:
    """Synlige fund, nyeste først, med dokument og kilde."""
    stmt = (
        select(MarketItem, Document, Source)
        .join(Document, Document.id == MarketItem.document_id)
        .join(Source, Source.id == Document.source_id)
        .where(
            MarketItem.hidden.is_(False),
            Document.is_demo.is_(False),
            Source.access_class != AccessClass.restricted,
        )
        .order_by(MarketItem.observed_at.desc(), MarketItem.id)
    )
    if kind is not None:
        stmt = stmt.where(MarketItem.kind == kind)
    rows = [Row(item, document, source) for item, document, source in db.execute(stmt).all()]
    company_ids = {
        cid for r in rows for cid in (r.item.company_id, r.item.vendor_company_id) if cid
    }
    preload(db, Company, company_ids)
    preload(db, Technology, {r.item.technology_id for r in rows if r.item.technology_id})
    return rows


# --- Fælles byggesten ---


class SourceRef(BaseModel):
    name: str
    url: str | None = None
    title: str | None = None
    vendor_source: bool = False


class TechnologyRef(BaseModel):
    id: uuid.UUID
    label: str


def _source_ref(row: Row) -> SourceRef:
    return SourceRef(
        name=row.source.name,
        url=row.document.canonical_url,
        title=row.document.title,
        vendor_source=str(row.source.source_type) in VENDOR_SOURCE_TYPES,
    )


def _company_name(db: Session, company_id: uuid.UUID | None) -> str | None:
    if company_id is None:
        return None
    company = db.get(Company, company_id)
    return company.name if company else None


def technology_label(technology: Technology) -> str:
    entry = CATALOG_BY_NAME.get(technology.name)
    return entry.label if entry else technology.name


def _technology_ref(db: Session, technology_id: uuid.UUID | None) -> TechnologyRef | None:
    if technology_id is None:
        return None
    technology = db.get(Technology, technology_id)
    if technology is None:
        return None
    return TechnologyRef(id=technology.id, label=technology_label(technology))


# --- Cases ---


class CaseCard(BaseModel):
    id: uuid.UUID
    item_ids: list[uuid.UUID]
    company: str
    company_id: uuid.UUID | None
    country: str | None
    region: str
    region_label: str
    industry: str | None
    areas: list[str]
    what_they_did: str | None
    technology: TechnologyRef | None
    technology_name: str | None
    vendor: str | None
    stage: str | None
    stage_label: str | None
    scope: str | None
    effect: str | None
    kpi: str | None
    kpi_label: str | None
    effect_source: str | None
    effect_source_label: str | None
    lesson: str | None
    quote: str
    source: SourceRef
    also_reported_by: list[str] = Field(default_factory=list)
    observed_at: datetime


@dataclass
class CaseGroup:
    key: tuple[Any, ...]
    rows: list[Row] = field(default_factory=list)

    @property
    def item_ids(self) -> list[uuid.UUID]:
        return [r.item.id for r in self.rows]

    @property
    def areas(self) -> list[str]:
        return _union_areas(self.rows)


def _union_areas(rows: list[Row]) -> list[str]:
    seen: list[str] = []
    for r in rows:
        for area in r.item.areas or []:
            if area not in seen:
                seen.append(area)
    return seen


def group_cases(rows: list[Row]) -> list[CaseGroup]:
    """Samme virksomhed og teknologi omtalt i flere artikler = én case."""
    groups: dict[tuple[Any, ...], CaseGroup] = {}
    for row in rows:  # nyeste først
        if row.item.kind != KIND_CASE:
            continue
        technology_key: Any = row.item.technology_id or normalize_alias(
            str(row.item.data.get("technology_name") or "")
        )
        key = (row.item.company_id, technology_key)
        groups.setdefault(key, CaseGroup(key=key)).rows.append(row)
    return list(groups.values())


def _first(rows: list[Row], name: str) -> Any:
    for r in rows:
        value = r.item.data.get(name)
        if value not in (None, ""):
            return value
    return None


def case_card(db: Session, group: CaseGroup) -> CaseCard:
    primary = group.rows[0]
    rows = group.rows
    # Effekten og citatet hører sammen: brug citatet fra det fund, der
    # bærer effekten, når det nyeste fund ikke har en.
    effect_row = next((r for r in rows if r.item.data.get("effect")), primary)
    country = _first(rows, "country")
    stage = _first(rows, "adoption_stage")
    kpi = effect_row.item.data.get("kpi") if effect_row.item.data.get("effect") else None
    effect_source = (
        effect_row.item.data.get("effect_source")
        if kpi or effect_row.item.data.get("effect")
        else None
    )
    reg = region(country)
    also = []
    for r in rows[1:]:
        if r.source.name not in also and r.source.name != effect_row.source.name:
            also.append(r.source.name)
    return CaseCard(
        id=primary.item.id,
        item_ids=group.item_ids,
        company=_company_name(db, primary.item.company_id) or "Ukendt organisation",
        company_id=primary.item.company_id,
        country=country,
        region=reg,
        region_label=REGION_LABELS[reg],
        industry=_first(rows, "industry"),
        areas=group.areas,
        what_they_did=_first(rows, "what_they_did_da"),
        technology=_technology_ref(db, primary.item.technology_id),
        technology_name=_first(rows, "technology_name"),
        vendor=_company_name(
            db, next((r.item.vendor_company_id for r in rows if r.item.vendor_company_id), None)
        ),
        stage=stage,
        stage_label=STAGE_LABELS.get(stage) if stage else None,
        scope=_first(rows, "scope"),
        effect=effect_row.item.data.get("effect"),
        kpi=kpi,
        kpi_label=KPI_LABELS.get(kpi) if kpi else None,
        effect_source=effect_source,
        effect_source_label=EFFECT_SOURCE_LABELS.get(effect_source) if effect_source else None,
        lesson=_first(rows, "lesson"),
        quote=effect_row.item.quote,
        source=_source_ref(effect_row),
        also_reported_by=also,
        observed_at=primary.item.observed_at,
    )


def _case_sort_key(card: CaseCard) -> tuple[int, int, float]:
    # Danske og nordiske cases og cases med dokumenteret effekt først.
    region_rank = {"danmark": 0, "norden": 1}.get(card.region, 2)
    return (region_rank, 0 if card.effect else 1, -card.observed_at.timestamp())


def case_cards(db: Session, rows: list[Row] | None = None) -> list[CaseCard]:
    rows = rows if rows is not None else visible_rows(db, KIND_CASE)
    cards = [case_card(db, group) for group in group_cases(rows)]
    return sorted(cards, key=_case_sort_key)


# --- Teknologier ---


class VendorOffer(BaseModel):
    company_id: uuid.UUID | None
    name: str
    product: str | None = None
    danish_supported: bool | None = None
    quote: str | None = None
    source: SourceRef | None = None
    item_ids: list[uuid.UUID] = Field(default_factory=list)
    # Kendt fra en kundecase, ikke fra leverandørens eget tilbud.
    via_case: bool = False


class TechnologyCard(BaseModel):
    id: uuid.UUID
    label: str
    areas: list[str]
    what: str | None
    value: str | None
    is_new: bool
    vendors: list[VendorOffer]
    case_count: int
    latest_at: datetime | None


def technology_cards(db: Session, rows: list[Row] | None = None) -> list[TechnologyCard]:
    """Ét kort pr. teknologi: katalogets teknologier og de nye, radaren har
    fundet. Sorteret efter, hvor meget radaren har fundet."""
    rows = rows if rows is not None else visible_rows(db)
    by_technology: dict[uuid.UUID, list[Row]] = {}
    for row in rows:
        if row.item.technology_id is not None:
            by_technology.setdefault(row.item.technology_id, []).append(row)

    catalog = {
        t.name: t
        for t in db.scalars(
            select(Technology).where(Technology.name.in_([e.name for e in TECH_CATALOG]))
        ).all()
    }
    technology_ids = set(by_technology) | {t.id for t in catalog.values()}
    preload(db, Technology, technology_ids)

    cards: list[TechnologyCard] = []
    for technology_id in technology_ids:
        technology = db.get(Technology, technology_id)
        if technology is None:
            continue
        tech_rows = by_technology.get(technology_id, [])
        entry = CATALOG_BY_NAME.get(technology.name)
        offers = [r for r in tech_rows if r.item.kind == KIND_TECHNOLOGY]
        cases = [r for r in tech_rows if r.item.kind == KIND_CASE]
        vendors: dict[uuid.UUID | str, VendorOffer] = {}
        for r in offers:
            key: uuid.UUID | str = r.item.vendor_company_id or str(r.item.id)
            offer = vendors.get(key)
            if offer is None:
                vendors[key] = VendorOffer(
                    company_id=r.item.vendor_company_id,
                    name=_company_name(db, r.item.vendor_company_id) or "Ukendt leverandør",
                    product=r.item.data.get("product"),
                    danish_supported=r.item.data.get("danish_supported"),
                    quote=r.item.quote,
                    source=_source_ref(r),
                    item_ids=[r.item.id],
                )
            else:
                offer.item_ids.append(r.item.id)
                if r.item.data.get("danish_supported") is True:
                    offer.danish_supported = True
        for r in cases:
            vendor_id = r.item.vendor_company_id
            if vendor_id is not None and vendor_id not in vendors:
                vendors[vendor_id] = VendorOffer(
                    company_id=vendor_id,
                    name=_company_name(db, vendor_id) or "Ukendt leverandør",
                    source=_source_ref(r),
                    via_case=True,
                )
        if entry is None and not tech_rows:
            continue
        areas = list(entry.areas) if entry else _union_areas(tech_rows)
        cards.append(
            TechnologyCard(
                id=technology.id,
                label=technology_label(technology),
                areas=areas,
                what=entry.what
                if entry
                else _first(offers + cases, "what_it_does_da") or _first(cases, "what_they_did_da"),
                value=entry.value if entry else _first(offers, "business_value_da"),
                is_new=entry is None,
                vendors=sorted(
                    vendors.values(),
                    key=lambda v: (v.via_case, v.danish_supported is not True, v.name.casefold()),
                ),
                case_count=len(group_cases(cases)),
                latest_at=tech_rows[0].item.observed_at if tech_rows else None,
            )
        )
    return sorted(
        cards,
        key=lambda c: (-(c.case_count + len(c.vendors)), c.label.casefold()),
    )


def area_label(area: str) -> str:
    return AREA_LABELS.get(area, area)
