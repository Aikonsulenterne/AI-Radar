# AI Radar — Product & Design Master

## 0. Status og source of truth

Dette er den autoritative produkt- og designspecifikation for AI Radar. Den erstatter tidligere produktbriefs og løse noter. Den eksisterende HTML-prototype, README og `colors_and_type.css` er high-fidelity designreferencer, men prototypefunktioner er kun MVP-scope, når det står eksplicit her.

Ved konflikt gælder: låste beslutninger i denne fil, derefter denne fil, Technical Build Master, designreferencer og til sidst ældre noter.

## 1. Vision

AI Radar er et internt, evidensbaseret technology-intelligence- og beslutningsprodukt. Det skal hjælpe OK med at forstå:

1. Hvordan større danske og skandinaviske virksomheder adopterer AI.
2. Hvilke AI-capabilities der findes og modnes nu.
3. Hvilke udviklinger der kan blive relevante de næste 1–3 år.
4. Hvor stærk dokumentationen er.
5. Hvad der potentielt er relevant for OK.
6. Hvad OK bør holde øje med, undersøge, lave business case på, teste eller skalere.

AI Radar er ikke en nyhedsportal, et linkkatalog, et leverandørkatalog eller et generisk BI-dashboard.

Den centrale værdikæde er:

**Kilde → Dokument → Atomic Claim → Evidens → Verificeret signal → Adoption/teknologi → Relevans for OK → Opportunity → Handling**

Det vigtigste spørgsmål er: **Hvor ved vi det fra?**

## 2. Låste produktprincipper

### Evidens før AI

Alle publicerede faktuelle oplysninger skal kunne spores til en registreret kilde, et konkret dokument, et præcist evidensuddrag og et review-resultat.

### Fakta, analyse og anbefaling adskilles

- **Fakta:** direkte understøttet af kilder.
- **Analyse:** fortolkning eller syntese.
- **Anbefaling:** foreslået næste skridt.

De tre typer skal adskilles både semantisk og visuelt.

### Capability før leverandør

Produktet starter med problemer, use cases og capabilities. Leverandører vises sekundært og kun med dokumenteret relation.

### Human-in-the-loop

AI må foreslå, udtrække, klassificere, matche og sammenfatte. AI må ikke alene godkende væsentlige claims, investeringer, business cases eller implementeringer.

### Open source og portabilitet

Applikationsstacken skal så vidt muligt bygges med open source-komponenter og åbne standarder. Centrale komponenter skal kunne self-hostes eller udskiftes uden redesign af domænemodellen.

**Godkendt undtagelse:** Vercel bruges til hosting af Next.js-frontenden. Vercel må ikke blive en uerstattelig teknisk afhængighed.

### Start smalt

MVP'en skal bevise intelligence-metoden før produktet udvides.

## 3. Brugere og roller

### Reader

Kan se publicerede signaler, cases, teknologier, opportunities, kilder og briefingvisning. Kan ikke godkende claims eller administrere sources.

### Reviewer

Kan desuden gennemgå dokumenter, rette og godkende claims, afvise claims, markere behov for yderligere dokumentation og håndtere mulige dubletter og konflikter.

### Admin

Kan desuden administrere Source Registry, genkøre fejlede jobs, vedligeholde taxonomier og administrere roller.

Autorisation håndhæves server-side.

## 4. Centrale begreber

- **Source:** registreret kilde eller endpoint.
- **Document:** konkret hentet eller uploadet indholdsenhed.
- **Atomic Claim:** ét afgrænset dokumenterbart udsagn.
- **Evidence:** relationen mellem claim og præcist dokumentuddrag.
- **Signal:** publicerbar intelligence baseret på reviewede claims.
- **Adoption Case:** samling af claims om en virksomheds konkrete AI-anvendelse.
- **Technology:** kurateret AI-capability.
- **Opportunity:** ekstern evidens koblet til et reelt OK-problem og et næste skridt.
- **Briefing:** kort, redigerbar visning af publicerede signaler og opportunities.

## 5. MVP-mål

MVP'en skal bevise, at systemet kan:

1. Finde nyt indhold i kuraterede kilder.
2. Identificere relevante dokumenter.
3. Udtrække korrekte claims med præcise evidensuddrag.
4. Understøtte hurtigt menneskeligt review.
5. Publicere sporbar intelligence.
6. Vise intelligence efter virksomhed og teknologi.
7. Skabe reelle opportunity-kandidater for OK.

