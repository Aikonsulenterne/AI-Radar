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


# Kildepakke 2 (2026-10-10): konkrete leverandør- og kundecase-sider om AI i
# danske og nordiske kundecentre, fundet ved research og hentet månedligt med
# web_fetch. Siderne gemmes kun igen, når teksten ændrer sig væsentligt.
CASE_PAGES_MARKER = "Leverandør- og casesider 2026-10"
CASE_PAGES: tuple[tuple[str, str, str, str, str | None], ...] = (
    (
        "Puzzel-case: Andel Energi",
        "https://www.puzzel.com",
        "vendor_case",
        "https://www.puzzel.com/customers/andel-energi",
        "DK",
    ),
    (
        "Puzzel-case: Norlys",
        "https://www.puzzel.com",
        "vendor_case",
        "https://www.puzzel.com/customers/norlys",
        "DK",
    ),
    (
        "Puzzel-case: Aalborg Forsyning",
        "https://www.puzzel.com",
        "vendor_case",
        "https://www.puzzel.com/customers/aalborg-forsyning",
        "DK",
    ),
    (
        "NNIT-case: Norlys og AI i kundeservice",
        "https://nnit.com",
        "vendor_case",
        "https://nnit.com/our-solutions/data-and-ai/norlys-are-optimizing-the-customer-service-experience-using-artificial-intelligence",
        "DK",
    ),
    (
        "Kraken: Norlys vælger Kraken",
        "https://www.kraken.tech",
        "vendor_claim",
        "https://www.kraken.tech/press-releases/kraken-enters-nordics-with-norlys",
        "DK",
    ),
    (
        "Cognigy: Nuuday vælger AI-agenter",
        "https://www.cognigy.com",
        "vendor_claim",
        "https://www.cognigy.com/news/nuuday-selects-cognigy",
        "DK",
    ),
    (
        "Total Telecom: Nuuday-voicebotten Josefine",
        "https://totaltele.com",
        "media",
        "https://totaltele.com/nuuday-infuses-ai-into-customer-experience-with-the-avaya-onecloud-experience-platform/",
        "DK",
    ),
    (
        "KPMG-case: Alm. Brands ALBOT",
        "https://home.kpmg",
        "vendor_case",
        "https://home.kpmg/dk/en/home/services/case-stories/alm-brand-albot.html",
        "DK",
    ),
    (
        "Boye & Co: Trygs chatbots",
        "https://www.boye-co.com",
        "media",
        "https://www.boye-co.com/blog/2020/8/24/chatbots-during-covid19-at-danish-insurance-firm-tryg",
        "DK",
    ),
    (
        "Genesys-case: 3 Danmark",
        "https://www.casestudies.com",
        "vendor_case",
        "https://www.casestudies.com/company/genesys/case-study/3-denmark-boosts-productivity-10-and-cuts-handle-times-20-with-genesys",
        "DK",
    ),
    (
        "Puzzel køber Capturi (samtaleanalyse)",
        "https://techsavvy.media",
        "media",
        "https://techsavvy.media/en/leading-platform-acquires-aarhus-based-startup-to-boost-ai-powered-customer-service-in-europe/",
        "DK",
    ),
    (
        "CustomerThink: Capturi om samtaleanalyse på nordiske sprog",
        "https://customerthink.com",
        "media",
        "https://customerthink.com/the-challenge-with-conversational-analysis-in-the-nordics-interview-with-tue-martin-berg-of-capturi/",
        "DK",
    ),
    (
        "KU: SupWiz og AI-drevet kundesupport",
        "https://science.ku.dk",
        "research",
        "https://science.ku.dk/ai-centre/news/danish-researchers-behind-ai-driven-customer-support-in-a-class-of-its-own/",
        "DK",
    ),
    (
        "DI: AI-case Solar",
        "https://www.danskindustri.dk",
        "media",
        "https://www.danskindustri.dk/vi-radgiver-dig/virksomhedsregler-og-varktojer/ai/cases-og-eksempler/casearkiv-ai-for-alle/Solar/",
        "DK",
    ),
    (
        "DI: AI-case Group Online (Capturi)",
        "https://www.danskindustri.dk",
        "media",
        "https://www.danskindustri.dk/vi-radgiver-dig/virksomhedsregler-og-varktojer/ai/cases-og-eksempler/casearkiv-ai-for-alle/use-case-group-online/",
        "DK",
    ),
    (
        "TechCrunch: Zendesks AI-agent",
        "https://techcrunch.com",
        "media",
        "https://techcrunch.com/2025/10/08/zendesk-says-its-new-ai-agent-can-solve-80-of-support-issues",
        None,
    ),
)


def _ensure_pack(
    connection: Connection,
    *,
    marker: str,
    pack: tuple[tuple[str, str, str, str, str | None], ...],
    retrieval_method: str,
    frequency: str,
) -> bool:
    """Indsæt en kildepakke én gang. False, hvis den allerede er indsat."""
    seeded = connection.execute(
        text("select 1 from sources where notes like :marker limit 1"),
        {"marker": f"{marker}%"},
    ).first()
    if seeded is not None:
        return False
    for name, base_url, source_type, endpoint_url, country_code in pack:
        connection.execute(
            text(
                "insert into sources (name, base_url, source_type, retrieval_method, "
                "endpoint_url, country_code, frequency, access_class, active, next_check_at, "
                "notes) select :name, :base_url, cast(:source_type as source_type), "
                "cast(:retrieval_method as retrieval_method), :endpoint_url, :country_code, "
                "cast(:frequency as source_frequency), 'public'::access_class, true, now(), "
                ":marker where not exists "
                "(select 1 from sources s where s.endpoint_url = :endpoint_url)"
            ),
            {
                "name": name,
                "base_url": base_url,
                "source_type": source_type,
                "retrieval_method": retrieval_method,
                "endpoint_url": endpoint_url,
                "country_code": country_code,
                "frequency": frequency,
                "marker": marker,
            },
        )
    logger.info("source_pack_seeded marker=%s count=%d", marker, len(pack))
    return True


def _ensure_source_pack(connection: Connection) -> None:
    if _ensure_pack(
        connection,
        marker=SOURCE_PACK_MARKER,
        pack=SOURCE_PACK,
        retrieval_method="rss",
        frequency="weekly",
    ):
        connection.execute(
            text(
                "update sources set active = false, notes = coalesce(notes || ' · ', '') || "
                "'Pauset 2026-10: ikke kundecenter-relevant' "
                "where active and endpoint_url ilike '%aws.amazon.com%'"
            )
        )
    _ensure_pack(
        connection,
        marker=CASE_PAGES_MARKER,
        pack=CASE_PAGES,
        retrieval_method="web_fetch",
        frequency="monthly",
    )


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
