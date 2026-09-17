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
