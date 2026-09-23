"""Schemas for audit-loggen (Technical Master §18)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime
    # Null = systemhandling (worker), ikke en ukendt bruger.
    actor_user_id: uuid.UUID | None
    entity_type: str
    entity_id: uuid.UUID
    action: str
    changes: dict[str, Any] | None
    request_id: str | None
