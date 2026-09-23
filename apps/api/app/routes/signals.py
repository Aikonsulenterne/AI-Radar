"""Signal-endpoints og dashboard (Technical Master §11; Product Master §7).

Readers ser kun publicerede signaler. Kun godkendte claims må være faktuelt
grundlag for et publiceret signal — håndhævet ved publicering. Publicering
er en menneskelig handling (Reviewer/Admin).
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import AuditAction, AuditEntity, record
from app.auth import CurrentUser, get_current_user, require_role
from app.db import get_db
from app.enums import (
    EntityType,
    ProcessingStatus,
    ReviewStatus,
    SignalStatus,
    TechHorizon,
    UserRole,
)
from app.errors import ApiError
from app.models import Document
from app.models_claims import Claim, Company, Technology
from app.models_signals import Signal, SignalClaim
from app.routes.documents import _claim_out
from app.schemas import Paginated
from app.schemas_signals import (
    DashboardOut,
    RelatedEntityOut,
    SignalCreate,
    SignalDetailOut,
    SignalOut,
    SignalUpdate,
    horizon_counts,
)

router = APIRouter(tags=["signals"])

_APPROVED = {ReviewStatus.approved, ReviewStatus.approved_with_edits}
_REVIEWER = {UserRole.reviewer, UserRole.admin}


def _claim_count(db: Session, signal_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(SignalClaim).where(SignalClaim.signal_id == signal_id)
        )
        or 0
    )


def _signal_out(db: Session, signal: Signal) -> SignalOut:
    out = SignalOut.model_validate(signal)
    return out.model_copy(update={"claim_count": _claim_count(db, signal.id)})


def _get_signal_or_404(db: Session, signal_id: uuid.UUID) -> Signal:
    signal = db.get(Signal, signal_id)
    if signal is None:
        raise ApiError(404, "not_found", "Signalet findes ikke.")
    return signal


def _validate_claim_ids(db: Session, claim_ids: list[uuid.UUID]) -> None:
    for claim_id in claim_ids:
        if db.get(Claim, claim_id) is None:
            raise ApiError(422, "validation_error", f"Claim {claim_id} findes ikke.")


def _replace_signal_claims(db: Session, signal: Signal, claim_ids: list[uuid.UUID]) -> None:
    for link in db.scalars(select(SignalClaim).where(SignalClaim.signal_id == signal.id)).all():
        db.delete(link)
    db.flush()
    for claim_id in dict.fromkeys(claim_ids):
        db.add(SignalClaim(signal_id=signal.id, claim_id=claim_id))
    db.flush()


@router.get("/signals", response_model=Paginated[SignalOut])
def list_signals(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: SignalStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Paginated[SignalOut]:
    stmt = select(Signal).order_by(
        Signal.published_at.desc().nulls_last(), Signal.created_at.desc()
    )
    if user.role in _REVIEWER:
        if status is not None:
            stmt = stmt.where(Signal.status == status)
    else:
        # Readers ser kun publiceret intelligence.
        stmt = stmt.where(Signal.status == SignalStatus.published)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.limit(limit).offset(offset)).all()
    return Paginated[SignalOut](
        items=[_signal_out(db, row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/signals/{signal_id}", response_model=SignalDetailOut)
def get_signal(
    signal_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> SignalDetailOut:
    signal = _get_signal_or_404(db, signal_id)
    if signal.status != SignalStatus.published and user.role not in _REVIEWER:
        raise ApiError(404, "not_found", "Signalet findes ikke.")

    claim_ids = db.scalars(
        select(SignalClaim.claim_id).where(SignalClaim.signal_id == signal.id)
    ).all()
    claims = [
        _claim_out(db, claim)
        for claim_id in claim_ids
        if (claim := db.get(Claim, claim_id)) is not None
    ]

    companies: dict[uuid.UUID, str] = {}
    technologies: dict[uuid.UUID, str] = {}
    for claim_id in claim_ids:
        claim = db.get(Claim, claim_id)
        if claim is None:
            continue
        if claim.subject_entity_type == EntityType.company:
            company = db.get(Company, claim.subject_entity_id)
            if company is not None:
                companies[company.id] = company.name
        if claim.object_entity_type == EntityType.technology and claim.object_entity_id:
            technology = db.get(Technology, claim.object_entity_id)
            if technology is not None:
                technologies[technology.id] = technology.name

    base = _signal_out(db, signal)
    return SignalDetailOut(
        **base.model_dump(),
        claims=claims,
        companies=[RelatedEntityOut(id=i, name=n) for i, n in companies.items()],
        technologies=[RelatedEntityOut(id=i, name=n) for i, n in technologies.items()],
    )


@router.post("/signals", response_model=SignalOut, status_code=201)
def create_signal(
    body: SignalCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reviewer)),
) -> SignalOut:
    _validate_claim_ids(db, body.claim_ids)
    signal = Signal(
        title=body.title,
        summary=body.summary,
        analysis=body.analysis,
        recommendation=body.recommendation,
        documentation_level=body.documentation_level,
        created_by_user_id=user.user_id,
    )
    db.add(signal)
    db.flush()
    _replace_signal_claims(db, signal, body.claim_ids)
    return _signal_out(db, signal)


@router.patch("/signals/{signal_id}", response_model=SignalOut)
def update_signal(
    signal_id: uuid.UUID,
    body: SignalUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reviewer)),
) -> SignalOut:
    signal = _get_signal_or_404(db, signal_id)
    updates = body.model_dump(exclude_unset=True)

    status_update = updates.pop("status", None)
    if status_update is not None:
        if status_update != SignalStatus.archived:
            raise ApiError(
                422,
                "validation_error",
                "Kun 'archived' kan sættes via PATCH; publicér via /publish.",
            )
        signal.status = SignalStatus.archived
        record(
            db,
            entity_type=AuditEntity.signal,
            entity_id=signal.id,
            action=AuditAction.archived,
            actor_user_id=user.user_id,
        )

    claim_ids = updates.pop("claim_ids", None)
    if claim_ids is not None:
        if signal.status == SignalStatus.published:
            raise ApiError(
                409, "invalid_status", "Ret claims via ny version — signalet er publiceret."
            )
        ids = [uuid.UUID(str(c)) for c in claim_ids]
        _validate_claim_ids(db, ids)
        _replace_signal_claims(db, signal, ids)

    for field_name, value in updates.items():
        setattr(signal, field_name, value)
    db.flush()
    return _signal_out(db, signal)


@router.post("/signals/{signal_id}/publish", response_model=SignalOut)
def publish_signal(
    signal_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.reviewer)),
) -> SignalOut:
    signal = _get_signal_or_404(db, signal_id)
    if signal.status != SignalStatus.draft:
        raise ApiError(409, "invalid_status", "Kun kladder kan publiceres.")

    claim_ids = db.scalars(
        select(SignalClaim.claim_id).where(SignalClaim.signal_id == signal.id)
    ).all()
    if not claim_ids:
        raise ApiError(409, "no_claims", "Et signal kræver mindst ét godkendt claim.")
    for claim_id in claim_ids:
        claim = db.get(Claim, claim_id)
        if claim is None or claim.review_status not in _APPROVED:
            raise ApiError(
                409,
                "unapproved_claims",
                "Kun godkendte claims må være faktuelt grundlag for et publiceret signal.",
            )

    signal.status = SignalStatus.published
    signal.published_at = datetime.now(UTC)
    db.flush()
    record(
        db,
        entity_type=AuditEntity.signal,
        entity_id=signal.id,
        action=AuditAction.published,
        actor_user_id=user.user_id,
        changes={"claims": len(claim_ids)},
    )
    return _signal_out(db, signal)


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> DashboardOut:
    published = (
        db.scalar(
            select(func.count()).select_from(Signal).where(Signal.status == SignalStatus.published)
        )
        or 0
    )
    approved_claims = (
        db.scalar(select(func.count()).select_from(Claim).where(Claim.review_status.in_(_APPROVED)))
        or 0
    )
    companies_with_claims = (
        db.scalar(
            select(func.count(func.distinct(Claim.subject_entity_id))).where(
                Claim.subject_entity_type == EntityType.company,
                Claim.review_status.in_(_APPROVED),
            )
        )
        or 0
    )
    documents_in_review = (
        db.scalar(
            select(func.count())
            .select_from(Document)
            .where(
                Document.processing_status.in_(
                    {ProcessingStatus.review_pending, ProcessingStatus.partially_reviewed}
                )
            )
        )
        or 0
    )

    counts: dict[TechHorizon, int] = {}
    for horizon, count in db.execute(
        select(Technology.horizon, func.count())
        .where(Technology.active.is_(True))
        .group_by(Technology.horizon)
    ).all():
        counts[horizon] = count

    latest = db.scalars(
        select(Signal)
        .where(Signal.status == SignalStatus.published)
        .order_by(Signal.published_at.desc())
        .limit(5)
    ).all()

    return DashboardOut(
        published_signals=published,
        approved_claims=approved_claims,
        companies_with_claims=companies_with_claims,
        documents_in_review=documents_in_review,
        technologies_by_horizon=horizon_counts(counts),
        latest_signals=[_signal_out(db, s) for s in latest],
    )
