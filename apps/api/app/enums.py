"""Domæne-enums (Technical Master §5, §7; Product Master §11).

Værdierne matcher PostgreSQL-enum-typerne i supabase/migrations 1:1.
"""

from enum import StrEnum


class SourceType(StrEnum):
    primary = "primary"
    independent_analysis = "independent_analysis"
    vendor_case = "vendor_case"
    vendor_claim = "vendor_claim"
    media = "media"
    research = "research"
    early_signal = "early_signal"


class RetrievalMethod(StrEnum):
    rss = "rss"
    web_fetch = "web_fetch"
    manual_upload = "manual_upload"


class Frequency(StrEnum):
    manual = "manual"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class AccessClass(StrEnum):
    public = "public"
    licensed = "licensed"
    restricted = "restricted"


class ProcessingStatus(StrEnum):
    discovered = "discovered"
    fetched = "fetched"
    normalized = "normalized"
    classified_relevant = "classified_relevant"
    classified_irrelevant = "classified_irrelevant"
    extraction_pending = "extraction_pending"
    review_pending = "review_pending"
    partially_reviewed = "partially_reviewed"
    reviewed = "reviewed"
    failed = "failed"


class UserRole(StrEnum):
    reader = "reader"
    reviewer = "reviewer"
    admin = "admin"


# --- Claims og entities (Slice 2) ---
class EntityType(StrEnum):
    company = "company"
    technology = "technology"
    vendor = "vendor"


class ClaimType(StrEnum):
    adoption = "adoption"
    use_case = "use_case"
    stage = "stage"
    technology_vendor = "technology_vendor"
    effect = "effect"
    negative = "negative"
    organization = "organization"


class Predicate(StrEnum):
    USES_CAPABILITY = "USES_CAPABILITY"
    USES_FOR = "USES_FOR"
    ADOPTION_STAGE = "ADOPTION_STAGE"
    USES_TECHNOLOGY = "USES_TECHNOLOGY"
    USES_VENDOR = "USES_VENDOR"
    REPORTED_EFFECT = "REPORTED_EFFECT"
    REPORTS_BARRIER = "REPORTS_BARRIER"
    REPORTS_NEGATIVE_OUTCOME = "REPORTS_NEGATIVE_OUTCOME"
    ABANDONED_OR_REPLACED = "ABANDONED_OR_REPLACED"
    USES_GOVERNANCE_MODEL = "USES_GOVERNANCE_MODEL"
    USES_HUMAN_REVIEW = "USES_HUMAN_REVIEW"
    REPORTS_ADOPTION_APPROACH = "REPORTS_ADOPTION_APPROACH"
    REPORTS_DATA_FOUNDATION = "REPORTS_DATA_FOUNDATION"


# Eksklusiv mapping claim_type → tilladte predicates (Technical Master §5).
PREDICATES_BY_CLAIM_TYPE: dict[ClaimType, frozenset[Predicate]] = {
    ClaimType.adoption: frozenset({Predicate.USES_CAPABILITY}),
    ClaimType.use_case: frozenset({Predicate.USES_FOR}),
    ClaimType.stage: frozenset({Predicate.ADOPTION_STAGE}),
    ClaimType.technology_vendor: frozenset({Predicate.USES_TECHNOLOGY, Predicate.USES_VENDOR}),
    ClaimType.effect: frozenset({Predicate.REPORTED_EFFECT}),
    ClaimType.negative: frozenset(
        {
            Predicate.REPORTS_BARRIER,
            Predicate.REPORTS_NEGATIVE_OUTCOME,
            Predicate.ABANDONED_OR_REPLACED,
        }
    ),
    ClaimType.organization: frozenset(
        {
            Predicate.USES_GOVERNANCE_MODEL,
            Predicate.USES_HUMAN_REVIEW,
            Predicate.REPORTS_ADOPTION_APPROACH,
            Predicate.REPORTS_DATA_FOUNDATION,
        }
    ),
}

# Tilladte adoption stages (Technical Master §5).
ADOPTION_STAGES: frozenset[str] = frozenset(
    {"Experiment", "Pilot", "Production", "Scale", "Unknown"}
)


class ReviewStatus(StrEnum):
    proposed = "proposed"
    approved = "approved"
    approved_with_edits = "approved_with_edits"
    needs_corroboration = "needs_corroboration"
    rejected = "rejected"


class ClaimLifecycle(StrEnum):
    current = "current"
    contradicted = "contradicted"
    superseded = "superseded"
    expired = "expired"


class ClaimCreatedBy(StrEnum):
    ai = "ai"
    human = "human"


class EvidenceRelationship(StrEnum):
    supports = "supports"
    contradicts = "contradicts"
    supersedes = "supersedes"


class ClaimRelation(StrEnum):
    """Reviewerens endelige relation mellem to claims (Technical Master §15)."""

    supports = "supports"
    contradicts = "contradicts"
    supersedes = "supersedes"


class TechHorizon(StrEnum):
    now = "now"
    next = "next"
    horizon = "horizon"


# --- Signaler (Slice 3) ---
class DocumentationLevel(StrEnum):
    strong = "strong"
    limited = "limited"
    early = "early"
    conflicting = "conflicting"


class SignalStatus(StrEnum):
    draft = "draft"
    published = "published"
    archived = "archived"


# --- Adoption cases (Slice 4) ---
class CaseStatus(StrEnum):
    draft = "draft"
    published = "published"
    archived = "archived"


# --- Opportunities (Slice 5) ---
class OpportunityStatus(StrEnum):
    identified = "identified"
    investigating = "investigating"
    business_case = "business_case"
    pilot = "pilot"
    scaling = "scaling"
    closed = "closed"
