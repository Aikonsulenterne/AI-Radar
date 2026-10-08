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
  `ai_not_configured`. Planlagte kørsler: se "Automatiske kørsler".
- **Evidens håndhæves mekanisk:** et claim kasseres, hvis
  `supporting_excerpt` ikke findes ordret i den normaliserede tekst;
  offsets beregnes server-side. Prompten forbyder at følge instruktioner
  i kildeteksten (untrusted data, Technical Master §9).
- **Schemafejl:** højst én kontrolleret retry; derefter
  `processing_status=failed` med `error_code=ai_schema_error` til manuel
  opfølgning.
- **To adaptere bag samme interface:** `OpenAICompatProvider` (ethvert
  OpenAI-kompatibelt endpoint) og `AnthropicProvider` (Claude via
  Anthropics officielle SDK), valgt med `AI_PROVIDER`. Pipeline, prompts og
  schema-validering er fælles; adapteren returnerer kun tekst. Claude-
  adapteren fjerner defensivt en ```json-indpakning, fordi promptene beder
  om rå JSON, men valideringen og den ene retry er fortsat sikkerhedsnettet.
  Claudes server-side refusal-fallbacks er ikke slået til: de kræver et
  beta-endpoint, og modellen er konfigurerbar, så en beta-header, der kun
  gælder bestemte modeller, ville være en skjult fejlkilde.
- **Udbyderfejl har deres egen diagnose.** En 4xx fra udbyderen (ugyldig
  nøgle, ukendt model, ingen adgang, opbrugt kvote) er en konfigurations-
  fejl: den prøves ikke igen, dokumentet røres ikke, og endpointet svarer
  502 `ai_provider_rejected` med en dansk forklaring, der peger på den
  relevante miljøvariabel. Udbyderens egen fejltekst gengives ikke — den
  kan indeholde en delvist maskeret nøgle. Workeren stopper behandlingen
  ved samme fejl i stedet for at gentage den for hvert dokument. En
  refusal fra modellen på et bestemt dokument sender dokumentet til manuel
  opfølgning med `error_code=ai_refused`.
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
- Render free tier hoster API'et (blueprint i `render.yaml`). Der er ingen
  separat worker-proces på free tier, så workerens kørsel udløses via
  `POST /api/v1/runs` og udføres som baggrundsopgave i API-processen efter
  svaret (se "Automatiske kørsler" nedenfor).

## Automatiske kørsler

- **Behov:** radaren skal hente fra kuraterede kilder ugentligt og on
  demand uden manuelle klik pr. kilde. Kilder kurateres fortsat af
  mennesker i Source Registry; kørslen opdager ikke nye kilder selv.
- **Udløser:** pg_cron + pg_net i Supabase (`supabase/ops/weekly_trigger.sql`,
  mandag 05:00 UTC). Valgt frem for GitHub Actions, fordi den ikke kræver
  repository secrets: nøglen ligger i Supabase Vault, og API'et validerer
  dens hash i `worker_trigger_keys` (eller `WORKER_TRIGGER_TOKEN`).
  Scriptet ligger uden for migrations/, da udvidelserne er
  Supabase-specifikke. `weekly-run.yml` er bevaret som manuelt alternativ.
  "Kør nu" i admin bruger samme endpoint med Admin-login.
- **Planlagt vs. on demand:** planlagt kørsel henter kun kilder med
  forfalden frekvens; "Kør nu" (`force_all`) henter alle aktive kilder,
  også dem med frekvens "manuel" — et menneske har bedt om det.
- **Kørselslog:** `worker_runs` (én række pr. kørsel: udløser, status,
  tællinger, sikker fejltekst). Kun én kørsel ad gangen; en kørsel, der har
  stået som `running` i over 6 timer, markeres som afbrudt.
- **Samtidighed med manuel AI-behandling:** begge veje går gennem
  `begin_processing`, der låser dokumentrækken og sætter
  `extraction_pending` før AI-kaldet, så et dokument aldrig behandles to
  gange (dobbeltklikket på Deepvis-dokumentet gav dobbelte claims).
- **Afgrænsning:** en afvist AI-nøgle stopper kørslen (status `failed` med
  årsag) i stedet for at gentage fejlen pr. dokument. Human-in-the-loop er
  uændret: kørslen foreslår claims; godkendelse og publicering er
  menneskelige handlinger.
- **Kendt begrænsning (free tier):** Render kan lukke en inaktiv instans;
  workflowet poller status hvert 30. sekund, hvilket også holder den vågen.
  Afbrydes en kørsel alligevel, samler næste kørsel de resterende
  normaliserede dokumenter op.

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

## Fuldt automatisk publicering (AUTO_PUBLISH)

- **Beslutning:** produktejeren valgte 2026-09-29 fuld automatik frem for
  AI-kontrol med stikprøver og frem for menneskelig godkendelse. Radaren
  skal selv hente, vurdere og publicere.
- **Flow:** efter claim extraction (`pipeline/process.py`) kalder
  `pipeline/autopublish.py` — kun når `AUTO_PUBLISH=true` — godkendelse af
  dokumentets åbne claims, én publiceret adoption case pr. virksomhed og ét
  publiceret signal (prompt `signal_draft` v1.0.0). Dokumentet får status
  `reviewed`. Fejler signal-prompten, publiceres claims og cases alligevel.
- **Backlog:** hver kørsel (`POST /runs`) publicerer også dokumenter, der
  står i `review_pending`/`partially_reviewed` — fx dem, der blev behandlet,
  før flaget blev slået til. Idempotent: afgjorte claims røres ikke.
- **Mærkning:** `claims.auto_approved`, `signals.auto_published` og
  `adoption_cases.auto_published`; UI'et viser "AI-publiceret" /
  "Automatisk godkendt af AI". Auditspor med `actor_user_id = null`.
- **Kvalitet uden menneske:** claim extraction bumpet til v1.1.0 — skelner
  leverandør fra bruger og udelader generiske produktbeskrivelser (fejlen
  fra Deepvis-dokumentet: "Deepvis bruger Vision AI").
- **Uændret:** opportunities kræver fortsat menneskelig godkendelse;
  evidensuddrag skal fortsat stå ordret i dokumentet; kendt risiko er, at
  forkerte fortolkninger nu publiceres uden kontrol. Afvist indhold kan
  stadig trækkes tilbage manuelt (arkivering af signal/case).

## Erfaringer fra første rigtige kørsel (2026-10-01)

- **Blokerede artikelsider:** Industry Dive (Utility, Retail, CX Dive)
  svarer 403 på artikelsider fra servere, selvom feeds'ene er åbne. Når en
  artikelside ikke kan hentes, gemmes entryets egen tekst fra feedet
  (`content:encoded`/`description`, Atom `content`/`summary`), hvis den er
  mindst 200 tegn — udgiverens offentliggjorte tekst, ingen omgåelse af
  adgangskontrol. CX Today svarede 429 (rate limit) på feedet selv.
- **Opbrugt AI-kredit:** Anthropic svarer 400 med "credit balance is too
  low". Det mappes til en afvisning med den danske besked "Kreditten hos
  AI-udbyderen er brugt op …", der stopper kørslen; ubehandlede dokumenter
  samles op af næste kørsel. Øvrige 400-svar gælder kun det enkelte
  dokument (`ai_request_rejected`), og kørslen fortsætter.
- **Entity-kvalitet:** claim extraction 1.2.0 kræver en organisation som
  subjekt (en person blev oprettet som virksomhed) og det fulde navn.
- **Tempo og omfang:** ca. 2–4 dokumenter pr. minut med Claude Opus;
  `RSS_MAX_ITEMS` er 10 pr. kilde pr. kørsel.

## Kundecenter-fokus (2026-10-06)

Første kørsler gav for meget generel AI-nyhed (forskning, modelnyheder,
leverandørblogs) og for lidt om kundecentre. Ændringer:

- **Relevans 2.0.0:** kun AI/automatisering i kundeservice og kundecentre
  (bots, agent assist, samtaleanalyse, QA, routing, CCaaS/CRM-AI, adoption
  hos navngivne organisationer, regulering af AI i kundekontakt). Generel
  AI-forskning og AI i andre funktioner frasorteres.
- **Billig relevansmodel:** relevanstrinnet kører på `claude-haiku-4-5`
  (overstyres med `AI_RELEVANCE_MODEL_ID`); udtræk og signaler bruger
  fortsat `AI_MODEL_ID`. Adapteren vælger model pr. prompt-id.
- **Signal 1.1.0:** analyse og anbefaling skrives til OK's kundecenter, og
  leverandørers egne tal benævnes som leverandørens.
- **Kildepakke:** `supabase/ops/kundecenter_sources.sql` tilføjer
  kundecenter-medier og danske Bing News-søgefeeds og pauser AWS ML-bloggen.
  Køres manuelt i Supabase SQL Editor. Feedene kunne ikke testes fra
  udviklingsmiljøet; hentefejl ses pr. kørsel.
- Allerede klassificerede dokumenter køres ikke om; kun ubehandlede
  (normaliserede) dokumenter møder det nye filter.

Udestår: problemtaksonomi for kundecentret, teknologilandskabsvisning
(kategori → leverandør → adopter) og leverandørkilder med verificerede feeds.

## Leverandørlandskab (2026-10-08)

Produktejeren præciserede radarens opgave: *hvilke leverandører tilbyder
hvilken AI-teknologi til danske kundecentre*. Extraction 1.1.0–1.2.0
sprang netop leverandørtilbud over, og Teknologiradaren talte kun adoption,
så næsten alt stod på 0. Ændringer:

- **Migration `20261008090000_vendor_offerings.sql`:** predicate
  `OFFERS_CAPABILITY` og teknologien *Virtual Agent* (chat-/voicebots).
  Skal køres i Supabase SQL Editor, *før* koden deployes — ellers fejler
  forespørgsler på den nye enum-værdi (Teknologiradar, Leverandører).
- **Extraction 1.3.0:** leverandørtilbud udtrækkes (`<leverandør>
  OFFERS_CAPABILITY <capability>`, produktnavn i objekttekst); brugerbeskeden
  indeholder radarens kuraterede capabilities, så objektet rammer en
  teknologi i stedet for fritekst. Relevans 2.1.0 nævner tilbud eksplicit.
- **Autopublicering:** tilbud giver ingen adoption case (leverandøren
  adopterer ikke sit eget produkt).
- **API:** `GET /vendor-landscape` (capability → leverandører → tilbud med
  evidens og kilde, plus kunder fra godkendte `USES_VENDOR`/`USES_TECHNOLOGY`
  claims). `TechnologyOut.vendor_count` og `TechnologyDetailOut.vendors`;
  adoption tæller ikke længere tilbud med.
- **UI:** ny side *Leverandører* (`/vendors`), *Signaler* (`/signals`, alle
  publicerede), "Se alle"-link på Overblik, leverandørantal på
  Teknologiradaren, og titlen på kort i HORIZON-kolonnen er synlig igen.
- **Kilder:** `kundecenter_sources.sql` har fået Bing News-feeds på
  leverandører (Puzzel, Dixa, Zendesk, Genesys, Agentforce, Dynamics 365
  Contact Center, contact center AI-lanceringer). Idempotent.
- Allerede behandlede dokumenter udtrækkes ikke igen; landskabet fyldes af
  nye artikler.
