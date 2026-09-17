# Implementeringsnoter — lokale valg pr. slice

Lokale implementeringsvalg jf. Technical Master §23: de ændrer ikke
produktadfærd, låst arkitektur, sikkerhed eller provenance. Ændres et valg
til noget væsentligt, opdateres masterfilerne i samme PR.

## Slice 0

- Web-shellen bruger midlertidige neutrale design tokens, fordi
  UI-prototypen og `colors_and_type.css` endnu ikke er i repoet. De skal
  erstattes af OK's tokens (burgundy, rød, varm cream, OKfamily/Fellix),
  når filerne og fontlicenserne foreligger.

## Slice 1 (Source → Document)

- **Fetch-metode:** `web_fetch` (simpel HTTP GET af `endpoint_url`) er den
  ene simple fetch-metode. `rss` findes i datamodellen, men `run` svarer
  409 `not_implemented`, indtil RSS-parsing tilføjes.
- **Kørsel i API-processen:** `POST /sources/{id}/run` og manuel upload
  kører synkront i API'et. Masterens API/worker-split fra samme codebase
  tages i brug, når planlagt/asynkron ingestion kommer (frekvensstyret).
- **Access class ved automatisk hentning:** kun `public` kilder hentes
  automatisk. `licensed`/`restricted` afvises med 409, indtil reglerne for
  tilladt snapshot-lagring (Technical Master §14) er operationaliseret.
- **Manuel upload-endpoint:** `POST /sources/{id}/documents` (multipart)
  supplerer masterens endpointliste; tilladte typer er text/plain,
  text/html og application/pdf med størrelsesgrænse.
- **Normalisering:** stdlib-HTML-parser (script/style udelades) og pypdf
  til PDF-tekst. Ukendte formater får `normalized_text = null` — der
  gættes ikke. Sprogdetektion er ikke implementeret (`language_code` null).
- **Auth:** HS256-validering af Supabase-JWT med `SUPABASE_JWT_SECRET`;
  roller slås op i `profiles`-tabellen (manglende profil = Reader).
  I `ENVIRONMENT=local` uden secret kører API'et med dev-bypass (Admin) af
  hensyn til lokal udvikling — aldrig i staging/production. Frontendens
  Supabase Auth-session/token-wiring kommer i en senere slice.
- **RLS:** aktiveret uden policies (deny-all) på profiles/sources/documents.
  Al adgang går gennem API'et, som håndhæver roller eksplicit; policies
  tilføjes, hvis direkte klientadgang nogensinde indføres.
- **Tests:** unit-/API-tests kører på SQLite in-memory (hurtige, ingen
  services); migrations valideres mod rigtig PostgreSQL 15 i CI's
  migrations-job. Integrationstests mod PostgreSQL/Storage-adapter udvides
  i takt med slices.
- **Storage:** adapter-interface med `local` (filsystem, udvikling/test)
  og `supabase` (REST mod private bucket, service-role key kun
  server-side). Signerede URLs udstedes kortvarigt; lokal adapter
  returnerer null.

## Slice 2 (Document → Claim → Review)

- **AI-kørsel:** `POST /review/documents/{id}/process` kører relevans og
  claim extraction synkront i API'et (endpointet supplerer masterens
  liste). Uden konfigureret AI-provider svarer det 503
  `ai_not_configured`. Planlagt/asynkron worker-kørsel kommer senere.
- **Evidens håndhæves mekanisk:** et claim kasseres, hvis
  `supporting_excerpt` ikke findes ordret i den normaliserede tekst;
  offsets beregnes server-side. Prompten forbyder at følge instruktioner
  i kildeteksten (untrusted data, Technical Master §9).
- **Schemafejl:** højst én kontrolleret retry; derefter
  `processing_status=failed` med `error_code=ai_schema_error` til manuel
  opfølgning.
- **Entity resolution er deterministisk:** kun exact/normaliseret
  alias- eller navnematch. Et umatchet virksomhedsnavn opretter en ny
  Company + alias (reviewer kan flette via duplicate-kandidater); et
  umatchet objekt forbliver `object_text`. Ingen fuzzy/AI-matching.
