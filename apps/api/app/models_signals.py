"""ORM-modeller for signaler (Slice 3). DDL ejes af supabase/migrations."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.enums import DocumentationLevel, SignalStatus
from app.models import TimestampMixin


class Signal(TimestampMixin, Base):
    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    analysis: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    documentation_level: Mapped[DocumentationLevel] = mapped_column(
        Enum(DocumentationLevel, name="documentation_level"), nullable=False
    )
    status: Mapped[SignalStatus] = mapped_column(
        Enum(SignalStatus, name="signal_status"),
        nullable=False,
        default=SignalStatus.draft,
        index=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class SignalClaim(Base):
    __tablename__ = "signal_claims"

    signal_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("signals.id"), primary_key=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("claims.id"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
