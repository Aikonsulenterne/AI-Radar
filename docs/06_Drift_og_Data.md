# AI Radar — drift og data (notat til IT og sikkerhed)

Status: udkast, oktober 2026. Formål: give IT et kort, ærligt billede af,
hvad AI Radar behandler, hvor det kører, og hvad der skal på plads, før den
kører i OK's eget miljø. Punkter markeret **[afklares]** er ikke verificeret.

## Hvad radaren gør

Radaren henter **offentlige** kilder (RSS-feeds og offentlige websider om AI
i kundeservice), lader en AI-model udtrække fakta med ordrette citater og
viser dem som leverandøroverblik og muligheder for OK Kundeservice. Den har
ingen adgang til mail, Teams, CRM, kundesystemer eller andre forretnings-
systemer, og den udfører ingen handlinger i dem.

## Hvilke data

| Data | Hvor fra | Persondata? |
|---|---|---|
| Artikler og websider | Offentlige kilder (kildeliste i Admin → Kilder) | Kan indeholde navne på talspersoner fra artiklerne; radaren gemmer organisationer, ikke personer |
| Manuelt uploadede dokumenter | Admin uploader | Afhænger af dokumentet — se nedenfor |
| OK-tal i beslutningsoplægget | Indtastes manuelt af Admin | Nej (aggregerede tal) |
| Brugerkonti | Supabase Auth (e-mail, rolle) | Ja, medarbejderes e-mail |
| Audit-log | Alle beslutninger (aktør, før/efter) | Bruger-id |

**Kundedata:** Radaren er ikke bygget til kundedata og må ikke få dem.
Interne dokumenter (fx eksport fra FocalScope) skal ligge i en kilde markeret
**intern** (Admin → Kilder → "Markér som intern"); deres analyser vises som
intern analyse og aldrig som markedsviden. **[afklares]** Om interne
dokumenter overhovedet må uploades, før radaren kører i OK's miljø — anbefalet
svar: nej, kun anonymiserede tal.

## Hvor det kører i dag (prototype)

| Del | Leverandør | Bemærkning |
|---|---|---|
| Database og login | Supabase (staging-projekt) | Region **[afklares]** |
| API og kørsler | Render (free tier) | Region **[afklares]**; sover ved inaktivitet |
| Web | Vercel | Kun visning; ingen data lagres i Vercel |
| AI-model | Anthropic API | Dokumenttekst sendes til modellen. Databehandleraftale og vilkår for brug af data **[afklares]** |

Konti og betaling ligger i dag uden for OK's leverandøraftaler. Det er den
vigtigste ting at rette, før radaren bruges bredt.

## Sikkerhed i dag

- Login via Supabase Auth; oprettelse af nye brugere er slået fra. Roller:
  Læser, Reviewer, Admin. Alle API-kald kræver gyldig token.
- Hemmeligheder (AI-nøgle, databaseadgang) ligger kun i hostingens
  miljøvariabler — aldrig i koden (secret scanning i CI).
- Kildetekst behandles som utroværdig: instruktioner i artikler følges
  aldrig, og AI-svar valideres mod et fast skema.
- Al AI-publiceret viden er mærket "AI-publiceret"; alle beslutninger
  skrives i en audit-log.

## Plan for at flytte ind i OK's miljø

Radaren er bygget portabelt: standard PostgreSQL, Docker-images for web og
API, ingen proprietær platformlogik. Forslag:

1. Database i OK's Azure/PostgreSQL (eller OK-ejet Supabase-projekt i EU).
2. API og web som containere i OK's miljø; login via OK's Entra ID
   **[afklares: kræver OIDC-opsætning]**.
3. AI-model via OK's eksisterende aftale (fx Azure OpenAI eller Anthropic via
   OK-kontrakt) — modellen udskiftes med én miljøvariabel.
4. Betaling og konti flyttes til OK; prototype-miljøet nedlægges.

## Åbne punkter til IT

1. Regioner for Supabase og Render (EU?).
2. Databehandleraftaler med de leverandører, der behandler data.
3. Hvilken AI-leverandør OK foretrækker, og om dokumenttekst fra offentlige
   kilder må sendes dertil.
4. Ejerskab: koden ligger i et privat GitHub-repo **[afklares: overdrages til
   OK's organisation]**.
5. Om interne, anonymiserede tal må bruges i radaren.
