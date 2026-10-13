-- Forenklet radar til direktøren for Salg, Kundeservice og Support
-- (2026-10-13). Ét AI-udtræk pr. artikel giver to slags fund:
--   technology: en leverandør sælger en AI-teknologi
--   case:       en navngiven virksomhed bruger AI i salg, kundeservice eller support
-- Hvert fund har et ordret citat fra dokumentet (dokument → kilde er sporbart).
-- Konsulenten kan skjule et forkert fund; intet slettes.

alter table documents add column if not exists market_extracted_at timestamptz null;
alter table documents add column if not exists market_relevant boolean null;

create table if not exists market_items ( id uuid primary key default gen_random_uuid(), kind text not null check (kind in ('technology', 'case')), document_id uuid not null references documents (id) on delete cascade, technology_id uuid null references technologies (id), company_id uuid null references companies (id), vendor_company_id uuid null references companies (id), areas jsonb not null default '[]'::jsonb, data jsonb not null default '{}'::jsonb, quote text not null, prompt_version text not null, observed_at timestamptz not null, hidden boolean not null default false, hidden_at timestamptz null, hidden_by_user_id uuid null, created_at timestamptz not null default now() );

create index if not exists ix_market_items_kind on market_items (kind);
create index if not exists ix_market_items_document on market_items (document_id);
create index if not exists ix_market_items_technology on market_items (technology_id);

-- Deny-all som resten af skemaet: al adgang går via API'et.
alter table market_items enable row level security;
