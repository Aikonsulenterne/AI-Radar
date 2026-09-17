-- Slice 4: adoption cases (Technical Master §5; Product Master §9).
-- Cases er præsentationsenheder — fakta ligger i claims.

create type case_status as enum ('draft', 'published', 'archived');

create table adoption_cases (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies (id),
  title text not null,
  summary text null,
  status case_status not null default 'draft',
  created_by_user_id uuid null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_adoption_cases_company on adoption_cases (company_id);
create index idx_adoption_cases_status on adoption_cases (status);

create trigger adoption_cases_set_updated_at
  before update on adoption_cases
  for each row execute function public.set_updated_at();

create table adoption_case_claims (
  case_id uuid not null references adoption_cases (id),
  claim_id uuid not null references claims (id),
  created_at timestamptz not null default now(),
  primary key (case_id, claim_id)
);

create index idx_adoption_case_claims_claim on adoption_case_claims (claim_id);

alter table adoption_cases enable row level security;
alter table adoption_case_claims enable row level security;
