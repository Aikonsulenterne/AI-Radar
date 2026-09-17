"""ORM-modeller for adoption cases (Slice 4). DDL ejes af supabase/migrations."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.enums import CaseStatus
from app.models import TimestampMixin


class AdoptionCase(TimestampMixin, Base):
    """Præsentationsenhed for en virksomheds dokumenterede AI-anvendelse.
    Fakta ligger i de tilknyttede claims."""

    __tablename__ = "adoption_cases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("companies.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, name="case_status"),
        nullable=False,
        default=CaseStatus.draft,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class AdoptionCaseClaim(Base):
    __tablename__ = "adoption_case_claims"

    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("adoption_cases.id"), primary_key=True
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("claims.id"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
