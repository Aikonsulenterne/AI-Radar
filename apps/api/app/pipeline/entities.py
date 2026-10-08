"""Entity resolution (Technical Master §8, trin 5).

Exact og normaliserede aliases først — deterministisk. Ingen fuzzy/AI-match:
et navn uden match opretter en ny virksomhed (uden opfundne felter), som
reviewer kan flette senere via duplicate-kandidater.
"""

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import EntityType
from app.models_claims import Company, EntityAlias, Technology, Vendor


def normalize_alias(name: str) -> str:
    return " ".join(name.casefold().split())


# Selskabsformer, der ikke gør to navne til to organisationer:
# "Zendesk" = "Zendesk Inc." = "Zendesk, Inc.".
_LEGAL_SUFFIXES = frozenset(
    {
        "inc",
        "inc.",
        "ltd",
        "ltd.",
        "llc",
        "a/s",
        "as",
        "aps",
        "ab",
        "oy",
        "oyj",
        "gmbh",
        "ag",
        "bv",
        "b.v.",
        "nv",
        "sa",
        "plc",
        "corp",
        "corp.",
        "corporation",
        "co.",
        "group",
    }
)


def legal_base_name(name: str) -> str:
    """Normaliseret navn uden afsluttende selskabsform og komma."""
    words = normalize_alias(name).replace(",", " ").split()
    while len(words) > 1 and words[-1] in _LEGAL_SUFFIXES:
        words.pop()
    return " ".join(words)


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


def _legal_base_match(db: Session, name: str) -> uuid.UUID | None:
    """Samme organisation under en anden selskabsform. Lineær scanning af
    virksomhedsaliases er acceptabel ved radarens volumen."""
    base = legal_base_name(name)
    if not base:
        return None
    for alias in db.scalars(
        select(EntityAlias).where(EntityAlias.entity_type == EntityType.company)
    ).all():
        if legal_base_name(alias.normalized_alias) == base:
            return alias.entity_id
    return None


def resolve_company(db: Session, name: str) -> Company:
    """Find virksomhed via alias, ellers opret (uden at opfinde land m.m.)."""
    entity_id = _alias_match(db, EntityType.company, name)
    if entity_id is not None:
        company = db.get(Company, entity_id)
        if company is not None:
            return company

    entity_id = _legal_base_match(db, name)
    if entity_id is not None:
        company = db.get(Company, entity_id)
        if company is not None:
            # Husk varianten, så næste opslag er et direkte alias-match.
            _add_alias(db, EntityType.company, company.id, name)
            db.flush()
            return company

    company = Company(name=name.strip(), slug=_unique_slug(db, slugify(name)))
    db.add(company)
    db.flush()
    _add_alias(db, EntityType.company, company.id, name)
    db.flush()
    return company


# Et capability-navn er kort og generisk ("Speech Analytics"). Længere tekst
# er en beskrivelse, ikke en ny teknologi, og forbliver objekttekst.
_MAX_CAPABILITY_CHARS = 60
_MAX_CAPABILITY_WORDS = 6

CANDIDATE_DEFINITION = "Ny capability fundet automatisk i markedet; ikke kurateret endnu."


def resolve_candidate_technology(db: Session, name: str) -> Technology | None:
    """Find eller opret en kandidat-teknologi for en capability, der ikke
    står på radarens liste. None, når navnet ikke ligner et capability-navn.

    Kandidaten placeres ikke i en horisont (det er en vurdering, AI ikke
    træffer) og har ingen opfundet definition; en Admin optager eller
    afviser den. Samme navn genbruges via alias, så der ikke opstår dubletter.
    """
    cleaned = " ".join(name.split())
    if not cleaned or len(cleaned) > _MAX_CAPABILITY_CHARS:
        return None
    if len(cleaned.split()) > _MAX_CAPABILITY_WORDS:
        return None
    entity_id = _alias_match(db, EntityType.technology, cleaned)
    if entity_id is not None:
        return db.get(Technology, entity_id)

    base = slugify(cleaned)
    slug = base
    counter = 2
    while db.scalar(select(Technology).where(Technology.slug == slug)) is not None:
        slug = f"{base}-{counter}"
        counter += 1
    technology = Technology(
        name=cleaned,
        slug=slug,
        definition=CANDIDATE_DEFINITION,
        horizon=None,
        active=True,
        is_candidate=True,
        discovered_at=datetime.now(UTC),
    )
    db.add(technology)
    db.flush()
    _add_alias(db, EntityType.technology, technology.id, cleaned)
    db.flush()
    return technology


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


def entity_name(
    db: Session, entity_type: EntityType | None, entity_id: uuid.UUID | None
) -> str | None:
    """Navnet på en entity, uanset type. Ukendt entity giver None."""
    if entity_type is None or entity_id is None:
        return None
    if entity_type == EntityType.company:
        company = db.get(Company, entity_id)
        return company.name if company else None
    if entity_type == EntityType.technology:
        technology = db.get(Technology, entity_id)
        return technology.name if technology else None
    vendor = db.get(Vendor, entity_id)
    return vendor.name if vendor else None
