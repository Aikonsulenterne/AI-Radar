"""ORM-modeller for entities, claims og evidens (Slice 2).

Afspejler supabase/migrations — DDL ejes af migrations.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.enums import (
    ClaimCreatedBy,
    ClaimLifecycle,
    ClaimRelation,
    ClaimType,
    EntityType,
    EvidenceRelationship,
    Predicate,
    ReviewStatus,
    SourceType,
    TechHorizon,
)
from app.models import TimestampMixin

# jsonb på PostgreSQL, generisk JSON i unit tests (SQLite).
JsonValue = JSON().with_variant(JSONB(), "postgresql")


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # Nullable som dokumenteret afvigelse: landet må ikke opfindes, når
    # kilden ikke nævner det (docs/05_Implementation_Notes.md).
    country_code: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(Text)
    website_url: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EntityAlias(TimestampMixin, Base):
    __tablename__ = "entity_aliases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type"), nullable=False
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_alias: Mapped[str] = mapped_column(Text, nullable=False)


class Technology(TimestampMixin, Base):
    __tablename__ = "technologies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    horizon: Mapped[TechHorizon] = mapped_column(
        Enum(TechHorizon, name="tech_horizon"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Vendor(TimestampMixin, Base):
    __tablename__ = "vendors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    website_url: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Claim(TimestampMixin, Base):
    """Ét afgrænset faktuelt udsagn. Ukendte værdier forbliver null."""

    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    claim_type: Mapped[ClaimType] = mapped_column(
        Enum(ClaimType, name="claim_type"), nullable=False
    )
    subject_entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType, name="entity_type"), nullable=False
    )
    subject_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    predicate: Mapped[Predicate] = mapped_column(
        Enum(Predicate, name="claim_predicate"), nullable=False
    )
    object_entity_type: Mapped[EntityType | None] = mapped_column(
        Enum(EntityType, name="entity_type")
    )
    object_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    object_text: Mapped[str | None] = mapped_column(Text)
    normalized_value: Mapped[dict[str, Any] | None] = mapped_column(JsonValue)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"),
        nullable=False,
        default=ReviewStatus.proposed,
        index=True,
    )
    lifecycle_status: Mapped[ClaimLifecycle] = mapped_column(
        Enum(ClaimLifecycle, name="claim_lifecycle"),
        nullable=False,
        default=ClaimLifecycle.current,
    )
    created_by: Mapped[ClaimCreatedBy] = mapped_column(
        Enum(ClaimCreatedBy, name="claim_created_by"), nullable=False
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClaimEvidence(TimestampMixin, Base):
    """Relationen claim → præcist dokumentuddrag. Uddraget skal kunne
    vurderes af en reviewer uden at stole på AI-resuméet."""

    __tablename__ = "claim_evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("claims.id"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("documents.id"), nullable=False, index=True
    )
    supporting_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt_start: Mapped[int | None] = mapped_column()
    excerpt_end: Mapped[int | None] = mapped_column()
    relationship: Mapped[EvidenceRelationship] = mapped_column(
        Enum(EvidenceRelationship, name="evidence_relationship"),
        nullable=False,
        default=EvidenceRelationship.supports,
    )
    source_type_snapshot: Mapped[SourceType | None] = mapped_column(
        Enum(SourceType, name="source_type")
    )
    independent_origin_key: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status"),
        nullable=False,
        default=ReviewStatus.proposed,
    )


class ClaimRelationLink(Base):
    """Reviewerens relation mellem to claims. Begge claims består — et
    gammelt claim overskrives aldrig (Technical Master §15)."""

    __tablename__ = "claim_relations"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("claims.id"), nullable=False, index=True
    )
    related_claim_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("claims.id"), nullable=False, index=True
    )
    relation: Mapped[ClaimRelation] = mapped_column(
        Enum(ClaimRelation, name="claim_relation"), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
