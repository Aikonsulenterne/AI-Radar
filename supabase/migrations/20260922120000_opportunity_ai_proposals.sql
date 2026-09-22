-- AI-foreslåede opportunity-kandidater (Product Master §10, Technical Master §10).
--
-- Et forslag er ikke et menneskeligt kurateret input: det skal kunne skelnes
-- i brugerfladen, og det skal kunne spores, hvilken promptversion der lavede
-- det. Godkendelsesflowet er uændret — approved_by_user_id er fortsat den
-- menneskelige godkendelse, som status ikke kan rykkes uden.

alter table opportunities
  add column proposed_by_ai boolean not null default false,
  add column proposal_prompt_version text;

comment on column opportunities.proposed_by_ai is
  'Kandidaten er foreslået af AI og afventer menneskelig godkendelse.';
comment on column opportunities.proposal_prompt_version is
  'Promptversion bag AI-forslaget; null for menneskeskabte kandidater.';
