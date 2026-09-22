# Deployment (staging og production)

Miljøregler fra Technical Master §4: separate Supabase-projekter, databaser,
buckets, keys og callback URLs pr. miljø. Secrets konfigureres uden for Git.
Ingen production-data i tests; ingen demo-claims i production.

## 1. Supabase (pr. miljø)

1. Opret et Supabase-projekt (staging hhv. production).
2. Kør migrations i rækkefølge (Supabase CLI: `supabase db push`, eller
   `psql -v ON_ERROR_STOP=1 -f <fil>` for hver fil i `supabase/migrations/`).
3. Kør `supabase/seed.sql` i staging (teknologier + problem-taxonomi).
   I production køres seed kun efter bevidst beslutning — indholdet er
   kurateret taxonomi, ikke demo-claims.
4. Opret en **privat** Storage-bucket med navnet `documents`.
5. Notér: projekt-URL, anon key (frontend) og service-role key (kun
   backend). En JWT-secret er kun nødvendig for legacy HS256-projekter —
   nye projekter signerer med ES256, og API'et validerer dem mod
   projektets JWKS-endpoint ud fra `SUPABASE_URL`.
6. Roller: indsæt rækker i `profiles` (user_id fra Auth, role
   reader/reviewer/admin). RLS er deny-all — al adgang går via API'et.

## 2a. Backend på Render (valgt til staging)

`render.yaml` i repo-roden er en Render Blueprint: Dashboard → **New →
Blueprint** → vælg AI-Radar-repoet → indtast de to secrets
(`DATABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`) → Apply. JWT-validering
sker via projektets JWKS-endpoint (moderne Supabase signing keys), så
ingen JWT-secret er nødvendig. Region Frankfurt, free tier, auto-deploy fra `main`,
health check på `/api/v1/health`.

Free tier-begrænsninger (bevidst accepteret for staging): servicen
sover efter inaktivitet (~30-50 sek. opvågning), og worker-processen
kører ikke — hentning/AI-behandling udføres via knapperne i admin-UI'et.
Ved opgradering til betalt plan tilføjes workeren som separat service
(`python -m app.worker --interval 300`).

## 2. Backend (containerhost, generelt)

1. Byg imaget: `docker build apps/api` (CI bygger det også).
2. Kør API'et med miljøvariabler (se `apps/api/.env.example`):
   `ENVIRONMENT=staging|production`, `DATABASE_URL`
   (`postgresql+psycopg://…` — brug Supabase connection string),
   `STORAGE_BACKEND=supabase`, `SUPABASE_URL`,
   `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET=documents`,
   `CORS_ORIGINS=<godkendte Vercel-domæner + lokale origins>`,
   samt AI-provider-variablerne når AI-behandling skal køre.
3. Workeren kører fra samme image med anden kommando:
   `python -m app.worker --interval 300`.
4. Rollback: genaktivér forrige containerimage.

Dev-bypass for auth er kun aktiv ved `ENVIRONMENT=local` uden
`SUPABASE_JWT_SECRET` — staging/production sætter `ENVIRONMENT` til
`staging` hhv. `production`, hvilket slår bypasset fra uanset secrets.

Containerkommandoen ligger i imagets `CMD` (binder uvicorn til `$PORT`
med fallback til 8000). Sæt ikke en platform-specifik start-kommando
oven i den med egne anførselstegn — Render kører feltet gennem sin egen
shell, og en indlejret `sh -c "..."` ender som ét kommando-ord (exit 127).

## 3. Frontend (Vercel)

1. Forbind repositoryet til Vercel; **root directory `apps/web`**.
   Framework preset: Next.js (autodetekteres).
2. Environment variables (alle tre, for Production + Preview):
   - `NEXT_PUBLIC_API_BASE_URL=https://<api-host>/api/v1`
   - `NEXT_PUBLIC_SUPABASE_URL=https://<projekt-ref>.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>` — anon key er beregnet
     til browseren; service-role key må aldrig lægges i Vercel.
3. Når Vercel-domænet kendes: tilføj det til `CORS_ORIGINS` på API'et
   (kommasepareret) og redeploy API'et. Uden det afvises browserkaldene.
4. Supabase → Authentication → URL Configuration: sæt Site URL til
   Vercel-domænet.
5. Preview deployments på PR; production deployes fra `main` efter grøn CI.
6. Rollback: Vercel's deployment-historik.
7. Frontend-portabilitet: `docker build apps/web` giver et standalone-image.

## 4. Verifikation efter deploy

- `GET /api/v1/health` svarer `{"status":"ok"}`.
- `GET /api/v1/sources` uden token svarer 401 (auth er aktiv).
- Login på `/login` med en bruger fra Supabase Auth, der har en række i
  `profiles`; topbaren viser e-mailen efter login.
- Frontendens Overblik viser data fra API'et.
- Kør evalueringen mod reference-datasættet før modelskift:
  `uv run python -m app.evaluation --dataset evaluation/dataset.jsonl`.
