"""Markedsfund: hvad leverandører sælger, og hvordan andre bruger AI.

Ét fund pr. (dokument, leverandør, teknologi) eller (dokument, virksomhed,
teknologi). Felterne fra AI-udtrækket ligger i `data`; citatet er ordret
tekst fra dokumentet, så fundet altid kan spores til sin kilde.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models_claims import JsonValue

KIND_TECHNOLOGY = "technology"
KIND_CASE = "case"


class MarketItem(Base):
    __tablename__ = "market_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    technology_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("technologies.id"))
    company_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("companies.id"))
    vendor_company_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("companies.id"))
    areas: Mapped[list[str]] = mapped_column(JsonValue, nullable=False, default=list)
    data: Mapped[dict[str, Any]] = mapped_column(JsonValue, nullable=False, default=dict)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hidden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hidden_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
