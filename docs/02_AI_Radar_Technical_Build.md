# AI Radar — Technical Build Master

## 0. Status og source of truth

Dette er den autoritative tekniske byggeplan for AI Radar. Den læses sammen med `01_AI_Radar_Product_Design.md`. Product Master definerer produktadfærd og scope. Denne fil definerer arkitektur, datamodel, sikkerhed, kontrakter, deployment og implementeringsrækkefølge.

## 1. Låste tekniske beslutninger

- **Frontend:** Next.js + TypeScript.
- **Frontend hosting:** Vercel.
- **Backend:** Python + FastAPI.
- **Backend runtime:** standard containeriseret service på en udskiftelig containerhost.
- **Database:** Supabase PostgreSQL.
- **Dokumentlager:** Supabase Storage med private buckets.
- **Authentication:** Supabase Auth.
- **Authorization:** server-side roller plus PostgreSQL Row Level Security.
- **AI:** provider-neutralt lag med OpenAI-kompatibel adapter.
- **Repository:** Git med GitHub som nuværende remote og samarbejdsplatform.
- **Observability:** OpenTelemetry-kompatibel instrumentering og standardlogs.

Applikationsstacken skal så vidt muligt bestå af open source-komponenter og åbne standarder. Centrale komponenter skal kunne self-hostes eller udskiftes.

**Godkendt undtagelse:** Vercel bruges som managed frontendhosting, men må ikke være en uerstattelig teknisk afhængighed.

## 2. Arkitektur

```text
GitHub
  Git repository, branches, pull requests og CI

Vercel
  Next.js + TypeScript
  Server-side frontendfunktioner
  Supabase Auth session
  |
  | HTTPS
  v
Container host
  FastAPI API
  Ingestion/AI worker fra samme codebase
  |
  +--> Supabase PostgreSQL
  +--> Supabase Storage
  +--> Konfigureret AI-provider
  +--> OpenTelemetry logs og metrics

Supabase
  PostgreSQL
  Storage
  Authentication
  Row Level Security
```

MVP bruger én backend-codebase. API og worker kan køre som separate processer fra samme containerimage og fælles domænelag. Undgå mikroservices.

Supabase er den valgte managed MVP-platform, men datalaget skal fortsat bruge standard PostgreSQL, migrations og tydelige storage/auth-adapters. Ingen kritisk forretningslogik må kun eksistere i Supabase dashboard-konfiguration.

## 3. Repository og GitHub

```text
ai-radar/
├── apps/
│   ├── web/                 # Next.js
│   └── api/                 # FastAPI og worker entrypoints
├── packages/
│   ├── contracts/           # Kun hvis typer reelt deles
│   └── taxonomy/            # Kun hvis taxonomi reelt deles
├── supabase/
│   ├── migrations/
│   ├── seed.sql
│   └── config.toml
├── infrastructure/          # Docker og deploymentkonfiguration
├── evaluation/
├── docs/
│   ├── 01_AI_Radar_Product_Design.md
│   └── 02_AI_Radar_Technical_Build.md
├── .github/workflows/
├── CLAUDE.md
├── README.md
└── .gitignore
```

Tomme packages må fjernes. Struktur må ikke skabes alene for symmetri.

### Instruktion til Claude Code

Claude Code skal:

1. Forbinde til det GitHub-repository, som brugeren autoriserer.
2. Arbejde på `feature/<kort-navn>` og ikke direkte på `main`.
3. Bruge små, logiske commits.
4. Oprette eller opdatere en pull request med ændringsoversigt og teststatus.
5. Behandle de to masterfiler som source of truth.
6. Stoppe ved væsentlige produkt- eller arkitekturkonflikter frem for at gætte.
7. Behandle HTML-prototypen som designreference, ikke produktionskode.
8. Undgå nye services, frameworks og databaser uden et konkret krav.
9. Aldrig committe `.env`, Supabase service-role key, databasepasswords, AI-nøgler eller Vercel-secrets.
10. Opdatere masterfilerne i samme PR, når en godkendt beslutning ændrer produkt eller arkitektur.

