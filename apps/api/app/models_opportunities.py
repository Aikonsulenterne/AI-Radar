"""ORM-modeller for problem-taxonomi og opportunities (Slice 5)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.enums import OpportunityStatus
from app.models import TimestampMixin


class ProblemTaxonomy(TimestampMixin, Base):
    __tablename__ = "problem_taxonomy"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    area: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Opportunity(TimestampMixin, Base):
    """Ekstern evidens koblet til et reelt OK-problem og et næste skridt.
    AI må foreslå; et menneske godkender (approved_by_user_id)."""

    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    problem_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("problem_taxonomy.id"), nullable=False, index=True
    )
    relevance_hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_gaps: Mapped[str | None] = mapped_column(Text)
    recommended_next_action: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[OpportunityStatus] = mapped_column(
        Enum(OpportunityStatus, name="opportunity_status"),
        nullable=False,
        default=OpportunityStatus.identified,
        index=True,
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    # Provenance for AI-forslag: et forslag må aldrig fremstå som kurateret.
    proposed_by_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    proposal_prompt_version: Mapped[str | None] = mapped_column(Text)


class OpportunitySignal(Base):
    __tablename__ = "opportunity_signals"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id"), primary_key=True
    )
    signal_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("signals.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OpportunityClaim(Base):
    __tablename__ = "opportunity_claims"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("opportunities.id"), primary_key=True
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
