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