Standardbranch er `main`. Pull request og grøn CI kræves før merge.

## 4. Miljøer

- **local:** Docker Compose og Supabase lokal udvikling, når praktisk.
- **staging:** separat Supabase-projekt, backend-staging og Vercel preview/staging.
- **production:** separat Supabase-projekt, production backend og Vercel production.

Regler:

- Separate databaser og Storage buckets pr. miljø.
- Separate keys, callback URLs og konfigurationer.
- Ingen production-data i tests.
- Ingen demo-claims publiceres i production.
- Secrets konfigureres uden for Git.

## 5. Domænemodel

Alle primære tabeller bruger UUID, `created_at`, `updated_at` og auditmetadata. Timestamps gemmes i UTC.

### Company

- `id uuid primary key`
- `name text not null`
- `slug text unique not null`
- `country_code text not null`
- `industry text null`
- `website_url text null`
- `active boolean default true`

### EntityAlias

- `id uuid`
- `entity_type enum(company, technology, vendor)`
- `entity_id uuid`
- `alias text`
- `normalized_alias text`

Unik kombination af entity type og normalized alias.

### Source

- `id uuid`
- `name text not null`
- `base_url text null`
- `source_type enum not null`
- `retrieval_method enum(rss, web_fetch, manual_upload)`
- `endpoint_url text null`
- `country_code text null`
- `frequency enum(manual, daily, weekly, monthly)`
- `access_class enum(public, licensed, restricted)`
- `active boolean default true`
- `last_checked_at timestamptz null`
- `next_check_at timestamptz null`
- `owner_user_id uuid null`
- `notes text null`

MVP understøtter RSS, almindeligt web fetch og manuel upload. Bred search discovery er ikke MVP.

### Document

- `id uuid`
- `source_id uuid not null`
- `canonical_url text null`
- `title text null`
- `language_code text null`
- `published_at timestamptz null`
- `retrieved_at timestamptz not null`
- `content_hash text not null`
- `raw_storage_path text null`
- `normalized_text text null`
- `mime_type text null`
- `processing_status enum not null`
- `is_demo boolean default false`
- `error_code text null`
- `error_message_safe text null`

Idempotency bruger som udgangspunkt `source_id + content_hash`.

Processing status:

- discovered
- fetched
- normalized
- classified_relevant
- classified_irrelevant
- extraction_pending
- review_pending
- partially_reviewed
- reviewed
- failed

### Claim

- `id uuid`
- `claim_type enum not null`
- `subject_entity_type enum(company, technology, vendor)`
- `subject_entity_id uuid not null`
- `predicate enum not null`
- `object_entity_type enum null`
- `object_entity_id uuid null`
- `object_text text null`
- `normalized_value jsonb null`
- `valid_from date null`
- `valid_to date null`
- `observed_at timestamptz not null`
- `review_status enum not null`
- `lifecycle_status enum not null`
- `created_by enum(ai, human)`
- `reviewed_by_user_id uuid null`
- `reviewed_at timestamptz null`

Et claim må kun indeholde ét faktuelt udsagn. Ukendte værdier og tidsreferencer forbliver null.

### MVP claim types og predicates

- Adoption: `USES_CAPABILITY`
- Use case: `USES_FOR`
- Stage: `ADOPTION_STAGE`
- Technology/vendor: `USES_TECHNOLOGY`, `USES_VENDOR`
- Effect: `REPORTED_EFFECT`
- Negative/barrier: `REPORTS_BARRIER`, `REPORTS_NEGATIVE_OUTCOME`, `ABANDONED_OR_REPLACED`
- Organization: `USES_GOVERNANCE_MODEL`, `USES_HUMAN_REVIEW`, `REPORTS_ADOPTION_APPROACH`, `REPORTS_DATA_FOUNDATION`

Tilladte adoption stages:

