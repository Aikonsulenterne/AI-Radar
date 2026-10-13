"""Companies, technologies og adoption cases (Technical Master §11).

Profiler viser kun reviewede fakta: godkendte claims og publicerede cases.
Manglende fakta er null ("Ikke dokumenteret") — der gættes aldrig.
"""

import uuid
from collections.abc import Iterable, Sequence
from typing import Any

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
from app.models_claims import Claim, ClaimEvidence, Company, EntityAlias, Technology
from app.pipeline.entities import (
    entity_name,
    legal_base_name,
    normalize_alias,
    preload,
    preload_entities,
)
from app.routes.documents import claims_out
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
    TechnologyUpdate,
    VendorFactOut,
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


def count_map(rows: Iterable[Any]) -> dict[uuid.UUID, int]:
    """(id, antal)-rækker fra en GROUP BY som opslag."""
    return {key: int(count) for key, count in rows if key is not None}


def _companies_out(db: Session, companies: Sequence[Company]) -> list[CompanyOut]:
    """Claim- og case-antal for mange virksomheder i to forespørgsler."""
    if not companies:
        return []
    ids = [company.id for company in companies]
    approved = count_map(
        db.execute(
            select(Claim.subject_entity_id, func.count())
            .where(
                Claim.subject_entity_type == EntityType.company,
                Claim.subject_entity_id.in_(ids),
                Claim.review_status.in_(_APPROVED),
            )
            .group_by(Claim.subject_entity_id)
        ).all()
    )
    cases = count_map(
        db.execute(
            select(AdoptionCase.company_id, func.count())
            .where(
                AdoptionCase.company_id.in_(ids),
                AdoptionCase.status == CaseStatus.published,
            )
            .group_by(AdoptionCase.company_id)
        ).all()
    )
    return [
        CompanyOut.model_validate(company).model_copy(
            update={
                "approved_claim_count": approved.get(company.id, 0),
                "published_case_count": cases.get(company.id, 0),
            }
        )
        for company in companies
    ]


def _company_out(db: Session, company: Company) -> CompanyOut:
    return _companies_out(db, [company])[0]


def _subject_counts(db: Session, ids: list[uuid.UUID], *, offers: bool) -> dict[uuid.UUID, int]:
    predicate_filter = (
        Claim.predicate == Predicate.OFFERS_CAPABILITY
        if offers
        else Claim.predicate != Predicate.OFFERS_CAPABILITY
    )
    return count_map(
        db.execute(
            select(Claim.object_entity_id, func.count(func.distinct(Claim.subject_entity_id)))
            .where(
                Claim.object_entity_type == EntityType.technology,
                Claim.object_entity_id.in_(ids),
                Claim.review_status.in_(_APPROVED),
                predicate_filter,
            )
            .group_by(Claim.object_entity_id)
        ).all()
    )


def _technologies_out(db: Session, technologies: Sequence[Technology]) -> list[TechnologyOut]:
    if not technologies:
        return []
    ids = [technology.id for technology in technologies]
    # En leverandørs tilbud er ikke adoption og tælles for sig.
    adopting = _subject_counts(db, ids, offers=False)
    vendors = _subject_counts(db, ids, offers=True)
    return [
        TechnologyOut.model_validate(technology).model_copy(
            update={
                "adopting_company_count": adopting.get(technology.id, 0),
                "vendor_count": vendors.get(technology.id, 0),
            }
        )
        for technology in technologies
    ]


def _technology_out(db: Session, technology: Technology) -> TechnologyOut:
    return _technologies_out(db, [technology])[0]


def _claims_by_case(db: Session, case_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Claim]]:
    by_case: dict[uuid.UUID, list[Claim]] = {case_id: [] for case_id in case_ids}
    if not case_ids:
        return by_case
    for case_id, claim in db.execute(
        select(AdoptionCaseClaim.case_id, Claim)
        .join(Claim, Claim.id == AdoptionCaseClaim.claim_id)
        .where(AdoptionCaseClaim.case_id.in_(case_ids))
    ).all():
        by_case[case_id].append(claim)
    return by_case


def _case_claims(db: Session, case_id: uuid.UUID) -> list[Claim]:
    return _claims_by_case(db, [case_id])[case_id]


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