- **`companies.country_code` er nullable** (master siger not null):
  entity resolution må ikke opfinde et land, kilden ikke nævner —
  princippet "manglende data vises som manglende" vægtes over
  kolonnekravet. Land udfyldes ved kuratering.
- **Duplicate-kandidater** beregnes deterministisk (samme subjekt +
  predicate + objekt) og vises i review; revieweren afgør relationen.
  Automatisk konfliktafgørelse er fortsat ude af scope.
- **Approve-semantik:** `POST .../approve` uden edits → `approved`; med
  edits → `approved_with_edits`. `PATCH` retter et åbent claim uden at
  afgøre det. `complete` sætter dokumentet til `reviewed`, eller
  `partially_reviewed` hvis der stadig er `proposed` claims.
- **Seed:** de 8 startteknologier (Product Master §6) ligger i
  `supabase/seed.sql` med foreløbig horizon-kuratering, der skal
  valideres af produktejeren.

## Slice 3 (Published signal og Overblik)

- **Signal-authoring-endpoints** (`POST /signals`, `PATCH /signals/{id}`,
  `POST /signals/{id}/publish`) supplerer masterens read-endpoints:
  masteren definerer publiceringsflowet, men lister ikke endpoints til at
  oprette signaler. Reviewer/Admin kan oprette; publicering håndhæver, at
  alle tilknyttede claims er godkendte, og at der er mindst ét.
- **Relationer afledes af claims:** signal↔claims er eksplicit
  (signal_claims); virksomheder og teknologier på et signal afledes af de
  tilknyttede claims i stedet for separate junction-tabeller — provenance
  frem for dobbelt kuratering.
- **Readers ser kun published**; kladder og arkiverede signaler kræver
  Reviewer/Admin. `GET /signals/{id}` svarer 404 (ikke 403) for en kladde
  til en Reader, så eksistensen ikke afsløres.
- **Signal-detaljerute** `/signals/[signalId]` supplerer masterens
  frontend-ruteliste (route-baserede detaljer skal kunne deles og
  genindlæses, Product Master §12); admin-signalbyggeren ligger på
  `/admin/signals`.
- **Dashboardet** viser kun optællinger (ingen beregnede scores) med
  definition på hvert KPI-kort, jf. "kompakte KPI'er med kilde eller
  definition".

## Slice 4 (Adoption og Technology)

- **Case-authoring-endpoints** (`POST/PATCH /adoption-cases`,
  `/adoption-cases/{id}/publish`) supplerer masterens read-endpoints —
  samme mønster som signaler. Publicering kræver mindst ét claim, alle
  godkendte, og alle claims skal have casens virksomhed som subjekt.
- **Casens faktafelter afledes** (capability, use case, stadie, vendor,
  effekt) af de tilknyttede godkendte claims. Udokumenterede felter er
  null og vises som "Ikke dokumenteret" hhv. "Ingen dokumenteret effekt
  fundet" (Product Master §9). Casens `summary` er potentiel læring og
  vises som analyse.
- **Profiler viser kun reviewede fakta:** company-/teknologiprofiler
  viser godkendte claims og publicerede cases; readers ser aldrig
  kladder (404, ikke 403). Adoption på teknologiradaren er en optælling
  af virksomheder med godkendte claims — ingen momentum-/modenhedsscore
  uden evidens.
- **Filtre i MVP:** country_code og navnesøgning på companies;
  company_id/status på cases. Branche-/capability-/styrkefiltre udvides,
  når felterne reelt kurateres.
- **Admin-casebygger** på `/admin/cases` (supplerer masterens ruteliste
  ligesom `/admin/signals`).
- **Test-seed:** unit-testene seeder Agent Assist + alias i SQLite som
  spejl af supabase/seed.sql.

## Slice 5 (Opportunities)

- **Godkendelsesflow:** en opportunity uden `approved_by_user_id` er en
  kandidat. `POST /opportunities/{id}/approve` er den menneskelige
  godkendelse, og status kan først rykkes forbi `identified`, når den er
  givet (409 `not_approved` ellers). AI-genererede opportunity-forslag
  er ikke wiret endnu — mennesker opretter kandidater; når AI-forslag
  tilføjes, lander de som ugodkendte kandidater i samme flow.