- Experiment
- Pilot
- Production
- Scale
- Unknown

Eksempel på splitting:

> Company X bruger generativ AI til kundeservicemedarbejdere og rapporterer 20 procent lavere efterbehandlingstid.

Bliver til:

1. Company X `USES_CAPABILITY` Generative AI.
2. Company X `USES_FOR` Agent assistance.
3. Company X `REPORTED_EFFECT` 20 procent lavere efterbehandlingstid.

AI må ikke udlede leverandør, production-status, effekt eller tidsperiode, hvis det ikke står eksplicit.

### ClaimEvidence

- `id uuid`
- `claim_id uuid not null`
- `document_id uuid not null`
- `supporting_excerpt text not null`
- `excerpt_start integer null`
- `excerpt_end integer null`
- `relationship enum(supports, contradicts, supersedes)`
- `source_type_snapshot enum`
- `independent_origin_key text null`
- `review_status enum`

Uddraget skal være tilstrækkeligt til, at en reviewer kan vurdere claimet uden at stole på AI-resuméet.

### Signal

- `id uuid`
- `title text`
- `summary text`
- `analysis text null`
- `recommendation text null`
- `documentation_level enum(strong, limited, early, conflicting)`
- `status enum(draft, published, archived)`
- `published_at timestamptz null`
- relationer til claims, companies og technologies

Kun godkendte claims må være faktuelt grundlag for et publiceret signal.

### AdoptionCase

- `id uuid`
- `company_id uuid`
- `title text`
- `summary text null`
- `status enum(draft, published, archived)`
- relationer til claims, technologies og use cases

Cases er præsentationsenheder. Fakta ligger i claims.

### Technology

- `id uuid`
- `name text`
- `slug text unique`
- `definition text`
- `horizon enum(now, next, horizon)`
- `active boolean`

Modenhed, adoption, evidens for værdi, momentum og overførbarhed skal holdes adskilt. Ingen samlet opaque score.

### Vendor

- `id uuid`
- `name text`
- `website_url text null`
- `active boolean`

Vendor-capabilities kræver evidens eller markeres som unverified.

### ProblemTaxonomy

- `id uuid`
- `name text`
- `description text`
- `area text`
- `active boolean`

### Opportunity

- `id uuid`
- `title text`
- `problem_id uuid`
- `relevance_hypothesis text`
- `evidence_gaps text null`
- `recommended_next_action text`
- `status enum(identified, investigating, business_case, pilot, scaling, closed)`
- `owner_user_id uuid null`
- `created_by_user_id uuid`
- `approved_by_user_id uuid null`
- relationer til signals, claims og technologies

AI kan oprette et draft-forslag. Menneskelig godkendelse kræves for aktiv opportunity.

## 6. Review og evidensstatus

Review status:

- proposed
- approved
- approved_with_edits
- needs_corroboration
- rejected

Claim lifecycle:

- current
- contradicted
- superseded
- expired

“Approved” betyder, at en reviewer har vurderet claimet som korrekt gengivelse af evidensuddraget. Det betyder ikke automatisk uafhængigt bevist sandhed.

Gentagelser af samme oprindelige kilde tæller ikke som uafhængig corroboration.

## 7. Supabase

### PostgreSQL

- Brug almindelige tabeller, foreign keys, constraints og versionerede SQL-migrations.
- Undgå Supabase-specifik databaseadfærd, hvor standard PostgreSQL er tilstrækkeligt.
- `pgvector` er ikke standard i MVP og tilføjes kun efter dokumenteret behov.

### Storage

- Originale dokumenter gemmes i private buckets.
- Database gemmer storage path og metadata, ikke public URL som autoritativ reference.
- Signed URLs udstedes kortvarigt til autoriserede brugere.
- Filtype, størrelse og MIME type valideres.
- Service-role key bruges kun server-side.

### Auth og RLS

