"""Audit-logning af beslutninger (Technical Master §18).

Loggen dækker de steder, hvor et menneske eller systemet ændrer, hvad der
tæller som dokumenteret: review af claims, kilder og opportunities, samt
publicering af signaler og cases. `changes` rummer kun de ændrede felters
før/efter-værdier — aldrig tokens, secrets eller fulde dokumenttekster.
"""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from app.context import current_request_id
from app.models_audit import AuditEvent

# Længdegrænse pr. værdi i changes: audit-loggen er et spor, ikke en kopi
# af indholdet.
_MAX_VALUE_CHARS = 500


class AuditEntity(StrEnum):
    source = "source"
    document = "document"
    claim = "claim"
    signal = "signal"
    adoption_case = "adoption_case"
    opportunity = "opportunity"


class AuditAction(StrEnum):
    created = "created"
    updated = "updated"
    approved = "approved"
    rejected = "rejected"
    published = "published"
    archived = "archived"
    fetched = "fetched"
    processed = "processed"
    review_completed = "review_completed"
    ai_proposed = "ai_proposed"


def _truncate(value: Any) -> Any:
    if isinstance(value, str) and len(value) > _MAX_VALUE_CHARS:
        return value[:_MAX_VALUE_CHARS] + "…"
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def field_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Før/efter for de felter, der faktisk ændrede sig."""
    changed: dict[str, Any] = {}
    for field, new_value in after.items():
        old_value = before.get(field)
        if old_value != new_value:
            changed[field] = {"fra": _truncate(old_value), "til": _truncate(new_value)}
    return changed


def record(
    db: Session,
    *,
    entity_type: AuditEntity,
    entity_id: uuid.UUID,
    action: AuditAction,
    actor_user_id: uuid.UUID | None = None,
    changes: dict[str, Any] | None = None,
) -> AuditEvent:
    """Skriv én audit-række. Kaldes i samme transaktion som ændringen."""
    event = AuditEvent(
        entity_type=entity_type.value,
        entity_id=entity_id,
        action=action.value,
        actor_user_id=actor_user_id,
        changes={key: _truncate(value) for key, value in changes.items()} if changes else None,
        request_id=current_request_id(),
    )
    db.add(event)
    db.flush()
    return event
