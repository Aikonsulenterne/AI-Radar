"""Sikrer leverandør-migrationen, når API'et starter (PostgreSQL).

Render deployer fra main uden at køre migrations. Koden fra 2026-10-08
læser nye kolonner (technologies.is_candidate, documents.vendor_extracted_at,
worker_runs.documents_reread) og nye predicate-værdier; mangler de, fejler
næsten alle sider. Migrationen ejer stadig skemaet
(supabase/migrations/20261008090000_vendor_offerings.sql) — her gentages kun
dens idempotente sætninger, så en deploy aldrig kommer før skemaet. Testen
test_schema_guard holder de to i sync. Kan fjernes, når migrationen er kørt
alle steder.
"""

import logging

from sqlalchemy import Connection, text

from app.db import get_engine

logger = logging.getLogger("ai_radar.schema")

VENDOR_MIGRATION_STATEMENTS: tuple[str, ...] = (
    "alter type claim_predicate add value if not exists 'OFFERS_CAPABILITY'",
    "alter type claim_predicate add value if not exists 'OFFERS_IN_MARKET'",
    "alter type claim_predicate add value if not exists 'SUPPORTS_LANGUAGE'",
    "alter table technologies add column if not exists is_candidate boolean not null default false",
    "alter table technologies add column if not exists discovered_at timestamptz null",
    "alter table technologies alter column horizon drop not null",
    "alter table documents add column if not exists vendor_extracted_at timestamptz null",
    "alter table worker_runs add column if not exists documents_reread integer not null default 0",
    # Teknologien Virtual Agent (data, også idempotent).
    "with inserted as ( insert into technologies (name, slug, definition, horizon) values ( "
    "'Virtual Agent', 'virtual-agent', 'Chat- og voicebots, der selv besvarer og løser "
    "kundehenvendelser (selvbetjening).', 'now' ) on conflict (slug) do nothing returning id, "
    "name ) insert into entity_aliases (entity_type, entity_id, alias, normalized_alias) select "
    "'technology'::entity_type, id, name, lower(name) from inserted on conflict (entity_type, "
    "normalized_alias) do nothing",
)


# Kundecenter-kildepakken (supabase/ops/kundecenter_sources.sql), indsat én
# gang: findes en kilde med markøren, rører opstarten ikke kilderne — så
# kommer kilder, en Admin har slået fra, ikke igen.
SOURCE_PACK_MARKER = "Kundecenter-kildepakke 2026-10"
SOURCE_PACK: tuple[tuple[str, str, str, str, str | None], ...] = (
    (
        "CX Network – Contact Center",
        "https://www.cxnetwork.com",
        "media",
        "https://www.cxnetwork.com/rss/categories/contact-center",
        None,
    ),
    (
        "CCW Digital – Tools & Technologies",
        "https://europe.customercontactweekdigital.com",
        "media",
        "https://europe.customercontactweekdigital.com/rss/categories/tools-technologies",
        None,
    ),
    (
        "Call Centre Helper",
        "https://www.callcentrehelper.com",
        "media",
        "https://www.callcentrehelper.com/feed",
        None,
    ),
    (
        "Bing News: kundeservice + kunstig intelligens",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=kundeservice+%22kunstig+intelligens%22&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: kundecenter AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=kundecenter+AI&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: chatbot kundeservice",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=chatbot+kundeservice&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: AI kundeservice Norden",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%22customer+service%22+AI+Denmark+OR+Nordic&format=rss",
        None,
    ),
    (
        "Bing News: Puzzel AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=Puzzel+AI&format=rss",
        None,
    ),
    (
        "Bing News: Dixa AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=Dixa+AI+customer+service&format=rss",
        None,
    ),
    (
        "Bing News: Zendesk AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=Zendesk+AI+agents&format=rss",
        None,
    ),
    (
        "Bing News: Genesys AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=Genesys+Cloud+AI&format=rss",
        None,
    ),
    (
        "Bing News: Salesforce Agentforce Service",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=Agentforce+customer+service&format=rss",
        None,
    ),
    (
        "Bing News: Dynamics 365 Contact Center",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%22Dynamics+365+Contact+Center%22&format=rss",
        None,
    ),
    (
        "Bing News: contact center AI lancering",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%22contact+center%22+AI+launches&format=rss",
        None,
    ),
)


