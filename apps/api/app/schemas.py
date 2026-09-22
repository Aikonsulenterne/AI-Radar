"""Typed request-/response-schemas. OpenAPI er kontraktkilde."""

import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.enums import AccessClass, Frequency, ProcessingStatus, RetrievalMethod, SourceType

T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: SourceType
    retrieval_method: RetrievalMethod
    access_class: AccessClass
    base_url: str | None = None
    endpoint_url: str | None = None
    country_code: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    frequency: Frequency = Frequency.manual
    notes: str | None = None
    active: bool = True

    @model_validator(mode="after")
    def endpoint_required_for_fetch(self) -> "SourceCreate":
        if self.retrieval_method in (RetrievalMethod.rss, RetrievalMethod.web_fetch):
            if not self.endpoint_url:
                raise ValueError("endpoint_url er påkrævet for rss og web_fetch.")
        return self


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    source_type: SourceType | None = None
    retrieval_method: RetrievalMethod | None = None
    access_class: AccessClass | None = None
    base_url: str | None = None
    endpoint_url: str | None = None
    country_code: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    frequency: Frequency | None = None
    notes: str | None = None
    active: bool | None = None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    base_url: str | None
    source_type: SourceType
    retrieval_method: RetrievalMethod
    endpoint_url: str | None
    country_code: str | None
    frequency: Frequency
    access_class: AccessClass
    active: bool
    last_checked_at: datetime | None
    next_check_at: datetime | None
    owner_user_id: uuid.UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    canonical_url: str | None
    title: str | None
    language_code: str | None
    published_at: datetime | None
    retrieved_at: datetime
    content_hash: str
    mime_type: str | None
    processing_status: ProcessingStatus
    is_demo: bool
    error_code: str | None
    created_at: datetime


class DocumentDetailOut(DocumentOut):
    normalized_text: str | None
    raw_storage_path: str | None
    # Kortvarig signeret URL til den originale fil (null i lokal udvikling).
    raw_url: str | None = None


class IngestOutcome(BaseModel):
    document: DocumentOut
    created: bool


class RunDocumentOut(BaseModel):
    document: DocumentOut
    created: bool


class RunFailureOut(BaseModel):
    url: str
    code: str
    message: str


class RunResult(BaseModel):
    """En kørsel kan give flere dokumenter (RSS) eller ét (web_fetch)."""

    source_id: uuid.UUID
    documents: list[RunDocumentOut]
    created_count: int
    unchanged_count: int
    failures: list[RunFailureOut]