def _cases_out(db: Session, cases: Sequence[AdoptionCase]) -> list[CaseOut]:
    """Cases med claims, virksomhed og afledte fakta i få forespørgsler."""
    if not cases:
        return []
    by_case = _claims_by_case(db, [case.id for case in cases])
    company_ids = {case.company_id for case in cases}
    preload(db, Company, company_ids)
    preload_entities(db, [claim for claims in by_case.values() for claim in claims])
    result: list[CaseOut] = []
    for case in cases:
        claims = by_case[case.id]
        company = db.get(Company, case.company_id)
        result.append(
            CaseOut.model_validate(case).model_copy(
                update={
                    "company_name": company.name if company else None,
                    "claim_count": len(claims),
                    "facts": _derive_facts(db, claims),
                }
            )
        )
    return result


def _case_out(db: Session, case: AdoptionCase) -> CaseOut:
    return _cases_out(db, [case])[0]


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
        items=_companies_out(db, rows),
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
        claims=claims_out(db, claims, review_details=False),
        cases=_cases_out(db, cases),
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
        items=_technologies_out(db, rows),
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

    claim_rows = claims_out(db, claims, review_details=False)

    def companies_for(offers: bool) -> list[CompanyOut]:
        ids = {
            claim.subject_entity_id
            for claim in claims
            if claim.subject_entity_type == EntityType.company
            and (claim.predicate == Predicate.OFFERS_CAPABILITY) == offers
        }
        # Virksomhederne er allerede i sessionen efter claims_out.
        found = [company for company_id in ids if (company := db.get(Company, company_id))]
        return sorted(_companies_out(db, found), key=lambda c: c.name)

    base = _technology_out(db, technology)
    return TechnologyDetailOut(
        **base.model_dump(),
        claims=claim_rows,
        companies=companies_for(offers=False),
        vendors=companies_for(offers=True),
    )