- Supabase Auth leverer brugeridentity og session.
- Roller: Reader, Reviewer og Admin.
- Roller lagres i en kontrolleret profil/role-model, ikke i brugerredigerbare metadata.
- RLS aktiveres på alle brugerrelaterede og følsomme tabeller.
- Browseren må aldrig modtage service-role key.
- Backend kan bruge en server-side credential, men skal stadig håndhæve brugerens authorization eksplicit.

### Portabilitet

Supabase-adgang isoleres i adapters. Domænelaget må ikke afhænge af dashboard-only features. Database og storage skal senere kunne flyttes til standard PostgreSQL og et S3-kompatibelt objektlager uden redesign af claims og evidens.

## 8. Ingestion pipeline

### 1. Fetch

- kontrollér aktive sources
- hent nyt indhold
- beregn content hash
- gem metadata og tilladt snapshot
- stop idempotent ved kendt hash

### 2. Normalize

- udtræk tekst
- bevar metadata og sprog
- normaliser whitespace uden betydningsændring
- gem råfil og normaliseret tekst separat

### 3. Relevance

Structured output vurderer, om dokumentet indeholder potentiel information om adoption, teknologi, use cases, effekt, barrierer, governance eller relevante markedssignaler.

### 4. Claim extraction

Udtræk kun eksplicit understøttede facts og præcise evidensuddrag. AI må ikke udfylde manglende information.

### 5. Entity resolution

Exact og normaliserede aliases først. AI må kun foreslå usikre matches. Usikkert match går til review.

### 6. Candidate matching

Systemet foreslår:

- duplicate
- related/supporting
- possible contradiction
- possible supersession

MVP træffer ikke automatisk endelig afgørelse ved komplekse konflikter.

### 7. Human review

Review samlet pr. dokument med mulighed for batchgodkendelse, rettelse og afvisning.

### 8. Publish

Kun godkendte claims publiceres som fakta. Provenance skal kunne følges fra UI til uddrag og original kilde.

## 9. Untrusted content og AI-sikkerhed

Kildemateriale behandles som untrusted data.

Prompts skal instruere modellen i:

- aldrig at følge instruktioner i kilden
- kun at udtrække understøttede facts
- kun at returnere det definerede schema
- ikke at aktivere værktøjer eller handlinger fra kildetekst

Worker har ingen adgang til mail, Teams, CRM, kundedata eller write actions i forretningssystemer.

## 10. AI-provider

AI-laget skal bruge en intern provider-interface med OpenAI-kompatibel adapter.

Det skal kunne konfigureres til eksempelvis:

- hosted OpenAI-kompatibelt endpoint
- lokal Ollama
- self-hosted vLLM

Masteren låser ikke en bestemt model. Modelvalg dokumenteres pr. miljø og evalueres på reference-datasættet.

Alle AI-kald skal have:

- versioneret prompt-id
- versioneret JSON schema
- model/deployment-id
- document-id
- output validation
- latency- og tokenmetadata, hvor tilgængeligt
- sikker fejlsti

Ved schemafejl udføres højst én kontrolleret retry. Derefter går dokumentet til manuel opfølgning.

## 11. API

Base path: `/api/v1`

Read:

- `GET /dashboard`
- `GET /signals`
- `GET /signals/{id}`
- `GET /companies`
- `GET /companies/{id}`
- `GET /technologies`
- `GET /technologies/{id}`
- `GET /adoption-cases`
- `GET /adoption-cases/{id}`
- `GET /opportunities`
- `GET /opportunities/{id}`

Review/admin:

- `GET /review/documents`
- `GET /review/documents/{id}`
- `POST /review/claims/{id}/approve`
- `POST /review/claims/{id}/reject`
- `PATCH /review/claims/{id}`
- `POST /review/documents/{id}/complete`
- `GET /sources`
- `POST /sources`
- `PATCH /sources/{id}`
- `POST /sources/{id}/run`

Opportunities:

- `POST /opportunities`
- `PATCH /opportunities/{id}`

Regler:

