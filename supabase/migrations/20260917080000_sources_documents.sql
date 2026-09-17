-- Slice 1: Source Registry, Document og rollemodel (Technical Master §5, §7, §8).
-- Standard PostgreSQL; ingen Supabase-specifik adfærd i domænelaget.

create type source_type as enum (
  'primary',
  'independent_analysis',
  'vendor_case',
  'vendor_claim',
  'media',
  'research',
  'early_signal'
);

create type retrieval_method as enum ('rss', 'web_fetch', 'manual_upload');

create type source_frequency as enum ('manual', 'daily', 'weekly', 'monthly');

create type access_class as enum ('public', 'licensed', 'restricted');

create type processing_status as enum (
  'discovered',
  'fetched',
  'normalized',
  'classified_relevant',
  'classified_irrelevant',
  'extraction_pending',
  'review_pending',
  'partially_reviewed',
  'reviewed',
  'failed'
);

create type user_role as enum ('reader', 'reviewer', 'admin');

-- Roller lagres i en kontrolleret profil/role-model, ikke i brugerredigerbare
-- metadata (Technical Master §7). user_id er Supabase Auth-brugerens id; ingen
-- FK til auth.users af portabilitetshensyn (skal kunne flyttes til standard PG).
create table profiles (
  user_id uuid primary key,
  role user_role not null default 'reader',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger profiles_set_updated_at
  before update on profiles
  for each row execute function public.set_updated_at();

create table sources (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  base_url text null,
  source_type source_type not null,
  retrieval_method retrieval_method not null,
  endpoint_url text null,
  country_code text null,
  frequency source_frequency not null default 'manual',
  access_class access_class not null,
  active boolean not null default true,
  last_checked_at timestamptz null,
  next_check_at timestamptz null,
  owner_user_id uuid null,
  notes text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_sources_active on sources (active);

create trigger sources_set_updated_at
  before update on sources
  for each row execute function public.set_updated_at();

create table documents (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references sources (id),
  canonical_url text null,
  title text null,
  language_code text null,
  published_at timestamptz null,
  retrieved_at timestamptz not null,
  content_hash text not null,
  raw_storage_path text null,
  normalized_text text null,
  mime_type text null,
  processing_status processing_status not null,
  is_demo boolean not null default false,
  error_code text null,
  error_message_safe text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  -- Idempotency: source_id + content_hash (Technical Master §5).
  constraint uq_documents_source_content_hash unique (source_id, content_hash)
);

create index idx_documents_source_id on documents (source_id);
create index idx_documents_processing_status on documents (processing_status);

create trigger documents_set_updated_at
  before update on documents
  for each row execute function public.set_updated_at();

-- RLS: al adgang går gennem FastAPI med eksplicit server-side authorization;
-- frontend har ingen direkte databaseadgang. RLS aktiveres uden policies
-- (deny-all for anon/authenticated); backendens server-credential håndhæver
-- selv brugerens authorization (Technical Master §7).
alter table profiles enable row level security;
alter table sources enable row level security;
alter table documents enable row level security;
