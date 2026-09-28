-- Kørselslog for ingestion/AI-workeren. Hver kørsel — ugentlig (schedule),
-- "Kør nu" fra admin (manual) eller kommandolinjen (cli) — får én række,
-- så det kan ses, hvornår der sidst blev hentet, og hvad kørslen gav.
--
-- trigger og status er text frem for enum af samme grund som audit_log:
-- værdierne valideres i applikationslaget. error_message_safe rummer aldrig
-- secrets eller dokumenttekst.
create table worker_runs (
  id uuid primary key default gen_random_uuid(),
  trigger text not null,
  force_all boolean not null default false,
  status text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  started_by_user_id uuid,
  sources_checked integer not null default 0,
  documents_created integer not null default 0,
  documents_unchanged integer not null default 0,
  fetch_failures integer not null default 0,
  documents_processed integer not null default 0,
  processing_skipped_no_ai boolean not null default false,
  error_message_safe text
);

create index ix_worker_runs_started_at on worker_runs (started_at desc);

-- Deny-all som resten af skemaet: al adgang går gennem API'et.
alter table worker_runs enable row level security;
