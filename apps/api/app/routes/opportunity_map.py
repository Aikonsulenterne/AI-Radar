"""Muligheder for OK Kundeservice: fra OK's egne problemer til leverandører,
dokumenteret brug og effekt (direktørvisningen).

Koblingen problem → capability er kurateret her (radarens problemliste og
teknologier); alt indhold derunder er godkendte claims med evidens. Der
beregnes ingen samlet score: problemerne sorteres efter mængden af
dokumentation, og visningen siger det.
"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_role
from app.db import get_db
from app.enums import VENDOR_PREDICATES, EntityType, OpportunityStatus, Predicate, UserRole
from app.models_claims import Claim, Company, Technology
from app.models_opportunities import Opportunity, ProblemTaxonomy
from app.pipeline.entities import entity_name
from app.routes.catalog import (
    _APPROVED,
    _customers_by_vendor,
    _is_nordic,
    _offering_out,
    _technology_out,
    _vendor_facts,
)
from app.schemas_catalog import TechnologyOut

router = APIRouter(tags=["opportunity-map"])

# Kurateret: hvilke capabilities adresserer hvilket OK-problem. Navnene er
# radarens problem- og teknologinavne; ukendte navne springes over.
PROBLEM_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "Repetitive henvendelser": ("Virtual Agent", "Workflow Automation", "Knowledge AI"),
    "Store mailmængder": ("Virtual Agent", "Workflow Automation", "Agent Assist"),
    "Efterbehandling": ("Agent Assist", "Voice AI", "Conversation Intelligence"),
    "Manuel QA": ("Automated QA", "Conversation Intelligence"),
    "Knowledge gaps": ("Knowledge AI", "Knowledge-gap Detection", "Agent Assist"),
    "Genhenvendelser": ("Conversation Intelligence", "Knowledge-gap Detection"),
    "Routing": ("Workflow Automation", "Virtual Agent", "Conversation Intelligence"),
    "Onboarding": ("Knowledge AI", "Agent Assist"),
}


class MapVendorOut(BaseModel):
    company_id: uuid.UUID
    name: str
    nordic_documented: bool
    capabilities: list[str]
    products: list[str]
    # Dokumenterede kunder hos leverandøren — ikke nødvendigvis af netop
    # disse produkter, derfor vist under leverandøren og ikke som brug.
    customers: list[str] = Field(default_factory=list)


class MapReferenceOut(BaseModel):
    """En organisation med dokumenteret brug af en af capabilities."""

    name: str
    how: str
    source_url: str | None = None


class MapEffectOut(BaseModel):
    organization: str
    effect: str
    excerpt: str | None
    source_name: str | None
    source_url: str | None
    vendor_source: bool


class MapOpportunityOut(BaseModel):
    id: uuid.UUID
    title: str
    status: OpportunityStatus
    approved: bool
    recommended_next_action: str


class ProblemOpportunityOut(BaseModel):
    problem_id: uuid.UUID
    name: str
    description: str
    capabilities: list[TechnologyOut]
    vendors: list[MapVendorOut]
    references: list[MapReferenceOut]
    effects: list[MapEffectOut]
    opportunities: list[MapOpportunityOut]
    # Antal dokumenterede elementer — bruges kun til sortering, vises ikke
    # som score.
    evidence_count: int = 0


class OpportunityMapOut(BaseModel):
    problems: list[ProblemOpportunityOut] = Field(default_factory=list)


_VENDOR_SOURCES = {"vendor_case", "vendor_claim"}


def _problem_row(
    db: Session,
    problem: ProblemTaxonomy,
    technologies: dict[str, Technology],
) -> ProblemOpportunityOut:
    capability_techs = [
        technologies[name]
        for name in PROBLEM_CAPABILITIES.get(problem.name, ())
        if name in technologies
    ]
    tech_ids = {t.id for t in capability_techs}
    tech_names = {t.id: t.name for t in capability_techs}

    claims = (
        db.scalars(
            select(Claim).where(
                Claim.object_entity_type == EntityType.technology,
                Claim.object_entity_id.in_(tech_ids),
                Claim.review_status.in_(_APPROVED),
                Claim.subject_entity_type == EntityType.company,
            )
        ).all()
        if tech_ids
        else []
    )

    # Leverandører: tilbud på problemets capabilities.
    vendor_rows: dict[uuid.UUID, MapVendorOut] = {}
    adopter_ids: set[uuid.UUID] = set()
    references: list[MapReferenceOut] = []
    seen_refs: set[tuple[str, str]] = set()
    for claim in claims:
        name = entity_name(db, claim.subject_entity_type, claim.subject_entity_id) or "?"
        capability = tech_names.get(claim.object_entity_id or uuid.UUID(int=0), "?")
        if claim.predicate == Predicate.OFFERS_CAPABILITY:
            row = vendor_rows.setdefault(
                claim.subject_entity_id,
                MapVendorOut(
                    company_id=claim.subject_entity_id,
                    name=name,
                    nordic_documented=False,
                    capabilities=[],
                    products=[],
                ),
            )
            if capability not in row.capabilities:
                row.capabilities.append(capability)
            if claim.object_text and claim.object_text not in row.products:
                row.products.append(claim.object_text)
            continue
        if claim.predicate in VENDOR_PREDICATES:
            continue
        adopter_ids.add(claim.subject_entity_id)
        key = (name, capability)
        if key in seen_refs:
            continue
        seen_refs.add(key)
        existing = next((r for r in references if r.name == name), None)
        if existing is not None:
            existing.how = f"{existing.how}, {capability}"
        else:
            references.append(
                MapReferenceOut(
                    name=name,
                    how=f"Bruger {capability}",
                    source_url=_offering_out(db, claim).source_url,
                )
            )

    vendors_by_id = {
        vendor_id: company
        for vendor_id in vendor_rows
        if (company := db.get(Company, vendor_id)) is not None
    }
    for vendor_id, customers in _customers_by_vendor(db, vendors_by_id).items():
        vendor_rows[vendor_id].customers = sorted(customers)
    facts = _vendor_facts(db, set(vendor_rows))
    for vendor_id, row in vendor_rows.items():
        row.nordic_documented = _is_nordic(*facts[vendor_id])
    vendors = sorted(
        vendor_rows.values(),
        key=lambda v: (not v.nordic_documented, -len(v.capabilities), v.name.casefold()),
    )

    # Effekter rapporteret af organisationer, der bruger capabilities.
    effects: list[MapEffectOut] = []
    if adopter_ids:
        for claim in db.scalars(
            select(Claim).where(
                Claim.predicate == Predicate.REPORTED_EFFECT,
                Claim.review_status.in_(_APPROVED),
                Claim.subject_entity_id.in_(adopter_ids),
            )
        ).all():
            if not claim.object_text:
                continue
            offering = _offering_out(db, claim)
            effects.append(
                MapEffectOut(
                    organization=entity_name(db, claim.subject_entity_type, claim.subject_entity_id)
                    or "?",
                    effect=claim.object_text,
                    excerpt=offering.excerpt,
                    source_name=offering.source_name,
                    source_url=offering.source_url,
                    vendor_source=(offering.source_type or "") in _VENDOR_SOURCES,
                )
            )

    opportunities = [
        MapOpportunityOut(
            id=opportunity.id,
            title=opportunity.title,
            status=opportunity.status,
            approved=opportunity.approved_by_user_id is not None,
            recommended_next_action=opportunity.recommended_next_action,
        )
        for opportunity in db.scalars(
            select(Opportunity).where(
                Opportunity.problem_id == problem.id,
                Opportunity.status != OpportunityStatus.closed,
            )
        ).all()
    ]

    return ProblemOpportunityOut(
        problem_id=problem.id,
        name=problem.name,
        description=problem.description,
        capabilities=[_technology_out(db, t) for t in capability_techs],
        vendors=vendors,
        references=references,
        effects=effects,
        opportunities=opportunities,
        evidence_count=2 * len(references) + 2 * len(effects) + len(vendors),
    )


@router.get("/opportunity-map", response_model=OpportunityMapOut)
def opportunity_map(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> OpportunityMapOut:
    technologies = {
        t.name: t for t in db.scalars(select(Technology).where(Technology.active.is_(True))).all()
    }
    problems = db.scalars(select(ProblemTaxonomy).where(ProblemTaxonomy.active.is_(True))).all()
    rows = [_problem_row(db, problem, technologies) for problem in problems]
    rows.sort(key=lambda row: (-row.evidence_count, row.name))
    return OpportunityMapOut(problems=rows)
