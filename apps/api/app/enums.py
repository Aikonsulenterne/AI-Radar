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
