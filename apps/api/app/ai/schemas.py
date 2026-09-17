"""Versionerede JSON-schemas for AI-output med output validation.

Ved schemafejl udføres højst én kontrolleret retry; derefter går dokumentet
til manuel opfølgning (Technical Master §10).
"""

import json
import uuid
from typing import TypeVar

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


class AISchemaError(Exception):
    """AI-output kunne ikke valideres mod schema efter kontrolleret retry."""


TModel = TypeVar("TModel", bound=BaseModel)

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
