"""Schemas for workerens kørsler."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.enums import RunStatus, RunTrigger


class RunRequest(BaseModel):
    # True ("Kør nu"): alle aktive kilder hentes. False (ugentlig): kun forfaldne.
    force_all: bool = True


class WorkerRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trigger: RunTrigger
    force_all: bool
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None
    started_by_user_id: uuid.UUID | None
    sources_checked: int
    documents_created: int
    documents_unchanged: int
    fetch_failures: int
    documents_processed: int
    documents_published: int
    processing_skipped_no_ai: bool
    error_message_safe: str | None
