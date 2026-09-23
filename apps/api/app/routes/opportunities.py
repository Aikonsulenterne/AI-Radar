"""Opportunity-endpoints (Technical Master §11; Product Master §10).

Opportunities kvalificerer muligheder — produktet erstatter ikke business
case- eller projektstyring. En opportunity uden godkendelse er en kandidat;
menneskelig godkendelse kræves, før status kan rykkes forbi 'identified'.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.provider import AIProvider
from app.audit import AuditAction, AuditEntity, field_changes, record
from app.auth import CurrentUser, require_role
from app.db import get_db
from app.enums import OpportunityStatus, SignalStatus, UserRole
from app.errors import ApiError
from app.models_claims import Claim
from app.models_opportunities import (
    Opportunity,
    OpportunityClaim,
    OpportunitySignal,
    ProblemTaxonomy,
)
from app.models_signals import Signal
from app.pipeline.opportunities import propose_opportunity
from app.routes.documents import _claim_out, ai_provider_dep
from app.schemas import Paginated
from app.schemas_opportunities import (
    OpportunityCreate,
    OpportunityDetailOut,
    OpportunityOut,
    OpportunityProposeRequest,
    OpportunitySignalRef,
    OpportunityUpdate,
    ProblemOut,
)

router = APIRouter(tags=["opportunities"])


def _opportunity_out(db: Session, opportunity: Opportunity) -> OpportunityOut:
    problem = db.get(ProblemTaxonomy, opportunity.problem_id)
    signal_count = (
        db.scalar(
            select(func.count())
            .select_from(OpportunitySignal)
            .where(OpportunitySignal.opportunity_id == opportunity.id)
        )
        or 0
    )
    claim_count = (
        db.scalar(
            select(func.count())
            .select_from(OpportunityClaim)
            .where(OpportunityClaim.opportunity_id == opportunity.id)
        )
        or 0
    )
    out = OpportunityOut.model_validate(opportunity)
    return out.model_copy(
        update={
            "problem_name": problem.name if problem else None,
            "approved": opportunity.approved_by_user_id is not None,
            "signal_count": signal_count,
            "claim_count": claim_count,
        }
    )


def _get_opportunity_or_404(db: Session, opportunity_id: uuid.UUID) -> Opportunity:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise ApiError(404, "not_found", "Opportunity'en findes ikke.")
    return opportunity


def _validate_links(db: Session, signal_ids: list[uuid.UUID], claim_ids: list[uuid.UUID]) -> None:
    for signal_id in signal_ids:
        if db.get(Signal, signal_id) is None:
            raise ApiError(422, "validation_error", f"Signal {signal_id} findes ikke.")
    for claim_id in claim_ids:
        if db.get(Claim, claim_id) is None:
            raise ApiError(422, "validation_error", f"Claim {claim_id} findes ikke.")


def _replace_links(
    db: Session,
    opportunity: Opportunity,
    signal_ids: list[uuid.UUID] | None,
    claim_ids: list[uuid.UUID] | None,
) -> None:
    if signal_ids is not None:
        for link in db.scalars(
            select(OpportunitySignal).where(OpportunitySignal.opportunity_id == opportunity.id)
        ).all():
            db.delete(link)
        db.flush()
        for signal_id in dict.fromkeys(signal_ids):
            db.add(OpportunitySignal(opportunity_id=opportunity.id, signal_id=signal_id))
    if claim_ids is not None:
        for claim_link in db.scalars(
            select(OpportunityClaim).where(OpportunityClaim.opportunity_id == opportunity.id)
        ).all():
            db.delete(claim_link)
        db.flush()
        for claim_id in dict.fromkeys(claim_ids):
            db.add(OpportunityClaim(opportunity_id=opportunity.id, claim_id=claim_id))
    db.flush()


@router.get("/problems", response_model=Paginated[ProblemOut])
def list_problems(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> Paginated[ProblemOut]:
    rows = db.scalars(
        select(ProblemTaxonomy)
        .where(ProblemTaxonomy.active.is_(True))
        .order_by(ProblemTaxonomy.name)
    ).all()
    return Paginated[ProblemOut](
        items=[ProblemOut.model_validate(row) for row in rows],
        total=len(rows),
        limit=len(rows) or 1,
        offset=0,
    )


@router.get("/opportunities", response_model=Paginated[OpportunityOut])
def list_opportunities(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: OpportunityStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> Paginated[OpportunityOut]:
    stmt = select(Opportunity).order_by(Opportunity.updated_at.desc())
    if status is not None:
        stmt = stmt.where(Opportunity.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.limit(limit).offset(offset)).all()
    return Paginated[OpportunityOut](
        items=[_opportunity_out(db, row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityDetailOut)
def get_opportunity(
    opportunity_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> OpportunityDetailOut:
    opportunity = _get_opportunity_or_404(db, opportunity_id)

    signal_ids = db.scalars(
        select(OpportunitySignal.signal_id).where(
            OpportunitySignal.opportunity_id == opportunity.id
        )
    ).all()
    signals = [
        OpportunitySignalRef(id=signal.id, title=signal.title, status=signal.status)
        for signal_id in signal_ids
        if (signal := db.get(Signal, signal_id)) is not None
    ]
    claim_ids = db.scalars(
        select(OpportunityClaim.claim_id).where(OpportunityClaim.opportunity_id == opportunity.id)
    ).all()
    claims = [
        _claim_out(db, claim)
        for claim_id in claim_ids
        if (claim := db.get(Claim, claim_id)) is not None
    ]

    base = _opportunity_out(db, opportunity)
    return OpportunityDetailOut(**base.model_dump(), signals=signals, claims=claims)


@router.post("/opportunities", response_model=OpportunityOut, status_code=201)
def create_opportunity(
    body: OpportunityCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reviewer)),
) -> OpportunityOut:
    problem = db.get(ProblemTaxonomy, body.problem_id)
    if problem is None or not problem.active:
        raise ApiError(422, "validation_error", "Problemet findes ikke i taxonomien.")
    _validate_links(db, body.signal_ids, body.claim_ids)

    opportunity = Opportunity(
        title=body.title,
        problem_id=body.problem_id,
        relevance_hypothesis=body.relevance_hypothesis,
        evidence_gaps=body.evidence_gaps,
        recommended_next_action=body.recommended_next_action,
        created_by_user_id=user.user_id,
    )
    db.add(opportunity)
    db.flush()
    _replace_links(db, opportunity, body.signal_ids, body.claim_ids)
    record(
        db,
        entity_type=AuditEntity.opportunity,
        entity_id=opportunity.id,
        action=AuditAction.created,
        actor_user_id=user.user_id,
        changes={"title": opportunity.title, "problem": problem.name},
    )
    return _opportunity_out(db, opportunity)


@router.post("/opportunities/propose", response_model=OpportunityOut, status_code=201)
def propose_opportunity_endpoint(
    body: OpportunityProposeRequest,
    db: Session = Depends(get_db),
    provider: AIProvider = Depends(ai_provider_dep),
    user: CurrentUser = Depends(require_role(UserRole.reviewer)),
) -> OpportunityOut:
    """AI foreslår en kandidat ud fra et publiceret signals godkendte claims.

    Forslaget oprettes ugodkendt: created_by_user_id er tom, fordi intet
    menneske har skrevet det, og status kan først rykkes efter godkendelse.
    """
    signal = db.get(Signal, body.signal_id)
    if signal is None:
        raise ApiError(404, "not_found", "Signalet findes ikke.")
    if signal.status != SignalStatus.published:
        raise ApiError(
            409,
            "invalid_status",
            "Kun publicerede signaler kan danne grundlag for et forslag.",
        )

    opportunity = propose_opportunity(db, provider, signal)
    record(
        db,
        entity_type=AuditEntity.opportunity,
        entity_id=opportunity.id,
        action=AuditAction.ai_proposed,
        actor_user_id=user.user_id,
        changes={
            "signal_id": signal.id,
            "promptversion": opportunity.proposal_prompt_version,
        },
    )
    return _opportunity_out(db, opportunity)


@router.patch("/opportunities/{opportunity_id}", response_model=OpportunityOut)
def update_opportunity(
    opportunity_id: uuid.UUID,
    body: OpportunityUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reviewer)),
) -> OpportunityOut:
    opportunity = _get_opportunity_or_404(db, opportunity_id)
    updates = body.model_dump(exclude_unset=True)
    audited = {
        field: value for field, value in updates.items() if field not in ("signal_ids", "claim_ids")
    }
    before = {field: getattr(opportunity, field) for field in audited}

    status_update = updates.pop("status", None)
    if status_update is not None:
        if (
            status_update != OpportunityStatus.identified
            and opportunity.approved_by_user_id is None
        ):
            raise ApiError(
                409,
                "not_approved",
                "Opportunity'en skal godkendes af et menneske, før status kan rykkes.",
            )
        opportunity.status = status_update

    problem_id = updates.pop("problem_id", None)
    if problem_id is not None:
        problem = db.get(ProblemTaxonomy, problem_id)
        if problem is None or not problem.active:
            raise ApiError(422, "validation_error", "Problemet findes ikke i taxonomien.")
        opportunity.problem_id = problem_id

    signal_ids = updates.pop("signal_ids", None)
    claim_ids = updates.pop("claim_ids", None)
    if signal_ids is not None or claim_ids is not None:
        parsed_signals = [uuid.UUID(str(s)) for s in signal_ids] if signal_ids is not None else None
        parsed_claims = [uuid.UUID(str(c)) for c in claim_ids] if claim_ids is not None else None
        _validate_links(db, parsed_signals or [], parsed_claims or [])
        _replace_links(db, opportunity, parsed_signals, parsed_claims)

    for field_name, value in updates.items():
        setattr(opportunity, field_name, value)
    db.flush()
    changed = field_changes(before, audited)
    if changed:
        record(
            db,
            entity_type=AuditEntity.opportunity,
            entity_id=opportunity.id,
            action=AuditAction.updated,
            actor_user_id=user.user_id,
            changes=changed,
        )
    return _opportunity_out(db, opportunity)


@router.post("/opportunities/{opportunity_id}/approve", response_model=OpportunityOut)
def approve_opportunity(
    opportunity_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reviewer)),
) -> OpportunityOut:
    """Menneskelig godkendelse af en opportunity-kandidat."""
    opportunity = _get_opportunity_or_404(db, opportunity_id)
    if opportunity.approved_by_user_id is not None:
        raise ApiError(409, "invalid_status", "Opportunity'en er allerede godkendt.")
    opportunity.approved_by_user_id = user.user_id
    db.flush()
    record(
        db,
        entity_type=AuditEntity.opportunity,
        entity_id=opportunity.id,
        action=AuditAction.approved,
        actor_user_id=user.user_id,
        changes={"foreslået_af_ai": opportunity.proposed_by_ai},
    )
    return _opportunity_out(db, opportunity)
