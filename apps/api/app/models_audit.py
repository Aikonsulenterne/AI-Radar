"""ORM-model for audit-loggen (Technical Master §18).

Append-only: rækker rettes og slettes aldrig af applikationen.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models_claims import JsonValue


class AuditEvent(Base):
    __tablename__ = "audit_log"

    # Stigende sekvens: occurred_at er transaktionens starttidspunkt og er ens
    # for flere rækker i samme request, så id'et bærer rækkefølgen.
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Null = systemhandling (worker), ikke en anonym bruger.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    # Kun ændrede felters før/efter — aldrig secrets eller dokumenttekst.
    changes: Mapped[dict[str, Any] | None] = mapped_column(JsonValue)
    request_id: Mapped[str | None] = mapped_column(Text)
