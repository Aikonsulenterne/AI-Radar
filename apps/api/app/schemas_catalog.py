"""Schemas for companies, technologies og adoption cases (Slice 4).

Manglende fakta er null og vises i UI som "Ikke dokumenteret" — der
gættes aldrig (Product Master §9).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import CaseStatus, TechHorizon
from app.schemas_claims import ClaimOut


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    country_code: str | None
    industry: str | None
    website_url: str | None
    active: bool
    approved_claim_count: int = 0
    published_case_count: int = 0


class TechnologyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    definition: str
    horizon: TechHorizon
    active: bool
    # Antal virksomheder med godkendte claims, der refererer teknologien.
    adopting_company_count: int = 0


class CaseFacts(BaseModel):
    """Faktafelter afledt af casens godkendte claims. null = ikke
    dokumenteret; effekt uden claim = "Ingen dokumenteret effekt fundet"."""

    capability: str | None = None
    use_case: str | None = None
    stage: str | None = None
    vendor: str | None = None
    effect: str | None = None


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str | None = None
    title: str
    summary: str | None
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    claim_count: int = 0
    facts: CaseFacts = Field(default_factory=CaseFacts)


class CaseDetailOut(CaseOut):
    claims: list[ClaimOut] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class CompanyDetailOut(CompanyOut):
    claims: list[ClaimOut] = Field(default_factory=list)
    cases: list[CaseOut] = Field(default_factory=list)


class TechnologyDetailOut(TechnologyOut):
    claims: list[ClaimOut] = Field(default_factory=list)
    companies: list[CompanyOut] = Field(default_factory=list)


class CaseCreate(BaseModel):
    company_id: uuid.UUID
    title: str = Field(min_length=1, max_length=300)
    summary: str | None = Field(default=None, max_length=4000)
    claim_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    summary: str | None = Field(default=None, max_length=4000)
    claim_ids: list[uuid.UUID] | None = Field(default=None, max_length=100)
    status: CaseStatus | None = Field(
        default=None, description="Kun archived kan sættes her; publicér via /publish."
    )