@router.patch("/technologies/{technology_id}", response_model=TechnologyOut)
def update_technology(
    technology_id: uuid.UUID,
    body: TechnologyUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> TechnologyOut:
    """Kuratering. En kandidat optages på radaren, når den får en horisont;
    så er den ikke længere kandidat. active=false afviser/skjuler den."""
    technology = db.get(Technology, technology_id)
    if technology is None:
        raise ApiError(404, "not_found", "Teknologien findes ikke.")
    if body.merge_into_id is not None:
        return _merge_technology(db, technology, body, user)
    updates = body.model_dump(exclude_unset=True, exclude={"merge_into_id"})
    if "horizon" in updates and updates["horizon"] is None:
        raise ApiError(422, "invalid_horizon", "En teknologi på radaren skal have en horisont.")
    before = {key: getattr(technology, key) for key in (*updates, "is_candidate")}
    for key, value in updates.items():
        setattr(technology, key, value)
    if updates.get("horizon") is not None:
        technology.is_candidate = False
    if "name" in updates:
        alias_name = updates["name"]
        if _alias_owner(db, alias_name) is None:
            db.add(
                EntityAlias(
                    entity_type=EntityType.technology,
                    entity_id=technology.id,
                    alias=alias_name,
                    normalized_alias=normalize_alias(alias_name),
                )
            )
    after = {key: getattr(technology, key) for key in before}
    record(
        db,
        entity_type=AuditEntity.technology,
        entity_id=technology.id,
        action=AuditAction.updated,
        actor_user_id=user.user_id,
        changes={
            key: {"before": str(before[key]), "after": str(after[key])}
            for key in before
            if before[key] != after[key]
        },
    )
    db.commit()
    db.refresh(technology)
    return _technology_out(db, technology)


def _merge_technology(
    db: Session, technology: Technology, body: TechnologyUpdate, user: CurrentUser
) -> TechnologyOut:
    """Slå en dublet sammen med en eksisterende teknologi: claims peger
    derefter på målet, og dublettens navne bliver aliaser for målet, så
    næste udtræk med samme navn lander rigtigt. Dubletten deaktiveres."""
    if body.model_dump(exclude_unset=True, exclude={"merge_into_id"}):
        raise ApiError(
            422, "invalid_merge", "Sammenlægning kan ikke kombineres med andre ændringer."
        )
    target = db.get(Technology, body.merge_into_id)
    if target is None or not target.active or target.id == technology.id:
        raise ApiError(422, "invalid_merge", "Vælg en anden, aktiv teknologi at slå sammen med.")
    claims = db.scalars(
        select(Claim).where(
            Claim.object_entity_type == EntityType.technology,
            Claim.object_entity_id == technology.id,
        )
    ).all()
    for claim in claims:
        claim.object_entity_id = target.id
    for alias in db.scalars(
        select(EntityAlias).where(
            EntityAlias.entity_type == EntityType.technology,
            EntityAlias.entity_id == technology.id,
        )
    ).all():
        alias.entity_id = target.id
    technology.active = False
    technology.is_candidate = False
    record(
        db,
        entity_type=AuditEntity.technology,
        entity_id=technology.id,
        action=AuditAction.updated,
        actor_user_id=user.user_id,
        changes={"merged_into": str(target.id), "claims_moved": len(claims)},
    )
    db.commit()
    db.refresh(target)
    return _technology_out(db, target)


def _alias_owner(db: Session, name: str) -> uuid.UUID | None:
    return db.scalar(
        select(EntityAlias.entity_id).where(
            EntityAlias.entity_type == EntityType.technology,
            EntityAlias.normalized_alias == normalize_alias(name),
        )
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
        items=_cases_out(db, rows),
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
    preload_entities(db, claims)
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
        claims=claims_out(db, claims, review_details=False),
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


_SOURCES_KEY = "offering_sources"
_EvidenceSource = tuple[ClaimEvidence | None, Document | None, Source | None]


def prefetch_offering_sources(db: Session, claims: Sequence[Claim]) -> None:
    """Første evidens, dokument og kilde for mange claims i én forespørgsel.

    Gemmes i sessionens info (én request) og bruges af _offering_out. Kun
    læse-endpoints kalder den, så data kan ikke blive forældet undervejs.
    """
    cache: dict[uuid.UUID, _EvidenceSource] = db.info.setdefault(_SOURCES_KEY, {})
    wanted = [claim.id for claim in claims if claim.id not in cache]
    if not wanted:
        return
    for claim_id in wanted:
        cache[claim_id] = (None, None, None)
    rows = db.execute(
        select(ClaimEvidence, Document, Source)
        .join(Document, Document.id == ClaimEvidence.document_id)
        .join(Source, Source.id == Document.source_id)
        .where(ClaimEvidence.claim_id.in_(wanted))
        .order_by(ClaimEvidence.claim_id, ClaimEvidence.id)
    ).all()
    for evidence, document, source in rows:
        if cache[evidence.claim_id][0] is None:
            cache[evidence.claim_id] = (evidence, document, source)


def _evidence_source(db: Session, claim: Claim) -> _EvidenceSource:
    cache: dict[uuid.UUID, _EvidenceSource] = db.info.get(_SOURCES_KEY, {})
    cached = cache.get(claim.id)
    if cached is not None:
        return cached
    evidence = db.scalars(
        select(ClaimEvidence).where(ClaimEvidence.claim_id == claim.id).limit(1)
    ).first()
    document = db.get(Document, evidence.document_id) if evidence else None
    source = db.get(Source, document.source_id) if document else None
    return evidence, document, source


def _offering_out(db: Session, claim: Claim) -> OfferingOut:
    evidence, document, source = _evidence_source(db, claim)
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


def _merged_offerings(db: Session, claims: list[Claim]) -> list[OfferingOut]:
    """Samme produkt fra samme leverandør, omtalt i flere artikler, vises som
    ét tilbud (det nyeste) med de øvrige kilder i also_reported_by."""
    merged: dict[str, OfferingOut] = {}
    for claim in claims:  # nyeste først
        offering = _offering_out(db, claim)
        key = normalize_alias(offering.product or "") or str(claim.id)
        first = merged.get(key)
        if first is None:
            merged[key] = offering
            continue
        source = offering.source_name or offering.document_title
        if source and source not in first.also_reported_by and source != first.source_name:
            first.also_reported_by.append(source)
    return list(merged.values())


_NORDIC_MARKETS = (
    "denmark",
    "danmark",
    "danish",
    "dansk",
    "nordic",
    "nordics",
    "norden",
    "nordisk",
    "scandinavia",
    "skandinavien",
)


def _vendor_facts(
    db: Session, vendor_ids: set[uuid.UUID]
) -> dict[uuid.UUID, tuple[list[VendorFactOut], list[VendorFactOut]]]:
    """Godkendte marked- og sprogclaims pr. leverandør (dubletter fjernet)."""
    facts: dict[uuid.UUID, tuple[list[VendorFactOut], list[VendorFactOut]]] = {
        vendor_id: ([], []) for vendor_id in vendor_ids
    }
    if not vendor_ids:
        return facts
    rows = db.scalars(
        select(Claim).where(
            Claim.predicate.in_((Predicate.OFFERS_IN_MARKET, Predicate.SUPPORTS_LANGUAGE)),
            Claim.review_status.in_(_APPROVED),
            Claim.subject_entity_id.in_(vendor_ids),
        )
    ).all()
    prefetch_offering_sources(db, rows)
    for claim in rows:
        if not claim.object_text:
            continue
        offering = _offering_out(db, claim)
        target = facts[claim.subject_entity_id][
            0 if claim.predicate == Predicate.OFFERS_IN_MARKET else 1
        ]
        if any(normalize_alias(f.value) == normalize_alias(claim.object_text) for f in target):
            continue
        target.append(
            VendorFactOut(
                value=claim.object_text,
                excerpt=offering.excerpt,
                source_url=offering.source_url,
            )
        )
    return facts


def _is_nordic(markets: list[VendorFactOut], languages: list[VendorFactOut]) -> bool:
    values = [normalize_alias(f.value) for f in (*markets, *languages)]
    return any(
        word in value.split() or value == word for value in values for word in _NORDIC_MARKETS
    )


def vendor_usage_claims(db: Session) -> list[Claim]:
    """Godkendte USES_VENDOR/USES_TECHNOLOGY-claims med subjekter indlæst."""
    usage = list(
        db.scalars(
            select(Claim).where(
                Claim.predicate.in_((Predicate.USES_VENDOR, Predicate.USES_TECHNOLOGY)),
                Claim.review_status.in_(_APPROVED),
            )
        ).all()
    )
    preload_entities(db, usage)
    return usage


def _customers_by_vendor(
    db: Session,
    vendors: dict[uuid.UUID, Company],
    usage: Sequence[Claim] | None = None,
) -> dict[uuid.UUID, set[str]]:
    """Godkendte "X USES_VENDOR/USES_TECHNOLOGY <leverandør>"-claims, matchet
    på leverandørens id eller (når objektet forblev tekst) dens navn."""
    by_name = {legal_base_name(company.name): company_id for company_id, company in vendors.items()}
    customers: dict[uuid.UUID, set[str]] = {company_id: set() for company_id in vendors}
    if usage is None:
        usage = vendor_usage_claims(db)
    for claim in usage:
        vendor_id: uuid.UUID | None = None
        if claim.object_entity_type == EntityType.company and claim.object_entity_id in vendors:
            vendor_id = claim.object_entity_id
        elif claim.object_text:
            vendor_id = by_name.get(legal_base_name(claim.object_text))
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

    preload_entities(db, offers)
    prefetch_offering_sources(db, offers)
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
    vendor_facts = _vendor_facts(db, set(vendors))

    def vendor_rows(by_vendor: dict[uuid.UUID, list[Claim]]) -> list[LandscapeVendorOut]:
        rows = [
            LandscapeVendorOut(
                company_id=company_id,
                name=vendors[company_id].name,
                offerings=_merged_offerings(db, claims),
                customers=sorted(customers[company_id]),
                markets=vendor_facts[company_id][0],
                languages=vendor_facts[company_id][1],
                nordic_documented=_is_nordic(*vendor_facts[company_id]),
            )
            for company_id, claims in by_vendor.items()
        ]
        return sorted(rows, key=lambda row: (-len(row.offerings), row.name.casefold()))

    horizon_order = {"now": 0, "next": 1, "horizon": 2}
    technologies = sorted(
        db.scalars(select(Technology).where(Technology.active.is_(True))).all(),
        key=lambda t: (
            horizon_order.get(str(t.horizon), 9) if t.horizon is not None else 9,
            t.name,
        ),
    )
    capabilities = [
        LandscapeCapabilityOut(
            technology=technology_out,
            capability_name=technology.name,
            vendors=vendor_rows(grouped.get(technology.id, {})),
        )
        for technology, technology_out in zip(
            technologies, _technologies_out(db, technologies), strict=True
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
