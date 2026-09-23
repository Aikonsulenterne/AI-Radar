"""Læsning af audit-loggen (Technical Master §18).

Kun Admin: sporet viser, hvem der har truffet hvilke beslutninger, og hører
derfor ikke til i den almindelige brugerflade. Produktets aktivitetsfeed er
bevidst uden for MVP (Product Master §13).
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import AuditEntity
from app.auth import CurrentUser, require_role
from app.db import get_db
from app.enums import UserRole
from app.models_audit import AuditEvent
from app.schemas import Paginated
from app.schemas_audit import AuditEventOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=Paginated[AuditEventOut])
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    entity_type: AuditEntity | None = Query(default=None),
    entity_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> Paginated[AuditEventOut]:
    stmt = select(AuditEvent).order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
    if entity_type is not None:
        stmt = stmt.where(AuditEvent.entity_type == entity_type.value)
    if entity_id is not None:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.limit(limit).offset(offset)).all()
    return Paginated[AuditEventOut](
        items=[AuditEventOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
