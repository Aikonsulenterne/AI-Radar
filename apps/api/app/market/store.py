"""Små, menneskeindtastede oplysninger til Til OK, gemt i app_settings.

- Direktørens svar på ja/nej-spørgsmålene (append-only: hvert svar gemmes
  med dato; det nyeste pr. spørgsmål gælder). Kun beslutning og dato — ingen
  OK-tal.
- OK's offentlige status pr. teknologi, registreret af Admin med en
  offentlig kilde (fx ok.dk). Aldrig interne oplysninger.
"""

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.market.overview import OkStatus
from app.models_settings import AppSetting

DECISIONS_KEY = "ok_decisions"
OK_STATUS_KEY = "ok_public_status"
_MAX_ANSWERS = 500

Answer = Literal["ja", "nej", "senere"]
ANSWER_LABELS = {"ja": "ja", "nej": "nej", "senere": "senere"}


def decision_key(question: str) -> str:
    normalized = " ".join(question.casefold().split())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


class StoredAnswer(BaseModel):
    key: str
    question: str
    answer: Answer
    answered_at: datetime
    answered_by: str | None = None


def _value(db: Session, key: str) -> dict[str, Any]:
    row = db.get(AppSetting, key)
    return row.value if row else {}


def _save(db: Session, key: str, value: dict[str, Any]) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value
        row.updated_at = datetime.now(UTC)
    db.flush()


def answers(db: Session) -> list[StoredAnswer]:
    """Alle svar, ældste først."""
    return [StoredAnswer.model_validate(a) for a in _value(db, DECISIONS_KEY).get("items", [])]


def latest_answers(db: Session) -> dict[str, StoredAnswer]:
    latest: dict[str, StoredAnswer] = {}
    for answer in answers(db):
        latest[answer.key] = answer
    return latest


def record_answer(
    db: Session, question: str, answer: Answer, user_id: uuid.UUID | None
) -> StoredAnswer:
    stored = StoredAnswer(
        key=decision_key(question),
        question=question,
        answer=answer,
        answered_at=datetime.now(UTC),
        answered_by=str(user_id) if user_id else None,
    )
    items = _value(db, DECISIONS_KEY).get("items", [])
    items = [*items, stored.model_dump(mode="json")][-_MAX_ANSWERS:]
    _save(db, DECISIONS_KEY, {"items": items})
    return stored


def ok_status(db: Session) -> dict[str, OkStatus]:
    raw: dict[str, Any] = _value(db, OK_STATUS_KEY).get("items", {})
    return {tech_id: OkStatus.model_validate(item) for tech_id, item in raw.items()}


def set_ok_status(db: Session, technology_id: uuid.UUID, status: OkStatus | None) -> None:
    items: dict[str, Any] = dict(_value(db, OK_STATUS_KEY).get("items", {}))
    if status is None:
        items.pop(str(technology_id), None)
    else:
        items[str(technology_id)] = status.model_dump(mode="json")
    _save(db, OK_STATUS_KEY, {"items": items})
