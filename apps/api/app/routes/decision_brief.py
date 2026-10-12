"""Beslutningsoplæg til OK Kundeservice: OK's egne tal, interne fund og
ønsket, kombineret med radarens dokumentation (siden /beslutningsoplaeg).

Tallene er menneskeindtastede og vises som det; regneeksemplet bruger kun
de indtastede tal og de indtastede scenarieprocenter — AI udfylder intet.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import AuditAction, AuditEntity, record
from app.auth import CurrentUser, require_role
from app.db import get_db
from app.enums import UserRole
from app.models_settings import AppSetting

router = APIRouter(prefix="/decision-brief", tags=["decision-brief"])

_KEY = "decision_brief"
# Audit-loggen kræver et id; indstillingen får et fast, afledt id.
_AUDIT_ID = uuid.uuid5(uuid.NAMESPACE_URL, "ai-radar:setting:decision_brief")


class ContactVolumes(BaseModel):
    """Henvendelser pr. år pr. kanal."""

    phone: int | None = Field(default=None, ge=0)
    mail: int | None = Field(default=None, ge=0)
    chat: int | None = Field(default=None, ge=0)


class Finding(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    figure: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class PeerCall(BaseModel):
    organization: str = Field(min_length=1, max_length=200)
    status: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=1000)


class DecisionBrief(BaseModel):
    title: str = Field(default="90 dage til første AI-gevinst i OK Kundeservice", max_length=200)
    contact_center_system: str | None = Field(default=None, max_length=200)
    contract_renewal: str | None = Field(default=None, max_length=100)
    budget_deadline: str | None = Field(default=None, max_length=100)
    fte: float | None = Field(default=None, ge=0)
    cost_per_fte: float | None = Field(default=None, ge=0, description="Kr. pr. årsværk")
    contacts_per_year: ContactVolumes = Field(default_factory=ContactVolumes)
    aht_minutes: float | None = Field(default=None, ge=0)
    scenario_low_pct: float | None = Field(default=None, ge=0, le=100)
    scenario_high_pct: float | None = Field(default=None, ge=0, le=100)
    internal_findings: list[Finding] = Field(default_factory=list, max_length=10)
    ask: str | None = Field(default=None, max_length=2000)
    kill_criterion: str | None = Field(default=None, max_length=1000)
    data_promise: str | None = Field(default=None, max_length=1000)
    peer_calls: list[PeerCall] = Field(default_factory=list, max_length=10)


class Calculation(BaseModel):
    """Regneeksempel ud fra de indtastede tal. None = mangler input."""

    total_contacts: int | None = None
    annual_cost: float | None = None
    cost_per_contact: float | None = None
    handling_hours: float | None = None
    saving_low: float | None = None
    saving_high: float | None = None
    missing: list[str] = Field(default_factory=list)


class DecisionBriefOut(BaseModel):
    brief: DecisionBrief
    calculation: Calculation
    updated_at: datetime | None = None


def calculate(brief: DecisionBrief) -> Calculation:
    volumes = brief.contacts_per_year
    channels = [v for v in (volumes.phone, volumes.mail, volumes.chat) if v is not None]
    total = sum(channels) if channels else None
    annual = (
        brief.fte * brief.cost_per_fte
        if brief.fte is not None and brief.cost_per_fte is not None
        else None
    )
    missing = [
        label
        for label, value in (
            ("årsværk", brief.fte),
            ("pris pr. årsværk", brief.cost_per_fte),
            ("henvendelser pr. år", total),
            ("behandlingstid (AHT)", brief.aht_minutes),
            ("scenarie lav %", brief.scenario_low_pct),
            ("scenarie høj %", brief.scenario_high_pct),
        )
        if value is None
    ]
    return Calculation(
        total_contacts=total,
        annual_cost=annual,
        cost_per_contact=(annual / total) if annual is not None and total else None,
        handling_hours=(total * brief.aht_minutes / 60)
        if total is not None and brief.aht_minutes is not None
        else None,
        saving_low=(annual * brief.scenario_low_pct / 100)
        if annual is not None and brief.scenario_low_pct is not None
        else None,
        saving_high=(annual * brief.scenario_high_pct / 100)
        if annual is not None and brief.scenario_high_pct is not None
        else None,
        missing=missing,
    )


def _load(db: Session) -> tuple[DecisionBrief, datetime | None]:
    row = db.get(AppSetting, _KEY)
    if row is None:
        return DecisionBrief(), None
    return DecisionBrief.model_validate(row.value), row.updated_at


@router.get("", response_model=DecisionBriefOut)
def get_decision_brief(
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_role(UserRole.reader)),
) -> DecisionBriefOut:
    brief, updated_at = _load(db)
    return DecisionBriefOut(brief=brief, calculation=calculate(brief), updated_at=updated_at)


@router.put("", response_model=DecisionBriefOut)
def put_decision_brief(
    body: DecisionBrief,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role(UserRole.admin)),
) -> DecisionBriefOut:
    row = db.get(AppSetting, _KEY)
    value = body.model_dump(mode="json")
    if row is None:
        row = AppSetting(key=_KEY, value=value, updated_by_user_id=user.user_id)
        db.add(row)
    else:
        row.value = value
        row.updated_by_user_id = user.user_id
        row.updated_at = datetime.now(UTC)
    record(
        db,
        entity_type=AuditEntity.setting,
        entity_id=_AUDIT_ID,
        action=AuditAction.updated,
        actor_user_id=user.user_id,
        changes={"key": _KEY},
    )
    db.commit()
    return DecisionBriefOut(brief=body, calculation=calculate(body), updated_at=row.updated_at)
