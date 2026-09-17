-- Slice 3: signaler (Technical Master §5; Product Master §7, §11).

create type documentation_level as enum ('strong', 'limited', 'early', 'conflicting');

create type signal_status as enum ('draft', 'published', 'archived');

create table signals (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  summary text not null,
  analysis text null,
  recommendation text null,
  documentation_level documentation_level not null,
  status signal_status not null default 'draft',
  published_at timestamptz null,
  created_by_user_id uuid null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_signals_status on signals (status);

create trigger signals_set_updated_at
  before update on signals
  for each row execute function public.set_updated_at();

-- Kun godkendte claims må være faktuelt grundlag for et publiceret signal;
-- håndhæves i API'et ved publicering. Virksomheder og teknologier afledes
-- af de tilknyttede claims (provenance frem for duplikeret kuratering).
create table signal_claims (
  signal_id uuid not null references signals (id),
  claim_id uuid not null references claims (id),
  created_at timestamptz not null default now(),
  primary key (signal_id, claim_id)
);

create index idx_signal_claims_claim on signal_claims (claim_id);

alter table signals enable row level security;
alter table signal_claims enable row level security;
