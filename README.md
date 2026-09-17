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

**Slice 0 — Foundation** er etableret: repo-struktur, Next.js-shell,
FastAPI health endpoint, Supabase-migrationsbaseline, CI og Dockerfiles.
Implementeringsrækkefølgen (Slice 0–6) står i Technical Master §20.
