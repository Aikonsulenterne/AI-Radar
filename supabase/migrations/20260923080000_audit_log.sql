-- Audit-log (Technical Master §18: "Auditér ændringer i review, sources og
-- opportunities"). Rækkerne er append-only historik: hvem gjorde hvad hvornår,
-- og hvilke felter der ændrede sig. Tabellen gør produktkvalitetsmålene fra
-- §18 målbare — f.eks. rettelser før godkendelse.
--
-- entity_type og action er text frem for enum: nye handlinger skal kunne
-- tilføjes uden en migration, og værdierne valideres i applikationslaget.
-- changes rummer aldrig secrets eller fulde dokumenttekster — kun de
-- ændrede felters før/efter-værdier.

-- id er en stigende sekvens frem for en uuid: occurred_at er transaktionens
-- starttidspunkt og er derfor ens for flere rækker i samme request, så det er
-- id'et, der giver rækkefølgen inden for et sekund.
create table audit_log (
  id bigint generated always as identity primary key,
  occurred_at timestamptz not null default now(),
  actor_user_id uuid,
  entity_type text not null,
  entity_id uuid not null,
  action text not null,
  changes jsonb,
  request_id text
);

create index ix_audit_log_entity on audit_log (entity_type, entity_id, occurred_at desc);
create index ix_audit_log_occurred_at on audit_log (occurred_at desc);

-- Som resten af skemaet: deny-all: al læsning går gennem API'et, der
-- håndhæver Admin-rollen eksplicit.
alter table audit_log enable row level security;