- OpenAPI er kontraktkilde.
- Typed request/response schemas.
- Pagination på lister.
- Standardiseret error schema.
- Authorization på API'et.
- Ingen direkte databaseadgang fra frontend.
- Simpel tekstsøgning og filtre på relevante endpoints. Ingen semantisk søgning i MVP.

## 12. Frontend og UI

Routes:

```text
/
/adoption
/adoption/companies/[companyId]
/adoption/cases/[caseId]
/technologies
/technologies/[technologyId]
/opportunities
/opportunities/[opportunityId]
/sources
/briefing
/admin/review
/admin/review/[documentId]
/admin/sources
```

Krav:

- Next.js App Router.
- TypeScript strict mode.
- Server components som standard.
- Client components kun ved interaktivt behov.
- Typed data access layer til FastAPI.
- Ingen hardcodede production-facts i komponenter.
- UI'et genskabes fra prototypen med genbrugelige komponenter.
- Prototypefilens monolitiske struktur og inline styles kopieres ikke direkte.
- Design tokens fra `colors_and_type.css` anvendes.
- Route-baserede drawers eller detaljer skal kunne deles og genindlæses.
- Accessible dialogs, focus trap, Escape og fokusretur.
- Loading, empty, partial, unauthorized og error states.

### Vercel

- Vercel forbindes til GitHub-repositoryet.
- Pull requests kan skabe preview deployments.
- Production deployes fra `main` efter godkendt merge og grøn CI.
- Environment variables konfigureres i Vercel og committes ikke.
- Frontend kommunikerer med FastAPI over HTTPS.
- CORS begrænses til godkendte Vercel-domæner og lokale udviklingsorigins.
- Projektet skal også have en standard Dockerfile til frontend-portabilitet.

## 13. Authentication og authorization

- Supabase Auth er MVP'ens identity layer.
- Next.js bruger Supabase sessioner med sikre cookies efter anbefalet server-side mønster.
- FastAPI validerer JWT-signatur, issuer, audience og relevante claims.
- 401 bruges ved manglende eller ugyldig authentication.
- 403 bruges ved utilstrækkelig rolle.
- Tokens må ikke logges.
- Undgå langlivede tokens i browser storage.
- Auth isoleres bag en adapter, så en anden OIDC-provider senere kan anvendes.

## 14. Dokumentrettigheder

For hver source registreres `access_class` og tilladt storage-adfærd.

- **Public:** snapshot kan gemmes, hvis det er lovligt og teknisk tilladt.
- **Licensed:** gem kun det, licensvilkår tillader.
- **Restricted:** kræver godkendt adgang og må ikke eksponeres bredt.

Systemet må ikke omgå paywalls eller adgangskontrol.

## 15. Deduplikering og konflikter

Dokumentniveau:

- canonical URL
- content hash
- normalized fingerprint
- origin metadata

Claimniveau:

- subject
- predicate
- normalized object
- tidskontekst
- evidensoprindelse

Start deterministisk. Ingen vector database i MVP.

AI må markere en mulig konflikt. Reviewer sætter endelig relation: supports, contradicts eller supersedes. Gamle claims overskrives ikke.

## 16. Evaluation

Start med et repræsentativt manuelt evalueret dataset på tværs af lande, kildetyper, relevante og irrelevante dokumenter, positive og negative cases, manglende facts, dubletter og konflikter.

Mål:

- relevance precision
- claim precision
- excerpt correctness
- entity resolution accuracy
- technology classification accuracy
- duplicate candidate precision
- human acceptance rate
- reviewtid, hvis instrumentering er mulig

100–200 dokumenter er et modningsmål, ikke en blokering for første slice.

## 17. Testing

Backend:

- unit tests for normalization, validation og mapping
- integration tests mod PostgreSQL og Storage adapter
- API contract tests
- authorization og RLS tests
- ingestion idempotency tests
- AI schema tests med fixtures

Frontend:

- component tests for kritiske states
- route/data integration tests
- accessibility tests
- end-to-end test af primær brugerrejse

