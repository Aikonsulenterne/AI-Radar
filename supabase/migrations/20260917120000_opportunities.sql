-- Slice 5: problem-taxonomi og opportunities (Technical Master §5;
-- Product Master §10). Ekstern udvikling × dokumentation × relevant
-- OK-problem = opportunity-kandidat.

create type opportunity_status as enum (
  'identified',
  'investigating',
  'business_case',
  'pilot',
  'scaling',
  'closed'
);

create table problem_taxonomy (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text not null,
  area text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index uq_problem_taxonomy_name on problem_taxonomy (name);

create trigger problem_taxonomy_set_updated_at
  before update on problem_taxonomy
  for each row execute function public.set_updated_at();

create table opportunities (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  problem_id uuid not null references problem_taxonomy (id),
  relevance_hypothesis text not null,
  evidence_gaps text null,
  recommended_next_action text not null,
  status opportunity_status not null default 'identified',
  owner_user_id uuid null,
  created_by_user_id uuid null,
  -- AI kan foreslå; menneskelig godkendelse kræves for aktiv opportunity.
  approved_by_user_id uuid null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_opportunities_status on opportunities (status);
create index idx_opportunities_problem on opportunities (problem_id);

create trigger opportunities_set_updated_at
  before update on opportunities
  for each row execute function public.set_updated_at();

create table opportunity_signals (
  opportunity_id uuid not null references opportunities (id),
  signal_id uuid not null references signals (id),
  created_at timestamptz not null default now(),
  primary key (opportunity_id, signal_id)
);

create table opportunity_claims (
  opportunity_id uuid not null references opportunities (id),
  claim_id uuid not null references claims (id),
  created_at timestamptz not null default now(),
  primary key (opportunity_id, claim_id)
);

alter table problem_taxonomy enable row level security;
alter table opportunities enable row level security;
alter table opportunity_signals enable row level security;
alter table opportunity_claims enable row level security;
