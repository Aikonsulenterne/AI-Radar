"""Schemas for problem-taxonomi og opportunities (Slice 5)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import OpportunityStatus, SignalStatus
from app.schemas_claims import ClaimOut


class ProblemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    area: str
    active: bool


class OpportunitySignalRef(BaseModel):
    id: uuid.UUID
    title: str
    status: SignalStatus


class OpportunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    problem_id: uuid.UUID
    problem_name: str | None = None
    relevance_hypothesis: str
    evidence_gaps: str | None
    recommended_next_action: str
    status: OpportunityStatus
    owner_user_id: uuid.UUID | None
    # Menneskelig godkendelse: null = kandidat/forslag.
    approved: bool = False
    created_at: datetime
    updated_at: datetime
    signal_count: int = 0
    claim_count: int = 0


class OpportunityDetailOut(OpportunityOut):
    signals: list[OpportunitySignalRef] = Field(default_factory=list)
    claims: list[ClaimOut] = Field(default_factory=list)


class OpportunityCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    problem_id: uuid.UUID
    relevance_hypothesis: str = Field(min_length=1, max_length=4000)
    evidence_gaps: str | None = Field(default=None, max_length=4000)
    recommended_next_action: str = Field(min_length=1, max_length=4000)
    signal_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)
    claim_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)


class OpportunityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    problem_id: uuid.UUID | None = None
    relevance_hypothesis: str | None = Field(default=None, min_length=1, max_length=4000)
    evidence_gaps: str | None = Field(default=None, max_length=4000)
    recommended_next_action: str | None = Field(default=None, min_length=1, max_length=4000)
    status: OpportunityStatus | None = None
    owner_user_id: uuid.UUID | None = None
    signal_ids: list[uuid.UUID] | None = Field(default=None, max_length=50)
    claim_ids: list[uuid.UUID] | None = Field(default=None, max_length=100)