Primært end-to-end-scenario:

1. Source oprettes.
2. Dokument hentes.
3. Relevans og claims foreslås.
4. Reviewer godkender claim.
5. Signal publiceres.
6. Reader ser signal og evidens.
7. Opportunity-kandidat oprettes.

## 18. Observability og audit

Operational metrics:

- source checks og fejl
- documents fetched/unchanged/failed
- relevance outcomes
- extraction failures
- review queue size
- API fejl og latency
- AI latency og forbrug, hvor tilgængeligt

Product quality:

- godkendte kontra afviste claims
- rettelser før godkendelse
- dokumenter der fører til signaler
- signaler der fører til opportunities

Brug correlation ids. Log aldrig tokens, secrets eller fulde dokumenttekster. Auditér ændringer i review, sources og opportunities.

## 19. CI/CD og deployment

GitHub CI på pull requests:

- lint og formatting
- TypeScript type check
- Python type/lint check
- unit tests
- API tests
- frontend build
- backend container build
- dependency og secret scanning

Supabase:

- migrations, RLS policies og seed scripts versioneres i `supabase/`.
- Production migrations køres kontrolleret.
- Destruktive migrations kræver eksplicit plan.

Backend:

- FastAPI bygges som OCI/Docker-container.
- Hostspecifik konfiguration holdes uden for domænelaget.
- Tidligere containerimage skal kunne genaktiveres ved rollback.

Vercel:

- Repository forbindes til Vercel.
- Preview deployments på PR, når aktiveret.
- Production efter merge til `main` og grøn CI.
- Tidligere deployment skal kunne rulles tilbage.

## 20. Implementeringsrækkefølge

### Slice 0: Foundation

- GitHub-struktur og `CLAUDE.md`
- Next.js shell baseret på UI-prototypen
- FastAPI health endpoint
- Supabase lokal/staging-konfiguration
- migrationsbaseline
- CI
- Dockerfiles

### Slice 1: Source → Document

- Source Registry
- manuel upload og én simpel fetch-metode
- private Storage buckets
- normalization og idempotency
- admin source UI

### Slice 2: Document → Claim → Review

- relevance classification
- claim extraction
- evidence excerpts
- entity matching
- review queue og handlinger

### Slice 3: Published signal og Overblik

- signal publication
- Overblik/Radar
- provenance i UI

### Slice 4: Adoption og Technology

- company, case og technology profiles
- filtre
- relaterede entities

### Slice 5: Opportunities

- problem taxonomy
- opportunity candidate
- status, ejer og kobling til evidence

### Slice 6: Briefing og hardening

- enkel briefingvisning
- evaluation
- accessibility
- observability
- staging deployment

Hver slice skal være demonstrerbar end-to-end.

## 21. Bevidst ude af scope

- MCP
- graph database
- Azure AI Search
- separat vector database
- Kubernetes
- event streaming
- autonomous eller multi-agent systems
- bred automatisk web discovery
- business-system write actions
- customer data/PII
- automatisk endelig contradiction-afgørelse
- automatisk claim-publicering
- automatisk opportunity-godkendelse
- paywall-bypass
- fuld business case- og projektstyring

## 22. Definition of done

En slice er færdig, når:

- acceptance criteria er opfyldt
- tests er grønne
- authorization og RLS er verificeret
- fejl- og loading states er håndteret
- telemetry er tilføjet uden følsomme data
- API-kontrakt og migrations er opdateret
- relevante masterfiler er konsistente
- ændringerne ligger i en pull request

MVP er teknisk færdig, når denne kæde fungerer i staging:

**Source → Document → Claim → Evidence → Human review → Published signal → Adoption/Technology → Opportunity**

## 23. Regel ved uklarheder

Claude Code må træffe lokale implementeringsvalg, når de ikke ændrer produktadfærd, låst arkitektur, sikkerhed eller provenance. Ved væsentlige konflikter skal Claude Code stoppe og beskrive konflikten frem for at gætte.
