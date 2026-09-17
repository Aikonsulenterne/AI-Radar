"""Companies, technologies og adoption cases (Technical Master §11).

Profiler viser kun reviewede fakta: godkendte claims og publicerede cases.
Manglende fakta er null ("Ikke dokumenteret") — der gættes aldrig.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user, require_role
from app.db import get_db
from app.enums import CaseStatus, EntityType, Predicate, ReviewStatus, UserRole
from app.errors import ApiError
from app.models_cases import AdoptionCase, AdoptionCaseClaim
from app.models_claims import Claim, Company, Technology
from app.routes.documents import _claim_out, _entity_name
from app.schemas import Paginated
from app.schemas_catalog import (
    CaseCreate,
    CaseDetailOut,
    CaseFacts,
    CaseOut,
    CaseUpdate,
    CompanyDetailOut,
    CompanyOut,
    TechnologyDetailOut,
    TechnologyOut,
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


def _technology_out(db: Session, technology: Technology) -> TechnologyOut:
    adopting = (
        db.scalar(
            select(func.count(func.distinct(Claim.subject_entity_id))).where(
                Claim.object_entity_type == EntityType.technology,
                Claim.object_entity_id == technology.id,
                Claim.review_status.in_(_APPROVED),
            )
        )
        or 0
    )
    out = TechnologyOut.model_validate(technology)
    return out.model_copy(update={"adopting_company_count": adopting})


def _case_claims(db: Session, case_id: uuid.UUID) -> list[Claim]:
    claim_ids = db.scalars(
        select(AdoptionCaseClaim.claim_id).where(AdoptionCaseClaim.case_id == case_id)
    ).all()
    return [claim for cid in claim_ids if (claim := db.get(Claim, cid)) is not None]


def _object_display(db: Session, claim: Claim) -> str | None:
    name = _entity_name(db, claim.object_entity_type, claim.object_entity_id)
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
    company_ids = {
        claim.subject_entity_id
        for claim in claims
        if claim.subject_entity_type == EntityType.company
    }
    companies = [
        _company_out(db, company)
        for company_id in company_ids
        if (company := db.get(Company, company_id)) is not None
    ]
    base = _technology_out(db, technology)
    return TechnologyDetailOut(
        **base.model_dump(),
        claims=[_claim_out(db, claim) for claim in claims],
        companies=sorted(companies, key=lambda c: c.name),
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
            and (name := _entity_name(db, claim.object_entity_type, claim.object_entity_id))
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
    _user: CurrentUser = Depends(require_role(UserRole.reviewer)),
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
    return _case_out(db, case)
