-- Seed-data for lokal udvikling og staging.
-- Regler (Product Master §14): al seed-/demodata markeres is_demo og må
-- aldrig publiceres som production intelligence. Ingen production-data i tests.

-- Startteknologier (Product Master §6) — kurateret taxonomi, ikke facts.
-- Horizon-placeringen er en foreløbig kuratering til lokal udvikling og skal
-- valideres af produktejeren.
with tech (name, slug, definition, horizon) as (
  values
    ('Agent Assist', 'agent-assist',
     'AI-støtte til medarbejdere under kundekontakt, fx svarforslag og opslag.',
     'now'::tech_horizon),
    ('Knowledge AI', 'knowledge-ai',
     'AI-drevet søgning og svar på tværs af intern viden og dokumentation.',
     'now'::tech_horizon),
    ('Conversation Intelligence', 'conversation-intelligence',
     'Analyse af samtaler for emner, årsager og kvalitet.',
     'now'::tech_horizon),
    ('Automated QA', 'automated-qa',
     'Automatiseret kvalitetsvurdering af kundeinteraktioner.',
     'next'::tech_horizon),
    ('Voice AI', 'voice-ai',
     'Tale-baseret AI: transskription, taleassistenter og talebots.',
     'next'::tech_horizon),
    ('Knowledge-gap Detection', 'knowledge-gap-detection',
     'Identifikation af huller i vidensgrundlag ud fra henvendelser.',
     'next'::tech_horizon),
    ('Workflow Automation', 'workflow-automation',
     'Automatisering af arbejdsgange med regler og AI-komponenter.',
     'now'::tech_horizon),
    ('Agentic AI', 'agentic-ai',
     'AI-systemer der udfører flertrinsopgaver med værktøjer under opsyn.',
     'horizon'::tech_horizon)
),
inserted as (
  insert into technologies (name, slug, definition, horizon)
  select name, slug, definition, horizon from tech
  on conflict (slug) do nothing
  returning id, name
)
insert into entity_aliases (entity_type, entity_id, alias, normalized_alias)
select 'technology'::entity_type, id, name, lower(name) from inserted
on conflict (entity_type, normalized_alias) do nothing;

-- Problem-taxonomi for OK Kundecenter (Product Master §10) — startliste,
-- der kan udvides gennem kuratering.
insert into problem_taxonomy (name, description, area)
values
  ('Manuel QA', 'Kvalitetssikring af kundeinteraktioner foregår manuelt.', 'Kundecenter'),
  ('Store mailmængder', 'Høj volumen af indgående mails belaster behandlingen.', 'Kundecenter'),
  ('Knowledge gaps', 'Medarbejdere mangler hurtig adgang til korrekt viden.', 'Kundecenter'),
  ('Efterbehandling', 'Tid brugt på opsummering og registrering efter kontakt.', 'Kundecenter'),
  ('Genhenvendelser', 'Kunder vender tilbage, fordi første kontakt ikke løste problemet.', 'Kundecenter'),
  ('Routing', 'Henvendelser lander i forkerte køer og kræver overdragelse.', 'Kundecenter'),
  ('Onboarding', 'Oplæring af nye medarbejdere tager lang tid.', 'Kundecenter'),
  ('Repetitive henvendelser', 'Samme simple henvendelsestyper gentages i stort antal.', 'Kundecenter')
on conflict (name) do nothing;
