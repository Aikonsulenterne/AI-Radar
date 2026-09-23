-- Dubletter og konflikter mellem claims (Technical Master §15; Product
-- Master §: Review Queue-handlingerne "Merge duplicate candidate" og
-- "Mark possible contradiction").
--
-- Relationen er en selvstændig række frem for en kolonne på claims, fordi
-- masteren kræver, at gamle claims ikke overskrives: begge claims består,
-- og relationen bærer revieweren og tidspunktet. AI må foreslå en mulig
-- dublet deterministisk; det er mennesket, der sætter den endelige relation.

create type claim_relation as enum ('supports', 'contradicts', 'supersedes');

create table claim_relations (
  id bigint generated always as identity primary key,
  claim_id uuid not null references claims (id),
  related_claim_id uuid not null references claims (id),
  relation claim_relation not null,
  created_by_user_id uuid,
  created_at timestamptz not null default now(),
  constraint claim_relations_not_self check (claim_id <> related_claim_id)
);

-- Ét par må kun have én relation ad gangen.
create unique index uq_claim_relations_pair on claim_relations (claim_id, related_claim_id);
create index ix_claim_relations_related on claim_relations (related_claim_id);

alter table claim_relations enable row level security;
