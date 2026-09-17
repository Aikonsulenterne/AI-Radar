"""Schemas for signaler og dashboard (Slice 3)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import DocumentationLevel, SignalStatus, TechHorizon
from app.schemas_claims import ClaimOut


class SignalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=4000)
    analysis: str | None = None
    recommendation: str | None = None
    documentation_level: DocumentationLevel
    claim_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)


class SignalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    summary: str | None = Field(default=None, min_length=1, max_length=4000)
    analysis: str | None = None
    recommendation: str | None = None
    documentation_level: DocumentationLevel | None = None
    claim_ids: list[uuid.UUID] | None = Field(default=None, max_length=100)
    status: SignalStatus | None = Field(
        default=None,
        description="Kun archived kan sættes her; publicering sker via /publish.",
    )


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    summary: str
    analysis: str | None
    recommendation: str | None
    documentation_level: DocumentationLevel
    status: SignalStatus
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    claim_count: int = 0


class RelatedEntityOut(BaseModel):
    id: uuid.UUID
    name: str


class SignalDetailOut(SignalOut):
    """Signal med fuld provenance: fakta (claims + evidens) adskilt fra
    analyse og anbefaling (Product Master §2)."""

    claims: list[ClaimOut] = Field(default_factory=list)
    companies: list[RelatedEntityOut] = Field(default_factory=list)
    technologies: list[RelatedEntityOut] = Field(default_factory=list)


class HorizonCounts(BaseModel):
    now: int = 0
    next: int = 0
    horizon: int = 0


class DashboardOut(BaseModel):
    """Kompakte KPI'er med definition (Product Master §7). Hvert tal er en
    optælling i databasen — ingen beregnede scores."""

    published_signals: int
    approved_claims: int
    companies_with_claims: int
    documents_in_review: int
    technologies_by_horizon: HorizonCounts
    latest_signals: list[SignalOut] = Field(default_factory=list)


def horizon_counts(counts: dict[TechHorizon, int]) -> HorizonCounts:
    return HorizonCounts(
        now=counts.get(TechHorizon.now, 0),
        next=counts.get(TechHorizon.next, 0),
        horizon=counts.get(TechHorizon.horizon, 0),
    )
