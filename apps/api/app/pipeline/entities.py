"""Entity resolution (Technical Master §8, trin 5).

Exact og normaliserede aliases først — deterministisk. Ingen fuzzy/AI-match:
et navn uden match opretter en ny virksomhed (uden opfundne felter), som
reviewer kan flette senere via duplicate-kandidater.
"""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import EntityType
from app.models_claims import Company, EntityAlias, Technology, Vendor


def normalize_alias(name: str) -> str:
    return " ".join(name.casefold().split())


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return slug or "entity"


def _alias_match(db: Session, entity_type: EntityType, name: str) -> uuid.UUID | None:
    alias = db.scalar(
        select(EntityAlias).where(
            EntityAlias.entity_type == entity_type,
            EntityAlias.normalized_alias == normalize_alias(name),
        )
    )
    return alias.entity_id if alias else None


def _add_alias(db: Session, entity_type: EntityType, entity_id: uuid.UUID, name: str) -> None:
    db.add(
        EntityAlias(
            entity_type=entity_type,
            entity_id=entity_id,
            alias=name,
            normalized_alias=normalize_alias(name),
        )
    )


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    counter = 2
    while db.scalar(select(Company).where(Company.slug == slug)) is not None:
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def resolve_company(db: Session, name: str) -> Company:
    """Find virksomhed via alias, ellers opret (uden at opfinde land m.m.)."""
    entity_id = _alias_match(db, EntityType.company, name)
    if entity_id is not None:
        company = db.get(Company, entity_id)
        if company is not None:
            return company

    company = Company(name=name.strip(), slug=_unique_slug(db, slugify(name)))
    db.add(company)
    db.flush()
    _add_alias(db, EntityType.company, company.id, name)
    db.flush()
    return company


def resolve_object_entity(db: Session, name: str) -> tuple[EntityType, uuid.UUID] | None:
    """Match objekt mod teknologi, vendor eller virksomhed — kun via aliases
    eller eksakt (normaliseret) navn. Intet match → None (objektet forbliver
    tekst). Lineær navnescanning er acceptabel ved MVP-volumen (§6: 8
    teknologier, 8–10 vendors, 20–30 virksomheder)."""
    normalized = normalize_alias(name)

    for entity_type in (EntityType.technology, EntityType.vendor, EntityType.company):
        entity_id = _alias_match(db, entity_type, name)
        if entity_id is not None:
            return entity_type, entity_id

    for technology in db.scalars(select(Technology)).all():
        if normalize_alias(technology.name) == normalized:
            return EntityType.technology, technology.id
    for vendor in db.scalars(select(Vendor)).all():
        if normalize_alias(vendor.name) == normalized:
            return EntityType.vendor, vendor.id
    for company in db.scalars(select(Company)).all():
        if normalize_alias(company.name) == normalized:
            return EntityType.company, company.id
    return None