def _ensure_source_pack(connection: Connection) -> None:
    seeded = connection.execute(
        text("select 1 from sources where notes like :marker limit 1"),
        {"marker": f"{SOURCE_PACK_MARKER}%"},
    ).first()
    if seeded is not None:
        return
    for name, base_url, source_type, endpoint_url, country_code in SOURCE_PACK:
        connection.execute(
            text(
                "insert into sources (name, base_url, source_type, retrieval_method, "
                "endpoint_url, country_code, frequency, access_class, active, next_check_at, "
                "notes) select :name, :base_url, cast(:source_type as source_type), "
                "'rss'::retrieval_method, :endpoint_url, :country_code, "
                "'weekly'::source_frequency, 'public'::access_class, true, now(), :marker "
                "where not exists (select 1 from sources s where s.endpoint_url = :endpoint_url)"
            ),
            {
                "name": name,
                "base_url": base_url,
                "source_type": source_type,
                "endpoint_url": endpoint_url,
                "country_code": country_code,
                "marker": SOURCE_PACK_MARKER,
            },
        )
    connection.execute(
        text(
            "update sources set active = false, notes = coalesce(notes || ' · ', '') || "
            "'Pauset 2026-10: ikke kundecenter-relevant' "
            "where active and endpoint_url ilike '%aws.amazon.com%'"
        )
    )
    logger.info("source_pack_seeded count=%d", len(SOURCE_PACK))


# Fejl fra seneste opstart (vises i /health, så de kan ses uden Render-loggen).
LAST_ERRORS: list[str] = []

# Kolonner og enum-værdier, koden kræver. Bruges af /health.
_REQUIRED_COLUMNS = (
    ("technologies", "is_candidate"),
    ("technologies", "discovered_at"),
    ("documents", "vendor_extracted_at"),
    ("worker_runs", "documents_reread"),
)
_REQUIRED_PREDICATES = ("OFFERS_CAPABILITY", "OFFERS_IN_MARKET", "SUPPORTS_LANGUAGE")


def _short(exc: Exception) -> str:
    """Første linje af fejlen — aldrig forbindelsesstreng eller parametre."""
    first = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
    return f"{exc.__class__.__name__}: {first}"[:300]


def missing_schema() -> list[str] | None:
    """Det, der mangler i databasen; [] = alt på plads, None = ikke PostgreSQL
    eller kunne ikke tjekkes."""
    engine = get_engine()
    if engine.dialect.name != "postgresql":
        return None
    try:
        with engine.connect() as connection:
            columns = {
                (row[0], row[1])
                for row in connection.execute(
                    text(
                        "select table_name, column_name from information_schema.columns "
                        "where table_schema = current_schema()"
                    )
                )
            }
            predicates = {
                row[0]
                for row in connection.execute(
                    text("select unnest(enum_range(null::claim_predicate))::text")
                )
            }
    except Exception as exc:  # noqa: BLE001
        LAST_ERRORS.append(_short(exc))
        return None
    missing = [
        f"{table}.{column}" for table, column in _REQUIRED_COLUMNS if (table, column) not in columns
    ]
    missing += [
        f"claim_predicate.{value}" for value in _REQUIRED_PREDICATES if value not in predicates
    ]
    return missing


def ensure_vendor_schema() -> None:
    """Kør de idempotente sætninger. Fejl logges (fx manglende rettigheder
    eller en låst tabel) og stopper ikke opstarten; de vises i /health."""
    LAST_ERRORS.clear()
    try:
        engine = get_engine()
        if engine.dialect.name != "postgresql":
            return
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            # Vent aldrig længe på en lås: en hængende opstart er værre end en
            # sætning, der prøves igen ved næste genstart.
            connection.execute(text("set lock_timeout = '10s'"))
            connection.execute(text("set statement_timeout = '60s'"))
            for statement in VENDOR_MIGRATION_STATEMENTS:
                try:
                    connection.execute(text(statement))
                except Exception as exc:  # noqa: BLE001 — opstarten må ikke dø
                    LAST_ERRORS.append(_short(exc))
                    logger.error("schema_guard_failed error=%s", _short(exc))
            try:
                _ensure_source_pack(connection)
            except Exception as exc:  # noqa: BLE001
                LAST_ERRORS.append(_short(exc))
                logger.error("source_pack_failed error=%s", _short(exc))
    except Exception as exc:  # noqa: BLE001 — fx ingen forbindelse ved opstart
        LAST_ERRORS.append(_short(exc))
        logger.error("schema_guard_unavailable error=%s", _short(exc))
        return
    logger.info("schema_guard_done errors=%d", len(LAST_ERRORS))
