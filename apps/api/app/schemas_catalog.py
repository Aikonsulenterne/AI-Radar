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
    # None = kandidat fundet i markedet, endnu ikke placeret i en horisont.
    horizon: TechHorizon | None
    active: bool
    is_candidate: bool = False
    discovered_at: datetime | None = None
    # Antal virksomheder med godkendte claims, der refererer teknologien.
    adopting_company_count: int = 0
    # Antal leverandører med et godkendt tilbud (OFFERS_CAPABILITY).
    vendor_count: int = 0


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
    # Publiceret af AI uden menneskelig kontrol (AUTO_PUBLISH).
    auto_published: bool = False
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
    vendors: list[CompanyOut] = Field(default_factory=list)


class TechnologyUpdate(BaseModel):
    """Admin kuraterer en teknologi: optag en kandidat på radaren (horisont
    og definition), omdøb den, eller afvis den (active=false)."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    definition: str | None = Field(default=None, min_length=1, max_length=1000)
    horizon: TechHorizon | None = None
    active: bool | None = None


class OfferingOut(BaseModel):
    """Ét godkendt tilbud: leverandøren tilbyder en capability (produkt)."""

    claim_id: uuid.UUID
    product: str | None
    excerpt: str | None
    document_id: uuid.UUID | None
    document_title: str | None
    source_url: str | None
    source_name: str | None
    source_type: str | None
    auto_approved: bool
    observed_at: datetime | None


class LandscapeVendorOut(BaseModel):
    company_id: uuid.UUID
    name: str
    offerings: list[OfferingOut]
    # Organisationer med godkendt claim om, at de bruger leverandøren.
    customers: list[str]


class LandscapeCapabilityOut(BaseModel):
    """En kurateret teknologi — eller technology=None for tilbud, hvis
    capability ikke findes på den kuraterede liste."""

    technology: TechnologyOut | None
    capability_name: str
    vendors: list[LandscapeVendorOut]


class VendorLandscapeOut(BaseModel):
    capabilities: list[LandscapeCapabilityOut]
    vendor_count: int
    offering_count: int


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
