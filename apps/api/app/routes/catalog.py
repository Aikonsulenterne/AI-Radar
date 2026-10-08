"""Companies, technologies og adoption cases (Technical Master §11).

Profiler viser kun reviewede fakta: godkendte claims og publicerede cases.
Manglende fakta er null ("Ikke dokumenteret") — der gættes aldrig.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import AuditAction, AuditEntity, record
from app.auth import CurrentUser, get_current_user, require_role
from app.db import get_db
from app.enums import CaseStatus, EntityType, Predicate, ReviewStatus, UserRole
from app.errors import ApiError
from app.models import Document, Source
from app.models_cases import AdoptionCase, AdoptionCaseClaim
from app.models_claims import Claim, ClaimEvidence, Company, Technology
from app.pipeline.entities import entity_name, normalize_alias
from app.routes.documents import _claim_out
from app.schemas import Paginated
from app.schemas_catalog import (
    CaseCreate,
    CaseDetailOut,
    CaseFacts,
    CaseOut,
    CaseUpdate,
    CompanyDetailOut,
    CompanyOut,
    LandscapeCapabilityOut,
    LandscapeVendorOut,
    OfferingOut,
    TechnologyDetailOut,
    TechnologyOut,
    VendorLandscapeOut,
)

router = APIRouter(tags=["catalog"])

_APPROVED = {ReviewStatus.approved, ReviewStatus.approved_with_edits}
_REVIEWER = {UserRole.reviewer, UserRole.admin}


def _approved_claims_for_company(db: Session, company_id: uuid.UUID) -> list[Claim]:
    return list(
        db.scalars(
            select(Claim)
            .where(
                Claim.subject_entity_type == EntityType.company,
                Claim.subject_entity_id == company_id,
                Claim.review_status.in_(_APPROVED),
            )
            .order_by(Claim.observed_at.desc())
        ).all()
    )


def _company_out(db: Session, company: Company) -> CompanyOut:
    approved = (
        db.scalar(
            select(func.count())
            .select_from(Claim)
            .where(
                Claim.subject_entity_type == EntityType.company,
                Claim.subject_entity_id == company.id,
                Claim.review_status.in_(_APPROVED),
            )
        )
        or 0
    )
    cases = (
        db.scalar(
            select(func.count())
            .select_from(AdoptionCase)
            .where(
                AdoptionCase.company_id == company.id,
                AdoptionCase.status == CaseStatus.published,
            )
        )
        or 0
    )
    out = CompanyOut.model_validate(company)
    return out.model_copy(update={"approved_claim_count": approved, "published_case_count": cases})


def _distinct_subjects(db: Session, technology: Technology, *, offers: bool) -> int:
    predicate_filter = (
        Claim.predicate == Predicate.OFFERS_CAPABILITY
        if offers
        else Claim.predicate != Predicate.OFFERS_CAPABILITY
    )
    return (
        db.scalar(
            select(func.count(func.distinct(Claim.subject_entity_id))).where(
                Claim.object_entity_type == EntityType.technology,
                Claim.object_entity_id == technology.id,
                Claim.review_status.in_(_APPROVED),
                predicate_filter,
            )
        )
        or 0
    )


def _technology_out(db: Session, technology: Technology) -> TechnologyOut:
    out = TechnologyOut.model_validate(technology)
    return out.model_copy(
        update={
            # En leverandørs tilbud er ikke adoption og tælles for sig.
            "adopting_company_count": _distinct_subjects(db, technology, offers=False),
            "vendor_count": _distinct_subjects(db, technology, offers=True),
        }
    )


def _case_claims(db: Session, case_id: uuid.UUID) -> list[Claim]:
    claim_ids = db.scalars(
        select(AdoptionCaseClaim.claim_id).where(AdoptionCaseClaim.case_id == case_id)
    ).all()
    return [claim for cid in claim_ids if (claim := db.get(Claim, cid)) is not None]


def _object_display(db: Session, claim: Claim) -> str | None:
    name = entity_name(db, claim.object_entity_type, claim.object_entity_id)
    return name or claim.object_text


def _derive_facts(db: Session, claims: list[Claim]) -> CaseFacts:
    """Afled visningsfakta af godkendte claims; udokumenteret forbliver null."""
    facts = CaseFacts()
    for claim in claims:
        if claim.review_status not in _APPROVED:
            continue
        if claim.predicate == Predicate.USES_CAPABILITY and facts.capability is None:
            facts.capability = _object_display(db, claim)
        elif claim.predicate == Predicate.USES_FOR and facts.use_case is None:
            facts.use_case = _object_display(db, claim)
        elif claim.predicate == Predicate.ADOPTION_STAGE and facts.stage is None:
            facts.stage = claim.object_text
        elif claim.predicate == Predicate.USES_VENDOR and facts.vendor is None:
            facts.vendor = _object_display(db, claim)
        elif claim.predicate == Predicate.REPORTED_EFFECT and facts.effect is None:
            facts.effect = claim.object_text
    return facts


def _case_out(db: Session, case: AdoptionCase) -> CaseOut:
    claims = _case_claims(db, case.id)
    company = db.get(Company, case.company_id)
    out = CaseOut.model_validate(case)
    return out.model_copy(
        update={
            "company_name": company.name if company else None,
            "claim_count": len(claims),
            "facts": _derive_facts(db, claims),
        }
    )


# --- Companies ---


@router.get("/companies", response_model=Paginated[CompanyOut])
def list_companies(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    country_code: str | None = Query(default=None, pattern=r"^[A-Z]{2}$"),
    q: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> Paginated[CompanyOut]:
    stmt = select(Company).where(Company.active.is_(True)).order_by(Company.name)
    if country_code is not None:
        stmt = stmt.where(Company.country_code == country_code)
    if q:
        stmt = stmt.where(func.lower(Company.name).contains(q.casefold()))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.limit(limit).offset(offset)).all()
    return Paginated[CompanyOut](
        items=[_company_out(db, row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/companies/{company_id}", response_model=CompanyDetailOut)
def get_company(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> CompanyDetailOut:
    company = db.get(Company, company_id)
    if company is None:
        raise ApiError(404, "not_found", "Virksomheden findes ikke.")
    claims = _approved_claims_for_company(db, company.id)
    cases = db.scalars(
        select(AdoptionCase)
        .where(
            AdoptionCase.company_id == company.id,
            AdoptionCase.status == CaseStatus.published,
        )
        .order_by(AdoptionCase.updated_at.desc())
    ).all()
    base = _company_out(db, company)
    return CompanyDetailOut(
        **base.model_dump(),
        claims=[_claim_out(db, claim) for claim in claims],
        cases=[_case_out(db, case) for case in cases],
    )


# --- Technologies ---


@router.get("/technologies", response_model=Paginated[TechnologyOut])
def list_technologies(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> Paginated[TechnologyOut]:
    stmt = select(Technology).where(Technology.active.is_(True)).order_by(Technology.name)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.limit(limit).offset(offset)).all()
    return Paginated[TechnologyOut](
        items=[_technology_out(db, row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/technologies/{technology_id}", response_model=TechnologyDetailOut)
def get_technology(
    technology_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> TechnologyDetailOut:
    technology = db.get(Technology, technology_id)
    if technology is None:
        raise ApiError(404, "not_found", "Teknologien findes ikke.")
    claims = list(
        db.scalars(
            select(Claim)
            .where(
                Claim.object_entity_type == EntityType.technology,
                Claim.object_entity_id == technology.id,
                Claim.review_status.in_(_APPROVED),
            )
            .order_by(Claim.observed_at.desc())
        ).all()
    )

    def companies_for(offers: bool) -> list[CompanyOut]:
        ids = {
            claim.subject_entity_id
            for claim in claims
            if claim.subject_entity_type == EntityType.company
            and (claim.predicate == Predicate.OFFERS_CAPABILITY) == offers
        }
        found = [
            _company_out(db, company)
            for company_id in ids
            if (company := db.get(Company, company_id)) is not None
        ]
        return sorted(found, key=lambda c: c.name)

    base = _technology_out(db, technology)
    return TechnologyDetailOut(
        **base.model_dump(),
        claims=[_claim_out(db, claim) for claim in claims],
        companies=companies_for(offers=False),
        vendors=companies_for(offers=True),
    )


# --- Adoption cases ---


@router.get("/adoption-cases", response_model=Paginated[CaseOut])
def list_cases(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    company_id: uuid.UUID | None = Query(default=None),
    status: CaseStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Paginated[CaseOut]:
    stmt = select(AdoptionCase).order_by(AdoptionCase.updated_at.desc())
    if company_id is not None:
        stmt = stmt.where(AdoptionCase.company_id == company_id)
    if user.role in _REVIEWER:
        if status is not None:
            stmt = stmt.where(AdoptionCase.status == status)
    else:
        stmt = stmt.where(AdoptionCase.status == CaseStatus.published)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.limit(limit).offset(offset)).all()
    return Paginated[CaseOut](
        items=[_case_out(db, row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/adoption-cases/{case_id}", response_model=CaseDetailOut)
def get_case(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> CaseDetailOut:
    case = db.get(AdoptionCase, case_id)
    if case is None:
        raise ApiError(404, "not_found", "Casen findes ikke.")
    if case.status != CaseStatus.published and user.role not in _REVIEWER:
        raise ApiError(404, "not_found", "Casen findes ikke.")
    claims = _case_claims(db, case.id)
    technologies = sorted(
        {
            name
            for claim in claims
            if claim.object_entity_type == EntityType.technology
            and (name := entity_name(db, claim.object_entity_type, claim.object_entity_id))
        }
    )
    base = _case_out(db, case)
    return CaseDetailOut(
        **base.model_dump(),
        claims=[_claim_out(db, claim) for claim in claims],
        technologies=technologies,
    )


def _validate_case_claims(db: Session, company_id: uuid.UUID, claim_ids: list[uuid.UUID]) -> None:
    for claim_id in claim_ids:
        claim = db.get(Claim, claim_id)
        if claim is None:
            raise ApiError(422, "validation_error", f"Claim {claim_id} findes ikke.")
        if claim.subject_entity_type != EntityType.company or claim.subject_entity_id != company_id:
            raise ApiError(
                422,
                "validation_error",
                "Alle claims i en case skal handle om casens virksomhed.",
            )


def _replace_case_claims(db: Session, case: AdoptionCase, claim_ids: list[uuid.UUID]) -> None:
    for link in db.scalars(
        select(AdoptionCaseClaim).where(AdoptionCaseClaim.case_id == case.id)
    ).all():
        db.delete(link)
    db.flush()
    for claim_id in dict.fromkeys(claim_ids):
        db.add(AdoptionCaseClaim(case_id=case.id, claim_id=claim_id))
    db.flush()


@router.post("/adoption-cases", response_model=CaseOut, status_code=201)
def create_case(
    body: CaseCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reviewer)),
) -> CaseOut:
    if db.get(Company, body.company_id) is None:
        raise ApiError(422, "validation_error", "Virksomheden findes ikke.")
    _validate_case_claims(db, body.company_id, body.claim_ids)
    case = AdoptionCase(
        company_id=body.company_id,
        title=body.title,
        summary=body.summary,
        created_by_user_id=user.user_id,
    )
    db.add(case)
    db.flush()
    _replace_case_claims(db, case, body.claim_ids)
    return _case_out(db, case)


@router.patch("/adoption-cases/{case_id}", response_model=CaseOut)
def update_case(
    case_id: uuid.UUID,
    body: CaseUpdate,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reviewer)),
) -> CaseOut:
    case = db.get(AdoptionCase, case_id)
    if case is None:
        raise ApiError(404, "not_found", "Casen findes ikke.")
    updates = body.model_dump(exclude_unset=True)

    status_update = updates.pop("status", None)
    if status_update is not None:
        if status_update != CaseStatus.archived:
            raise ApiError(
                422,
                "validation_error",
                "Kun 'archived' kan sættes via PATCH; publicér via /publish.",
            )
        case.status = CaseStatus.archived

    claim_ids = updates.pop("claim_ids", None)
    if claim_ids is not None:
        if case.status == CaseStatus.published:
            raise ApiError(409, "invalid_status", "Casen er publiceret — arkivér først.")
        ids = [uuid.UUID(str(c)) for c in claim_ids]
        _validate_case_claims(db, case.company_id, ids)
        _replace_case_claims(db, case, ids)

    for field_name, value in updates.items():
        setattr(case, field_name, value)
    db.flush()
    return _case_out(db, case)


@router.post("/adoption-cases/{case_id}/publish", response_model=CaseOut)
def publish_case(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reviewer)),
) -> CaseOut:
    case = db.get(AdoptionCase, case_id)
    if case is None:
        raise ApiError(404, "not_found", "Casen findes ikke.")
    if case.status != CaseStatus.draft:
        raise ApiError(409, "invalid_status", "Kun kladder kan publiceres.")
    claims = _case_claims(db, case.id)
    if not claims:
        raise ApiError(409, "no_claims", "En case kræver mindst ét godkendt claim.")
    for claim in claims:
        if claim.review_status not in _APPROVED:
            raise ApiError(
                409,
                "unapproved_claims",
                "Kun godkendte claims må indgå i en publiceret case.",
            )
    case.status = CaseStatus.published
    db.flush()
    record(
        db,
        entity_type=AuditEntity.adoption_case,
        entity_id=case.id,
        action=AuditAction.published,
        actor_user_id=user.user_id,
        changes={"claims": len(claims)},
    )
    return _case_out(db, case)


# --- Leverandørlandskab ---

_OTHER_CAPABILITIES = "Øvrige capabilities"


def _offering_out(db: Session, claim: Claim) -> OfferingOut:
    evidence = db.scalars(
        select(ClaimEvidence).where(ClaimEvidence.claim_id == claim.id).limit(1)
    ).first()
    document = db.get(Document, evidence.document_id) if evidence else None
    source = db.get(Source, document.source_id) if document else None
    return OfferingOut(
        claim_id=claim.id,
        product=claim.object_text,
        excerpt=evidence.supporting_excerpt if evidence else None,
        document_id=document.id if document else None,
        document_title=document.title if document else None,
        source_url=document.canonical_url if document else None,
        source_name=source.name if source else None,
        source_type=str(source.source_type) if source else None,
        auto_approved=claim.auto_approved,
        observed_at=claim.observed_at,
    )


def _customers_by_vendor(
    db: Session, vendors: dict[uuid.UUID, Company]
) -> dict[uuid.UUID, set[str]]:
    """Godkendte "X USES_VENDOR/USES_TECHNOLOGY <leverandør>"-claims, matchet
    på leverandørens id eller (når objektet forblev tekst) dens navn."""
    by_name = {normalize_alias(company.name): company_id for company_id, company in vendors.items()}
    customers: dict[uuid.UUID, set[str]] = {company_id: set() for company_id in vendors}
    usage = db.scalars(
        select(Claim).where(
            Claim.predicate.in_((Predicate.USES_VENDOR, Predicate.USES_TECHNOLOGY)),
            Claim.review_status.in_(_APPROVED),
        )
    ).all()
    for claim in usage:
        vendor_id: uuid.UUID | None = None
        if claim.object_entity_type == EntityType.company and claim.object_entity_id in vendors:
            vendor_id = claim.object_entity_id
        elif claim.object_text:
            vendor_id = by_name.get(normalize_alias(claim.object_text))
        if vendor_id is None or claim.subject_entity_id == vendor_id:
            continue
        name = entity_name(db, claim.subject_entity_type, claim.subject_entity_id)
        if name:
            customers[vendor_id].add(name)
    return customers


@router.get("/vendor-landscape", response_model=VendorLandscapeOut)
def vendor_landscape(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> VendorLandscapeOut:
    """Hvem tilbyder hvilken AI-capability til kundecentre — kun godkendte
    OFFERS_CAPABILITY-claims, grupperet efter radarens kuraterede teknologier."""
    offers = db.scalars(
        select(Claim)
        .where(
            Claim.predicate == Predicate.OFFERS_CAPABILITY,
            Claim.review_status.in_(_APPROVED),
            Claim.subject_entity_type == EntityType.company,
        )
        .order_by(Claim.observed_at.desc())
    ).all()

    vendors: dict[uuid.UUID, Company] = {}
    # (teknologi-id eller None) → leverandør-id → tilbud
    grouped: dict[uuid.UUID | None, dict[uuid.UUID, list[Claim]]] = {}
    for claim in offers:
        company = vendors.get(claim.subject_entity_id) or db.get(Company, claim.subject_entity_id)
        if company is None:
            continue
        vendors[company.id] = company
        technology_id = (
            claim.object_entity_id if claim.object_entity_type == EntityType.technology else None
        )
        grouped.setdefault(technology_id, {}).setdefault(company.id, []).append(claim)

    customers = _customers_by_vendor(db, vendors)

    def vendor_rows(by_vendor: dict[uuid.UUID, list[Claim]]) -> list[LandscapeVendorOut]:
        rows = [
            LandscapeVendorOut(
                company_id=company_id,
                name=vendors[company_id].name,
                offerings=[_offering_out(db, claim) for claim in claims],
                customers=sorted(customers[company_id]),
            )
            for company_id, claims in by_vendor.items()
        ]
        return sorted(rows, key=lambda row: (-len(row.offerings), row.name.casefold()))

    horizon_order = {"now": 0, "next": 1, "horizon": 2}
    technologies = db.scalars(select(Technology).where(Technology.active.is_(True))).all()
    capabilities = [
        LandscapeCapabilityOut(
            technology=_technology_out(db, technology),
            capability_name=technology.name,
            vendors=vendor_rows(grouped.get(technology.id, {})),
        )
        for technology in sorted(
            technologies, key=lambda t: (horizon_order.get(str(t.horizon), 9), t.name)
        )
    ]
    if None in grouped:
        capabilities.append(
            LandscapeCapabilityOut(
                technology=None,
                capability_name=_OTHER_CAPABILITIES,
                vendors=vendor_rows(grouped[None]),
            )
        )
    return VendorLandscapeOut(
        capabilities=capabilities,
        vendor_count=len(vendors),
        offering_count=len(offers),
    )
