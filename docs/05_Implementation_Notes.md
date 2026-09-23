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

- **Fetch-metoder:** `web_fetch` er en simpel HTTP GET af `endpoint_url`.
  `rss` henter feedet, parser RSS 2.0 og Atom med stdlib (ingen ny
  afhængighed) og henter hvert entrys artikellink som sit eget dokument;
  entryets titel og `pubDate`/`published` bruges som dokumentets titel og
  `published_at`. Andre feedformater afvises (`feed_invalid`) frem for at
  gætte. `rss_max_items` (default 20) afgrænser én kørsel.
- **Feedet er untrusted data:** et feed med DTD afvises før parsing
  (entity-expansion mod stdlib-parseren), og hvert entry-link valideres med
  `ensure_public_http_url` — kun http/https, og adresseliteraler i
  loopback-/private/link-local-intervaller afvises, så en kilde ikke kan få
  serveren til at hente interne adresser. Et DNS-navn, der peger på en
  intern adresse, fanges ikke; det samme gælder redirects undervejs.
- **Kørselsresultatet er en liste:** `RunResult` rummer flere dokumenter
  (RSS) eller ét (web_fetch) plus `failures`. Fejl på feed-niveau afbryder
  kørslen; fejl på et enkelt artikellink samles op, så resten af feedet
  stadig hentes. `app/ingestion/run.py` deles af endpointet og workeren.
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
- **Tests kører mod to databaser.** Lokalt og i API-jobbet kører suiten på
  SQLite in-memory (hurtig, ingen services). CI's database-job kører
  derefter migrations mod PostgreSQL 15 og hele suiten igen mod det
  migrerede skema via `TEST_DATABASE_URL` — hver test starter med en
  truncate af alle tabeller. Den kørsel er nødvendig, fordi SQLite-skemaet
  bygges af ORM-modellerne selv og derfor aldrig kan afsløre, at en
  model og en migration er uenige. `test_schema_drift.py` sammenligner
  desuden hver ORM-tabel og -kolonne (eksistens og nullable) med det
  migrerede skema, så også stier uden egne tests er dækket; den springes
  over på SQLite.
- **Lokal PostgreSQL-kørsel:** kør migrations mod en tom database og
  `TEST_DATABASE_URL=postgresql+psycopg://…/postgres uv run pytest`.
  Suiten truncater alle tabeller, så brug aldrig et miljø med rigtige data.
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
  predicate + objekt) og vises i review med indhold, så relationen kan
  vurderes uden et ekstra opslag. Revieweren sætter den endelige relation
  via `POST /review/claims/{id}/relate` (supports/contradicts/supersedes),
  som gemmes i `claim_relations` med aktør og tidspunkt. Ingen af de to
  claims slettes eller overskrives (Technical Master §15): "supersedes"
  markerer det relaterede claim `superseded`, og "contradicts" markerer
  begge `contradicted` uden at afgøre hvilket der er rigtigt. Automatisk
  konfliktafgørelse er fortsat ude af scope. `lifecycle_status` er indtil
  videre informativ — publicering filtrerer på `review_status`, så en
  markering fjerner ikke i sig selv et claim fra et publiceret signal.
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
  givet (409 `not_approved` ellers).
- **AI-forslag** (`POST /opportunities/propose`, prompt
  `opportunity_proposal` 1.0.0) tager ét publiceret signal og bygger
  udelukkende på dets godkendte claims — modellen får intet andet
  faktagrundlag og må intet tilføje. Forslaget lander som en ugodkendt
  kandidat i samme flow, med `proposed_by_ai` og `proposal_prompt_version`
  som provenance og uden `created_by_user_id` (intet menneske skrev det).
  Modellen må svare `{"proposal": null}` (409 `no_opportunity`) frem for at
  presse et OK-problem ned over signalet, og et problemnavn uden for
  taxonomien afvises (502 `unknown_problem`) i stedet for at oprette et nyt
  — taxonomien er kurateret. UI'et markerer forslag med badge og en note om,
  at hypotese og næste handling er analyse, ikke fakta.
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
  kører fra samme image som API'et: henter forfaldne public rss- og
  web_fetch-kilder (frekvensstyret via next_check_at) gennem samme
  `run_source_fetch` som API-endpointet og AI-behandler normaliserede
  dokumenter, når provider er konfigureret.
- **Observability:** request-logging-middleware med correlation id
  (X-Request-ID) og varighed; AI-kald logger prompt-id/version, model,
  latency og tokenforbrug. Tokens, secrets og dokumenttekster logges
  aldrig. Fuld OpenTelemetry-instrumentering er en senere hardening.