Succeskriteriet er få, nye, relevante og veldokumenterede signaler, ikke stor volumen.

## 6. MVP-dækning

Målsætning ved lancering:

- 20–30 større skandinaviske virksomheder.
- 8 centrale teknologier.
- 8–10 relevante leverandører som relaterede entities.
- 40–60 kuraterede source endpoints.

Tallene er dækningsmål. Der skal kun bygges få generiske ingestion-metoder.

### Startteknologier

1. Agent Assist
2. Knowledge AI
3. Conversation Intelligence
4. Automated QA
5. Voice AI
6. Knowledge-gap Detection
7. Workflow Automation
8. Agentic AI

## 7. Produktområder

UI'et skal følge den eksisterende prototype visuelt. MVP-funktionaliteten koncentreres i følgende områder.

### Overblik / Radar

Viser:

- vigtigste publicerede signaler
- kompakte KPI'er med kilde eller definition
- teknologier i NU, NÆSTE og HORIZON
- dokumentationsstyrke
- relevante adoption cases
- opportunity-kandidater
- anbefalede næste handlinger

### AI-adoption

Viser:

- virksomheder og dokumenterede cases
- capability og use case
- implementeringsstadie
- teknologi og leverandør, når dokumenteret
- dokumenteret effekt, når den findes
- evidens og original kilde
- potentiel læring tydeligt markeret som analyse

Filtre: land, branche, capability, implementeringsstadie og dokumentationsstyrke.

### Teknologiradar

Viser technologies i tre horizons:

- **NU:** relativt modent og anvendeligt i dag.
- **NÆSTE:** bør undersøges i den nærmeste planlægningshorisont.
- **HORIZON:** kan få væsentlig betydning inden for 1–3 år, men har højere usikkerhed.

Teknologiprofilen skal holde følgende adskilt:

- teknologisk modenhed
- skandinavisk adoption
- dokumenteret forretningsværdi
- momentum/hype
- overførbarhed til OK

### Opportunities

Pipeline:

- Identificeret
- Undersøges
- Business case
- Pilot
- Skalering
- Afsluttet

En MVP-opportunity indeholder:

- titel
- problem eller behov hos OK
- relaterede signaler/claims
- relevanshypotese
- evidenshuller
- anbefalet næste handling
- status
- ejer

AI må foreslå. Et menneske skal godkende.

### Kilder og metode

Viser Source Registry, kildetyper, seneste kontrol, status og provenance-principper. Hver observation skal kunne åbnes tilbage til dokumentation.

### Administration / Review

Review Queue viser original kilde, dokumentmetadata, foreslåede claims, evidensuddrag, entities samt mulige dubletter og konflikter.

Handlinger:

- Approve
- Edit and approve
- Needs corroboration
- Reject
- Merge duplicate candidate
- Mark possible contradiction

### Briefing

Briefing er en enkel genereret visning, ikke et selvstændigt subsystem. Den kan indeholde:

- tre vigtigste udviklinger
- nye verificerede skandinaviske cases
- teknologier i bevægelse
- opportunities
- 3–5 næste skridt
- kilder

## 8. Primær brugerrejse

1. Brugeren ser et signal på Overblik.
2. Brugeren åbner signalet.
3. Brugeren ser fakta, analyse, anbefaling og dokumentationsstyrke.
4. Brugeren åbner claims, evidensuddrag og original kilde.
5. Brugeren går til relateret teknologi og skandinaviske cases.
6. Brugeren ser koblingen til et OK-problem.
7. Brugeren opretter eller godkender en opportunity-kandidat.
8. Opportunity'en kan inkluderes i briefingvisningen.

**Opdag → Forstå → Kontrollér dokumentation → Vurdér → Prioritér → Handl**

## 9. Adoption Case

Skal vise:

- virksomhed, land og branche
- capability og use case
- implementeringsstadie
- vendor/platform, hvis dokumenteret
- tidsreference, hvis dokumenteret
- effekt, hvis eksplicit dokumenteret
- evidens og reviewstatus
- potentiel læring som analyse

Manglende fakta vises som **Ikke dokumenteret**. Manglende effekt vises som **Ingen dokumenteret effekt fundet**.

Implementeringsstadier:

