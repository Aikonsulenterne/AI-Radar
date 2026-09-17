-- Slice 2: entities, claims og evidens (Technical Master §5, §6).

create type entity_type as enum ('company', 'technology', 'vendor');

create type claim_type as enum (
  'adoption',
  'use_case',
  'stage',
  'technology_vendor',
  'effect',
  'negative',
  'organization'
);

create type claim_predicate as enum (
  'USES_CAPABILITY',
  'USES_FOR',
  'ADOPTION_STAGE',
  'USES_TECHNOLOGY',
  'USES_VENDOR',
  'REPORTED_EFFECT',
  'REPORTS_BARRIER',
  'REPORTS_NEGATIVE_OUTCOME',
  'ABANDONED_OR_REPLACED',
  'USES_GOVERNANCE_MODEL',
  'USES_HUMAN_REVIEW',
  'REPORTS_ADOPTION_APPROACH',
  'REPORTS_DATA_FOUNDATION'
);

create type review_status as enum (
  'proposed',
  'approved',
  'approved_with_edits',
  'needs_corroboration',
  'rejected'
);

create type claim_lifecycle as enum ('current', 'contradicted', 'superseded', 'expired');

create type claim_created_by as enum ('ai', 'human');

create type evidence_relationship as enum ('supports', 'contradicts', 'supersedes');

create type tech_horizon as enum ('now', 'next', 'horizon');

-- country_code er nullable som bevidst afvigelse fra masterens "not null":
-- entity resolution må ikke opfinde et land, når kilden ikke nævner det
-- (Product Master: manglende data vises som manglende). Dokumenteret i
-- docs/03_Implementation_Notes.md.
create table companies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text unique not null,
  country_code text null,
  industry text null,
  website_url text null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger companies_set_updated_at
  before update on companies
  for each row execute function public.set_updated_at();

create table entity_aliases (
  id uuid primary key default gen_random_uuid(),
  entity_type entity_type not null,
  entity_id uuid not null,
  alias text not null,
  normalized_alias text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_entity_aliases_type_normalized unique (entity_type, normalized_alias)
);

create index idx_entity_aliases_entity on entity_aliases (entity_type, entity_id);

create trigger entity_aliases_set_updated_at
  before update on entity_aliases
  for each row execute function public.set_updated_at();

create table technologies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text unique not null,
  definition text not null,
  horizon tech_horizon not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger technologies_set_updated_at
  before update on technologies
  for each row execute function public.set_updated_at();

create table vendors (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  website_url text null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger vendors_set_updated_at
  before update on vendors
  for each row execute function public.set_updated_at();

-- Et claim indeholder ét faktuelt udsagn. Ukendte værdier forbliver null.
create table claims (
  id uuid primary key default gen_random_uuid(),
  claim_type claim_type not null,
  subject_entity_type entity_type not null,
  subject_entity_id uuid not null,
  predicate claim_predicate not null,
  object_entity_type entity_type null,
  object_entity_id uuid null,
  object_text text null,
  normalized_value jsonb null,
  valid_from date null,
  valid_to date null,
  observed_at timestamptz not null,
  review_status review_status not null default 'proposed',
  lifecycle_status claim_lifecycle not null default 'current',
  created_by claim_created_by not null,
  reviewed_by_user_id uuid null,
  reviewed_at timestamptz null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_claims_subject on claims (subject_entity_type, subject_entity_id);
create index idx_claims_review_status on claims (review_status);

create trigger claims_set_updated_at
  before update on claims
  for each row execute function public.set_updated_at();

-- Uddraget skal være tilstrækkeligt til, at en reviewer kan vurdere claimet
-- uden at stole på AI-resuméet (Technical Master §5).
create table claim_evidence (
  id uuid primary key default gen_random_uuid(),
  claim_id uuid not null references claims (id),
  document_id uuid not null references documents (id),
  supporting_excerpt text not null,
  excerpt_start integer null,
  excerpt_end integer null,
  relationship evidence_relationship not null default 'supports',
  source_type_snapshot source_type null,
  independent_origin_key text null,
  review_status review_status not null default 'proposed',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_claim_evidence_claim on claim_evidence (claim_id);
create index idx_claim_evidence_document on claim_evidence (document_id);

create trigger claim_evidence_set_updated_at
  before update on claim_evidence
  for each row execute function public.set_updated_at();

-- RLS: samme princip som Slice 1 — deny-all; al adgang via API'et.
alter table companies enable row level security;
alter table entity_aliases enable row level security;
alter table technologies enable row level security;
alter table vendors enable row level security;
alter table claims enable row level security;
alter table claim_evidence enable row level security;
