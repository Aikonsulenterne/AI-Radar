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
import os

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
    # Beslutningsoplæggets indstillinger (20261012090000_app_settings.sql).
    "create table if not exists app_settings ( key text primary key, value jsonb not null, "
    "updated_at timestamptz not null default now(), updated_by_user_id uuid null )",
    "alter table app_settings enable row level security",
    # Den forenklede radar (20261013090000_market_items.sql).
    "alter table documents add column if not exists market_extracted_at timestamptz null",
    "alter table documents add column if not exists market_relevant boolean null",
    "create table if not exists market_items ( id uuid primary key default gen_random_uuid(), "
    "kind text not null check (kind in ('technology', 'case')), document_id uuid not null "
    "references documents (id) on delete cascade, technology_id uuid null references "
    "technologies (id), company_id uuid null references companies (id), vendor_company_id "
    "uuid null references companies (id), areas jsonb not null default '[]'::jsonb, data "
    "jsonb not null default '{}'::jsonb, quote text not null, prompt_version text not null, "
    "observed_at timestamptz not null, hidden boolean not null default false, hidden_at "
    "timestamptz null, hidden_by_user_id uuid null, created_at timestamptz not null default "
    "now() )",
    "create index if not exists ix_market_items_kind on market_items (kind)",
    "create index if not exists ix_market_items_document on market_items (document_id)",
    "create index if not exists ix_market_items_technology on market_items (technology_id)",
    "alter table market_items enable row level security",
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


# Salg- og support-kildepakken (2026-10-13): radaren er til direktøren for
# Salg, Kundeservice og Support. Indsat én gang som kundecenter-pakken.
SALES_PACK_MARKER = "Salg- og support-kildepakke 2026-10"
SALES_PACK: tuple[tuple[str, str, str, str, str | None], ...] = (
    (
        "Bing News: AI salg og kundeservice",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=AI+salg+kundeservice&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: kunstig intelligens kundesupport",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%22kunstig+intelligens%22+kundesupport&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: danske energi- og teleselskaber og AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%28Norlys+OR+Andel+OR+%C3%98rsted+OR+Vattenfall+OR+TDC+OR+Telenor+OR+Telia%29+AI+kundeservice&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: AI sales assistant",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%22AI+sales+assistant%22+OR+%22sales+copilot%22&format=rss",
        None,
    ),
    (
        "Bing News: conversation intelligence sales",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%22conversation+intelligence%22+sales+AI&format=rss",
        None,
    ),
    (
        "Bing News: AI upsell customer service",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=AI+%22next+best+offer%22+OR+upsell+%22customer+service%22&format=rss",
        None,
    ),
    (
        "Bing News: AI churn prediction utilities telecom",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=AI+churn+prediction+utility+OR+telecom+OR+energy&format=rss",
        None,
    ),
    (
        "Bing News: AI customer support automation",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%22customer+support%22+AI+automation+launches&format=rss",
        None,
    ),
)


# Case-kildepakken (2026-10-14): danske og nordiske cases, brancher som OK og
# OK's nuværende leverandør (FocalScope). Indsat én gang som de andre pakker.
CASES_PACK_MARKER = "Case-kildepakke 2026-10"
CASES_PACK: tuple[tuple[str, str, str, str, str | None], ...] = (
    (
        "Bing News: FocalScope AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=FocalScope+AI&format=rss",
        None,
    ),
    (
        "Bing News: FocalScope",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=FocalScope&format=rss",
        None,
    ),
    (
        "Bing News: kundecase AI kundeservice",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=kundecase+AI+kundeservice&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: voicebot kundeservice",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=voicebot+kundeservice&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: AI-agent kundeservice",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%22AI-agent%22+kundeservice&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: energiselskab kundeservice AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%28energiselskab+OR+forsyning+OR+elselskab%29+kundeservice+AI&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: teleselskab kundeservice AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%28teleselskab+OR+TDC+OR+Telenor+OR+Telia+OR+Nuuday%29+kundeservice+AI&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: forsikring og bank kundeservice AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%28forsikring+OR+bank%29+kundeservice+%22kunstig+intelligens%22&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: Dansk Erhverv og DI om AI i kundeservice",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%28%22Dansk+Erhverv%22+OR+%22Dansk+Industri%22%29+kundeservice+AI&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: CX-konferencer i Norden",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%28%22CX+Nordic%22+OR+Kundeservicedagen+OR+%22Customer+Service+Day%22%29+AI&format=rss",
        None,
    ),
    (
        "Bing News: Sverige: AI i kundtjänst",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=AI+kundtj%C3%A4nst&format=rss",
        None,
    ),
    (
        "Bing News: Norge: KI i kundeservice",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%22kunstig+intelligens%22+OR+KI+kundeservice+Norge&format=rss",
        None,
    ),
    (
        "Bing News: Finland: tekoäly asiakaspalvelu",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=teko%C3%A4ly+asiakaspalvelu&format=rss",
        None,
    ),
    (
        "Bing News: Utilities: AI customer service case",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=utility+OR+energy+%22customer+service%22+AI+%22case+study%22&format=rss",
        None,
    ),
    (
        "Bing News: Contact center AI results",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%22contact+center%22+AI+reduced+%22handling+time%22+OR+%22wait+times%22&format=rss",
        None,
    ),
    (
        "Bing News: Puzzel og Boost.ai kundecases",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%28Puzzel+OR+%22Boost.ai%22%29+customer+AI&format=rss",
        None,
    ),
)


