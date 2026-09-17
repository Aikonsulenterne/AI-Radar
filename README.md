# AI Radar

Internt, evidensbaseret technology-intelligence- og beslutningsprodukt for OK.
Følger kæden: **Kilde → Dokument → Atomic Claim → Evidens → Verificeret signal
→ Adoption/teknologi → Relevans for OK → Opportunity → Handling.**

Det vigtigste spørgsmål er: **Hvor ved vi det fra?**

## Dokumentation

- [`docs/01_AI_Radar_Product_Design.md`](docs/01_AI_Radar_Product_Design.md) — produkt- og designmaster (source of truth for produktadfærd og scope)
- [`docs/02_AI_Radar_Technical_Build.md`](docs/02_AI_Radar_Technical_Build.md) — teknisk byggemaster (arkitektur, datamodel, sikkerhed, kontrakter, deployment)

## Stack

| Lag | Valg |
|---|---|
| Frontend | Next.js + TypeScript (Vercel) |
| Backend | Python + FastAPI (containeriseret) |
| Database | Supabase PostgreSQL (standard SQL + migrations) |
| Dokumentlager | Supabase Storage (private buckets) |
| Auth | Supabase Auth + server-side roller + RLS |
| AI | Provider-neutralt lag med OpenAI-kompatibel adapter |

## Kom i gang

Forudsætninger: Node 22+, Python 3.11+, [uv](https://docs.astral.sh/uv/).

```bash
# Frontend
cd apps/web
npm install
npm run dev          # http://localhost:3000

# Backend
cd apps/api
uv sync
uv run uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/api/v1/health

# Begge i containere
docker compose -f infrastructure/docker-compose.yml up --build
```

## Test og kvalitet

```bash
cd apps/web && npm run lint && npm run typecheck && npm run build
cd apps/api && uv run ruff check . && uv run pytest
```

CI kører de samme checks på pull requests (`.github/workflows/ci.yml`).
Pull request og grøn CI kræves før merge til `main`.

## Status

**Slice 0–6** er etableret (MVP-kæden fungerer end-to-end):

- Source Registry (API + admin-UI) med roller (Reader/Reviewer/Admin)
- Manuel upload (txt/html/pdf) og web fetch af public kilder
- Private storage via adapter (lokalt filsystem eller Supabase Storage)
- Normalisering og idempotency på (source_id, content_hash)
- Provider-neutralt AI-lag (OpenAI-kompatibelt) med versionerede prompts
- Relevansklassifikation og claim extraction med ordrette evidensuddrag
- Deterministisk entity resolution og duplicate-kandidater
- Review pr. dokument: godkend, ret og godkend, afvis, afslut —
  inkl. batchgodkendelse i UI'et
- Signaler med publiceringsflow: kun godkendte claims som faktagrundlag,
  fakta/analyse/anbefaling adskilt, dokumentationsstyrke og provenance
- Overblik med KPI-optællinger og seneste signaler; signalbygger under
  `/admin/signals`
- Adoption: virksomheder og cases med afledte faktafelter — manglende
  fakta vises som "Ikke dokumenteret"; casebygger under `/admin/cases`
- Teknologiradar i NU/NÆSTE/HORIZON med dokumenteret adoption pr.
  teknologi
- Opportunities: problem-taxonomi, kandidater koblet til
  signaler/claims, menneskelig godkendelse før pipelinen kan rykkes
- Briefing genereret af publiceret intelligence samt offentlig kildeside
- Worker-entrypoint (`python -m app.worker`), request-logging med
  correlation ids og evalueringsrunner (`python -m app.evaluation`)

Kæden **Source → Document → Claim → Evidence → Human review → Published
signal → Adoption/Technology → Opportunity** er implementeret; se
`docs/04_Deployment.md` for staging-opsætning og
`docs/05_Implementation_Notes.md` for valg og kendte udeståender.

AI-kørsel kræver `AI_PROVIDER_BASE_URL`/`AI_MODEL_ID` i API'ets miljø;
pipelinen er fixture-testet uden netkald. Implementeringsrækkefølgen
(Slice 0–6) står i Technical Master §20; lokale implementeringsvalg i
`docs/05_Implementation_Notes.md`.