- Experiment
- Pilot
- Production
- Scale
- Unknown

## 10. Opportunities og OK-problemer

En opportunity skal bygge på:

**Ekstern udvikling × dokumentation × relevant OK-problem = opportunity-kandidat**

MVP starter med en enkel problem-taxonomi:

- manuel QA
- store mailmængder
- knowledge gaps
- efterbehandling
- genhenvendelser
- routing
- onboarding
- repetitive henvendelser

AI Radar kvalificerer muligheder. Produktet erstatter ikke business case-, projekt-, pilot- eller porteføljestyring.

## 11. Evidens i brugerfladen

Brugeren ser primært:

- **Stærk dokumentation:** primære, uafhængige eller flere reelt uafhængige kilder.
- **Begrænset dokumentation:** dokumenteret, men hovedsageligt fra én part eller oprindelse.
- **Tidligt signal:** interessant, men utilstrækkeligt dokumenteret.
- **Modstridende:** relevante kilder peger i forskellige retninger.

Kildetyper:

- primary
- independent_analysis
- vendor_case
- vendor_claim
- media
- research
- early_signal

Kildetype er ikke det samme som sandhedsstatus.

## 12. Designretning

Den vedlagte UI-prototype er high-fidelity reference for layout, navigation, komponenter, spacing, drawers, tabeller, states og interaktioner.

Brug OK's tokens fra `colors_and_type.css`, herunder burgundy, rød, varm cream, OKfamily og Fellix, når fontlicenserne er tilgængelige.

Bevar:

- desktop-first layout
- fast venstreside-navigation
- sticky topbar
- kort, tabeller og stakbaserede drawers
- tydelig focus state
- fakta/analyse/anbefaling adskilt med form og labels
- rolige animationer

Undgå AI-glow, gradients som standard, robotillustrationer, glasmorfisme og UI, der ligner en nyhedsside.

Tilgængelighed: WCAG 2.1 AA, tastaturnavigation, focus trap, Escape-lukning, fokusretur og status, der ikke kun kommunikeres med farve.

## 13. Prototype og MVP-afgrænsning

Følgende prototypefunktioner må gerne have visuel plads, men kræver ikke fuld backendfunktionalitet i første build:

- avanceret leverandørsammenligning
- planlagte briefinger og skabelonbibliotek
- notifikationscenter
- gemte filtre
- følg virksomhed
- comments og aktivitetsfeed
- avanceret global semantisk søgning

Use cases og leverandører kan vises gennem relationer og profiler, selv hvis de ikke har komplette selvstændige workflows i MVP'en.

## 14. Mockdata

Prototype-data er demodata. Virkelige navne gør ikke observationerne faktuelle.

- Seeddata markeres `is_demo`.
- Demo-data må ikke publiceres som production intelligence.
- Faktiske cases kræver kilde og evidens.
- AI må ikke udfylde ukendte facts.
- Mockdata skal matche den rigtige datamodel.

## 15. Ikke i MVP

- autonom researchagent
- bred automatisk web discovery
- multi-agent orchestration
- MCP-servere
- graph database
- Azure AI Search
- separat vector database
- automatisk endelig contradiction-afgørelse
- automatisk claim-publicering
- automatisk opportunity-godkendelse
- fuldt problemregister
- fuld business case- og projektstyring
- avanceret briefingworkflow
- kundedata eller PII
- paywall-bypass

## 16. Product acceptance criteria

MVP er produktmæssigt klar, når:

1. En bruger kan følge en reel kæde fra source til opportunity.
2. Ingen publiceret fakta vises uden provenance.
3. Manglende data vises som manglende og gættes ikke.
4. Fakta, analyse og anbefaling kan skelnes.
5. Reviewer kan rette, godkende og afvise claims.
6. Reader kan undersøge signaler efter virksomhed og teknologi.
7. Opportunities er koblet til ekstern evidens og OK-problem.
8. UI'et følger designreferencen på desktop og laptop.
9. Centrale loading-, empty-, partial-, unauthorized- og error states findes.
10. Demo-data kan ikke forveksles med production intelligence.

## 17. Ændringsregel

Hvis en ny idé modsiger masteren:

1. Identificér konflikten.
2. Forklar konsekvensen.
3. Anbefal én retning.
4. Træf beslutning ved væsentlige ændringer.
5. Opdatér begge masterfiler konsistent.
