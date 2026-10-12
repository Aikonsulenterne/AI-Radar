"""Små, redigerbare indstillinger (fx beslutningsoplæggets OK-tal).

Én række pr. nøgle med en JSON-værdi; indholdet er menneskeindtastet og
valideres af API-skemaet, ikke af databasen.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models_claims import JsonValue


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
