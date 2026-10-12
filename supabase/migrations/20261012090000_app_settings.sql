-- Redigerbare indstillinger, fx beslutningsoplæggets OK-tal (2026-10-12).
-- Én række pr. nøgle med en JSON-værdi, som API'et validerer.

create table if not exists app_settings (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now(),
  updated_by_user_id uuid null
);

alter table app_settings enable row level security;
