-- Leverandørlandskab (produktejerbeslutning 2026-10-08): radaren skal vise,
-- hvilke leverandører der tilbyder hvilken AI-capability til kundecentre.
-- Et tilbud er et claim "<leverandør> OFFERS_CAPABILITY <capability>" med
-- leverandøren som subjekt og produktnavnet som objekttekst.

alter type claim_predicate add value if not exists 'OFFERS_CAPABILITY';

-- Selvbetjening via chat-/voicebots manglede i den kuraterede liste.
with inserted as (
  insert into technologies (name, slug, definition, horizon)
  values (
    'Virtual Agent',
    'virtual-agent',
    'Chat- og voicebots, der selv besvarer og løser kundehenvendelser (selvbetjening).',
    'now'
  )
  on conflict (slug) do nothing
  returning id, name
)
insert into entity_aliases (entity_type, entity_id, alias, normalized_alias)
select 'technology'::entity_type, id, name, lower(name) from inserted
on conflict (entity_type, normalized_alias) do nothing;

-- Nye capabilities i markedet: et tilbud (eller en anvendelse) med en
-- capability, der ikke findes på den kuraterede liste, opretter en
-- kandidat-teknologi. Den er ikke placeret i en horisont, før en Admin
-- optager den på radaren.
alter table technologies add column if not exists is_candidate boolean not null default false;
alter table technologies add column if not exists discovered_at timestamptz null;
alter table technologies alter column horizon drop not null;