- **Audit-log** (`audit_log`, `GET /audit`, kun Admin) dækker §18's
  "ændringer i review, sources og opportunities" samt publicering af
  signaler og cases, fordi publicering er det, der gør fakta offentlige.
  Rækkerne er append-only og rummer aktør, handling, entity og før/efter
  for de ændrede felter — hver værdi afkortet ved 500 tegn, så loggen er et
  spor og ikke en kopi af indholdet. `request_id` kobler rækken til
  requesten via en ContextVar sat i middlewaren, så endpoints ikke skal
  bære et ekstra argument. `entity_type` og `action` er text frem for
  PostgreSQL-enums, så nye handlinger ikke kræver en migration.
  Tabellens `id` er en stigende sekvens, ikke en uuid: `occurred_at` er
  transaktionens starttidspunkt og er ens for flere rækker fra samme
  request, så id'et bærer rækkefølgen. Produktets aktivitetsfeed er
  bevidst uden for MVP (Product Master §13), så loggen har ingen
  brugerflade.
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
- **Review-arbejdsbordet (§15)** er two-pane: dokumentet med evidensuddrag
  fremhævet til venstre, claims og reviewhandlinger til højre. Uddragene
  placeres via de server-beregnede offsets; passer de ikke, findes uddraget
  ordret, og kan det ikke placeres, fremhæves det ikke — det vises fortsat
  på claim-kortet, så intet evidensuddrag går tabt. Overlappende uddrag
  fremhæves kun én gang. Det valgte uddrag skifter både understregnings-
  tykkelse og flade, så markeringen ikke kun er kulør. Under 1100px stables
  panelerne med dokumentet først. §15's krav om at godkendelse ikke må ske
  uden synligt evidensuddrag er håndhævet i UI'et: et claim uden evidens
  viser ingen handlinger.
- **Confidence vises ikke.** UI Master §15 nævner confidence som
  sorteringshjælp, men feltet findes hverken i Technical Masters datamodel
  eller i API'et. Ved konflikt vinder Technical Master, og en score må ikke
  opfindes — feltet kan tilføjes, hvis modellen begynder at levere det.
- **Udestående mod UI Master:** stakbaseret entity-drawer (detaljer er
  route-baserede sider, hvilket Technical Master §12 tillader),
  filterbar på adoption (land/branche/capability/status/styrke), toasts,
  kompakt tablet-sidebar og `AI Radar.dc.html`-sammenligning (filen er
  ikke leveret).

## Staging-opsætning (Supabase + Render)

- Supabase-projektet `ai-radar-staging` (org OK, Frankfurt) kører alle
  migrations + seed; privat `documents`-bucket oprettet.
- **JWT-validering understøtter to veje:** ES256/RS256 via projektets
  JWKS-endpoint (moderne Supabase signing keys — det aktive på
  staging-projektet) og HS256 via `SUPABASE_JWT_SECRET` (legacy; bruges
  af unit tests). Algoritmen aflæses af tokenets header; ukendte
  algoritmer afvises.
- Render free tier hoster API'et (blueprint i `render.yaml`); workeren
  kører ikke på free tier — hentning/AI-behandling via admin-UI'ets
  knapper indtil opgradering.

## Frontend-auth (Supabase Auth)

- Login (`/login`, e-mail/adgangskode via `signInWithPassword`), logout og
  brugerstatus i topbaren. Session holdes i cookies via `@supabase/ssr`;
  middleware refresher tokens.
- API-laget har en token-provider pr. runtime: serveren læser sessionen
  fra requestens cookies (registreret i `lib/register-server-auth.ts`),
  browseren fra Supabase-klienten (`components/auth/auth-init.tsx`).
  Alle eksisterende kald får dermed Authorization-header uden ændrede
  call sites. Uden Supabase-env (lokal udvikling) sendes ingen header,
  og API'ets dev-bypass gælder.
- Brugere oprettes i Supabase Auth; roller styres i `profiles`-tabellen
  (admin-bruger seedet i staging).

## Udestående (kendte mangler mod masterne)

- OK's design tokens fra `colors_and_type.css` og UI-prototypen.
- Route-baserede drawers og udvidede filtre (branche, capability,
  dokumentationsstyrke) på adoption.
- OpenTelemetry-eksport og RLS-tests (RLS er deny-all, og al adgang går
  via API'et, hvis rolletjek er dækket af API-testene — nu også mod
  PostgreSQL).
- Evaluering af `opportunity_proposal`-prompten mod reference-datasættet,
  når datasættet er bygget.
