-- Nøgler, som en planlagt udløser kan starte kørsler med (X-Worker-Token).
-- Kun SHA-256-hashen gemmes; selve nøglen kendes kun af udløseren. Det gør
-- det muligt at planlægge kørsler fra databasen (supabase/ops/
-- weekly_trigger.sql) uden at sætte en miljøvariabel på API-hosten.
create table worker_trigger_keys (
  token_sha256 text primary key,
  note text,
  created_at timestamptz not null default now()
);

-- Deny-all som resten af skemaet: kun API'et (service-forbindelsen) læser.
alter table worker_trigger_keys enable row level security;
