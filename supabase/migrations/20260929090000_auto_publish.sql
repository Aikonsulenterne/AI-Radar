-- Fuldt automatisk publicering (besluttet 2026-09-29, erstatter human-in-the-
-- loop for claims, cases og signaler — se docs/05_Implementation_Notes.md).
-- auto_published markerer det, AI har godkendt og publiceret uden menneskelig
-- kontrol, så UI'et altid kan vise det, og så det kan findes og efterprøves.
alter table signals add column auto_published boolean not null default false;
alter table adoption_cases add column auto_published boolean not null default false;
alter table claims add column auto_approved boolean not null default false;

-- Kørselsloggen tæller dokumenter publiceret automatisk.
alter table worker_runs add column documents_published integer not null default 0;
