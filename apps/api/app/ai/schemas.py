"""Versionerede JSON-schemas for AI-output med output validation.

Ved schemafejl udføres højst én kontrolleret retry; derefter går dokumentet
til manuel opfølgning (Technical Master §10).
"""

import json
import uuid
from typing import Literal, TypeVar

from pydantic import BaseModel, Field, ValidationError

from app.ai.provider import AIProvider, AIProviderError
from app.enums import ClaimType, Predicate

SCHEMA_VERSION = "1.0.0"


class RelevanceResult(BaseModel):
    relevant: bool
    reason: str = Field(max_length=500)


class ExtractedClaim(BaseModel):
    claim_type: ClaimType
    predicate: Predicate
    subject_name: str = Field(min_length=1, max_length=300)
    object_name: str | None = Field(default=None, max_length=300)
    object_text: str | None = Field(default=None, max_length=2000)
    supporting_excerpt: str = Field(min_length=1, max_length=4000)


class ExtractionResult(BaseModel):
    claims: list[ExtractedClaim] = Field(max_length=100)


class ProposedOpportunity(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    problem_name: str = Field(min_length=1, max_length=200)
    relevance_hypothesis: str = Field(min_length=1, max_length=2000)
    evidence_gaps: str | None = Field(default=None, max_length=2000)
    recommended_next_action: str = Field(min_length=1, max_length=2000)


class OpportunityProposalResult(BaseModel):
    """Modellen må afvise at foreslå noget — det er et gyldigt svar."""

    proposal: ProposedOpportunity | None = None
    reason: str = Field(default="", max_length=500)


class SignalDraft(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=1500)
    analysis: str = Field(default="", max_length=2000)
    recommendation: str = Field(default="", max_length=1500)


class InsightDraft(BaseModel):
    type: Literal["adoption", "vendor_move", "effect", "barrier", "gap", "new_tech"]
    title: str = Field(min_length=1, max_length=160)
    finding: str = Field(min_length=1, max_length=1200)
    implication: str = Field(default="", max_length=1200)
    recommendation: str = Field(default="", max_length=800)
    problem: str | None = Field(default=None, max_length=200)
    claims: list[int] = Field(min_length=1, max_length=40)


class InsightResult(BaseModel):
    insights: list[InsightDraft] = Field(default_factory=list, max_length=12)


class AISchemaError(Exception):
    """AI-output kunne ikke valideres mod schema efter kontrolleret retry."""


TModel = TypeVar("TModel", bound=BaseModel)


class MarketTechnologyDraft(BaseModel):
    technology: str = Field(min_length=1, max_length=120)
    vendor: str = Field(min_length=1, max_length=200)
    product: str | None = Field(default=None, max_length=200)
    what_it_does_da: str | None = Field(default=None, max_length=400)
    business_value_da: str | None = Field(default=None, max_length=400)
    danish_supported: bool | None = None
    area: list[str] = Field(default_factory=list, max_length=3)
    quote: str = Field(min_length=1, max_length=1200)


class MarketCaseDraft(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    country: str | None = Field(default=None, max_length=60)
    industry: str | None = Field(default=None, max_length=60)
    what_they_did_da: str | None = Field(default=None, max_length=400)
    technology: str | None = Field(default=None, max_length=120)
    vendor: str | None = Field(default=None, max_length=200)
    adoption_stage: str | None = Field(default=None, max_length=30)
    scope: str | None = Field(default=None, max_length=300)
    effect: str | None = Field(default=None, max_length=500)
    kpi: str | None = Field(default=None, max_length=60)
    effect_source: str | None = Field(default=None, max_length=30)
    lesson: str | None = Field(default=None, max_length=500)
    area: list[str] = Field(default_factory=list, max_length=3)
    quote: str = Field(min_length=1, max_length=1200)


class MarketExtractionResult(BaseModel):
    technologies: list[MarketTechnologyDraft] = Field(default_factory=list, max_length=30)
    cases: list[MarketCaseDraft] = Field(default_factory=list, max_length=30)


class OkBriefPoint(BaseModel):
    text: str = Field(min_length=1, max_length=400)
    refs: list[str] = Field(default_factory=list, max_length=10)


class OkBriefCaseRef(BaseModel):
    ref: str = Field(min_length=1, max_length=20)
    why: str = Field(default="", max_length=300)


class OkBriefProblem(BaseModel):
    problem: str = Field(min_length=1, max_length=20)
    technologies: list[str] = Field(default_factory=list, max_length=10)
    cases: list[OkBriefCaseRef] = Field(default_factory=list, max_length=10)
    next_step: str = Field(default="", max_length=400)


class OkBriefResult(BaseModel):
    top_now: list[OkBriefPoint] = Field(default_factory=list, max_length=10)
    problems: list[OkBriefProblem] = Field(default_factory=list, max_length=40)


_RETRY_SUFFIX = (
    "\n\nYour previous answer was not valid JSON for the required schema. "
    "Return ONLY a valid JSON object matching the schema. No prose."
)


def call_with_schema(
    provider: AIProvider,
    *,
    prompt_id: str,
    prompt_version: str,
    system: str,
    user: str,
    result_model: type[TModel],
    document_id: uuid.UUID | None = None,
) -> TModel:
    """Kald provider og validér output; højst én kontrolleret retry."""
    last_error: Exception | None = None
    for attempt in range(2):
        prompt_user = user if attempt == 0 else user + _RETRY_SUFFIX
        try:
            raw = provider.complete_text(
                prompt_id=prompt_id,
                prompt_version=prompt_version,
                system=system,
                user=prompt_user,
                document_id=document_id,
            )
            return result_model.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError, AIProviderError) as exc:
            last_error = exc
    raise AISchemaError("AI-output kunne ikke valideres efter retry.") from last_error