# Dem, der ligner OK (catalog.PEERS): deres AI-cases står øverst under
# Sådan gør andre. Kun offentlige nyhedskilder.
PEERS_PACK_MARKER = "Konkurrent-kildepakke 2026-10"
PEERS_PACK: tuple[tuple[str, str, str, str, str | None], ...] = (
    (
        "Bing News: Norlys og AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=Norlys+%28AI+OR+%22kunstig+intelligens%22%29&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: Andel Energi og AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%22Andel+Energi%22+%28AI+OR+%22kunstig+intelligens%22%29&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: Ørsted kundeservice og AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%C3%98rsted+kundeservice+%28AI+OR+%22kunstig+intelligens%22%29&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: Energi Fyn, EWII og Vattenfall og AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%28%22Energi+Fyn%22+OR+EWII+OR+Vattenfall%29+%28AI+OR+%22kunstig+intelligens%22%29&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: Circle K, Q8, Shell, Uno-X og Clever og AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%28%22Circle+K%22+OR+Q8+OR+Shell+OR+%22Uno-X%22+OR+Clever%29+%28AI+OR+%22kunstig+intelligens%22%29+kunder&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: TDC, YouSee og Nuuday og AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%28TDC+OR+YouSee+OR+Nuuday%29+%28AI+OR+%22kunstig+intelligens%22%29&format=rss&setlang=da&cc=DK",
        "DK",
    ),
    (
        "Bing News: Telenor, Telia og 3 kundeservice og AI",
        "https://www.bing.com/news",
        "media",
        "https://www.bing.com/news/search?q=%28Telenor+OR+Telia+OR+%223+Danmark%22%29+kundeservice+%28AI+OR+%22kunstig+intelligens%22%29&format=rss&setlang=da&cc=DK",
        "DK",
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
    _ensure_pack(
        connection,
        marker=SALES_PACK_MARKER,
        pack=SALES_PACK,
        retrieval_method="rss",
        frequency="weekly",
    )
    _ensure_pack(
        connection,
        marker=CASES_PACK_MARKER,
        pack=CASES_PACK,
        retrieval_method="rss",
        frequency="weekly",
    )
    _ensure_pack(
        connection,
        marker=PEERS_PACK_MARKER,
        pack=PEERS_PACK,
        retrieval_method="rss",
        frequency="weekly",
    )


# Fejl fra seneste opstart (vises i /health, så de kan ses uden Render-loggen).
LAST_ERRORS: list[str] = []
# Status for keepalive-jobbet; vises i /health?schema=true.
KEEPALIVE_STATUS = "ikke tjekket"

# Render free tier sover efter 15 minutter uden trafik, og første klik tager
# så 30-50 sekunder. pg_cron pinger API'et hvert 10. minut på hverdage
# 05-19 UTC (06/07-20/21 dansk tid) — ca. 330 af free tiers 750 timer.
KEEPALIVE_JOB = "ai-radar-keepalive"
KEEPALIVE_SCHEDULE = "*/10 5-19 * * 1-5"


def _ensure_keepalive(connection: Connection) -> str:
    """Planlæg keepalive-pinget, når API'et kører på Render og databasen har
    pg_cron og pg_net (Supabase). Idempotent: cron.schedule med samme navn
    opdaterer jobbet. Opretter aldrig selv extensions."""
    base_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not base_url:
        return "ikke aktiv (kører ikke på Render)"
    installed = set(
        connection.execute(
            text("select extname from pg_extension where extname in ('pg_cron', 'pg_net')")
        ).scalars()
    )
    if installed != {"pg_cron", "pg_net"}:
        return "ikke aktiv (pg_cron/pg_net er ikke slået til)"
    command = (
        "select net.http_get(url := "
        + connection.execute(
            text("select quote_literal(:url)"), {"url": f"{base_url}/api/v1/health"}
        ).scalar_one()
        + ", timeout_milliseconds := 60000)"
    )
    connection.execute(
        text("select cron.schedule(:name, :schedule, :command)"),
        {"name": KEEPALIVE_JOB, "schedule": KEEPALIVE_SCHEDULE, "command": command},
    )
    return f"aktiv ({KEEPALIVE_SCHEDULE} UTC)"


# Kolonner og enum-værdier, koden kræver. Bruges af /health.
_REQUIRED_COLUMNS = (
    ("documents", "market_extracted_at"),
    ("market_items", "quote"),
    ("technologies", "is_candidate"),
    ("technologies", "discovered_at"),
    ("documents", "vendor_extracted_at"),
    ("worker_runs", "documents_reread"),
    ("app_settings", "value"),
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
            global KEEPALIVE_STATUS
            try:
                KEEPALIVE_STATUS = _ensure_keepalive(connection)
            except Exception as exc:  # noqa: BLE001
                KEEPALIVE_STATUS = "fejlede"
                LAST_ERRORS.append(_short(exc))
                logger.error("keepalive_failed error=%s", _short(exc))
    except Exception as exc:  # noqa: BLE001 — fx ingen forbindelse ved opstart
        LAST_ERRORS.append(_short(exc))
        logger.error("schema_guard_unavailable error=%s", _short(exc))
        return
    logger.info("schema_guard_done errors=%d", len(LAST_ERRORS))