- **`GET /problems`** (taxonomi-listen) og approve-endpointet supplerer
  masterens endpointliste.
- **Relationer:** junctions til signaler og claims; teknologier afledes
  af claims som i resten af produktet. Problem-taxonomien er seedet med
  Product Master §10's startliste.
- **Ejerfeltet** findes i API'et (PATCH owner_user_id), men UI'et sætter
  det ikke endnu — brugeradministration kommer med auth-wiring.

## Slice 6 (Briefing og hardening)

- **Briefingen** genereres i frontenden fra eksisterende endpoints
  (signaler, cases, opportunities) — intet separat subsystem, jf.
  Product Master §7. "Redigerbar visning" afventer en senere iteration.
- **Worker-entrypointet** (`python -m app.worker --once|--interval N`)
  kører fra samme image som API'et: henter forfaldne public
  web_fetch-kilder (frekvensstyret via next_check_at) og AI-behandler
  normaliserede dokumenter, når provider er konfigureret.
- **Observability:** request-logging-middleware med correlation id
  (X-Request-ID) og varighed; AI-kald logger prompt-id/version, model,
  latency og tokenforbrug. Tokens, secrets og dokumenttekster logges
  aldrig. Fuld OpenTelemetry-instrumentering er en senere hardening.
- **Evaluering:** `app/evaluation.py` + JSONL-datasætformat i
  `evaluation/`; metrikker for relevance/claim precision-recall og
  excerpt correctness. Datasættet skal opbygges manuelt (100–200 docs
  som modningsmål).
- **Tilgængelighed:** skip-link, landmarks, labels, fokus-styles og
  tekstlige statusser; fuld WCAG 2.1 AA-gennemgang udestår som
  hardening-opgave.
- **Deployment:** staging-/production-guide i `docs/04_Deployment.md`.

## UI-implementering (UI Master, docs/03)

- **Tokens er staged** i `apps/web/src/styles/tokens.css` præcis som UI
  Master §3; `globals.css` bygger alle komponentstyles på tokens (ingen
  neutrale placeholder-tokens tilbage, ingen rå hex uden token).
- **Layout:** `src/components/layout/{app-shell,sidebar,topbar}.tsx` —
  burgundy sidebar (248px, aktiv række med red-mid prik), 64px topbar
  med sidetitel, main med 1392px container og arIn-entry-animation
  (respekterer prefers-reduced-motion).
- **Semantiske mønstre (§8):** `.section-fact` (4px burgundy venstrekant),
  `.signal-analysis` (cream-cool + stiplet border, label "Analyse, ikke
  fakta"), `.signal-recommendation` (4px rød venstrekant). Horizon- og
  dokumentationsniveau-badges følger §9-farverne med tekstlabel.
- **Fonte:** OKfamily/Fellix er licenserede og ikke i repoet; appen
  bygger med de godkendte fallbacks (Georgia-serif / Inter-sans) og
  `public/fonts/README.md` beskriver forventede filnavne. next/font/local
  aktiveres, når filerne staged. **Pixel-fidelity accepteres først da.**
- **Udestående mod UI Master:** stakbaseret entity-drawer (detaljer er
  route-baserede sider, hvilket Technical Master §12 tillader),
  filterbar på adoption (land/branche/capability/status/styrke),
  two-pane review-layout, toasts, kompakt tablet-sidebar og
  `AI Radar.dc.html`-sammenligning (filen er ikke leveret).

## Udestående (kendte mangler mod masterne)

- Supabase Auth-wiring i frontenden (login, session-token på API-kald);
  API'et validerer allerede JWT + roller.
- RSS-hentemetoden (409 not_implemented indtil videre).
- OK's design tokens fra `colors_and_type.css` og UI-prototypen.
- Route-baserede drawers og udvidede filtre (branche, capability,
  dokumentationsstyrke) på adoption.
- OpenTelemetry-eksport, audit-log-tabeller og RLS-/authorization-tests
  mod rigtig PostgreSQL i CI (migrations valideres; adfærdstests kører
  på SQLite).
- AI-genererede opportunity-forslag (lander som ugodkendte kandidater).
