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

**Ændret beslutning (2026-10-08, produktejer):** Radarens hovedopgave er at vise, hvilke leverandører der tilbyder hvilken AI-teknologi til (danske) kundecentre, og hvem der bruger den. Leverandørtilbud er derfor førsteklasses indhold: claim extraction udtrækker `OFFERS_CAPABILITY` (leverandør → kurateret capability, produktnavn), og siden *Leverandører* viser landskabet pr. capability med dokumenterede kunder. Tilbud er stadig evidensbaserede (ordret uddrag, kun godkendte claims), tæller aldrig som adoption og giver ingen adoption case, og udsagn fra leverandørens egne kilder mærkes som leverandørens. Radaren skal også finde capabilities, OK ikke kender endnu: en capability uden for den kuraterede liste oprettes som kandidat (*Nyt i markedet*, uden horisont og uden opfundet definition), og en Admin optager den på radaren eller afviser den.

### Human-in-the-loop

AI må foreslå, udtrække, klassificere, matche og sammenfatte. AI må ikke alene godkende væsentlige claims, investeringer, business cases eller implementeringer.

**Ændret beslutning (2026-09-29, produktejer):** Claims, adoption cases og signaler kan publiceres fuldt automatisk (indstillingen `AUTO_PUBLISH`). AI godkender da sine egne claims og publicerer case og signal uden menneskelig kontrol. Alt sådant indhold markeres synligt som *AI-publiceret* / *Automatisk godkendt af AI*, og evidensreglerne gælder fortsat: kun claims med ordret evidensuddrag, og signalets faktaafsnit må kun gengive claims. Opportunities, investeringer, business cases og implementeringer kræver fortsat menneskelig godkendelse. Med `AUTO_PUBLISH` slået fra gælder det oprindelige review-flow.

### Open source og portabilitet

Applikationsstacken skal så vidt muligt bygges med open source-komponenter og åbne standarder. Centrale komponenter skal kunne self-hostes eller udskiftes uden redesign af domænemodellen.

**Godkendt undtagelse:** Vercel bruges til hosting af Next.js-frontenden. Vercel må ikke blive en uerstattelig teknisk afhængighed.

### Start smalt

MVP'en skal bevise intelligence-metoden før produktet udvides.

**Fokus (besluttet 2026-10-06, produktejer):** Radaren fokuserer på OK's kundecenter. Den skal besvare to spørgsmål: hvilken AI- og automatiseringsteknologi findes på markedet til kundeservice og kundecentre, og hvordan andre, især danske og nordiske, kundecentre bruger og adopterer AI. Relevansklassifikationen frasorterer generel AI-forskning, AI i andre forretningsfunktioner og modelnyheder uden kundeserviceperspektiv, og kildeporteføljen vægter kundecenter-medier og danske søgefeeds frem for generelle tech- og leverandørblogs. Leverandørers egne tal skal fremgå som leverandørens.

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

## 18. Beslutning 2026-10-13: den forenklede radar

**Primær bruger:** direktøren for Salg, Kundeservice og Support i OK a.m.b.a.
Sekundær bruger: AI-konsulenten, der driver radaren (kilder, opdatering,
skjul forkerte fund). Beslutningen erstatter navigation og begreber fra
§§ 5–11 i brugerens visning; datamodel og gamle moduler bliver liggende.

Radaren besvarer tre spørgsmål inden for **Salg, Kundeservice og Support**:

1. Hvilken AI-teknologi findes der på markedet, som OK kan bruge?
2. Hvordan bruger andre virksomheder AI, og hvordan har de indført den?
3. Hvad kan OK lære af det, og hvad er næste skridt?

Navigation (højst fire punkter): **Til OK** (forside), **Teknologier**,
**Sådan gør andre** og **Kilder** (kun Admin). Et områdefilter (Alle / Salg
/ Kundeservice / Support) går igen på alle sider.

- **Til OK:** "Det vigtigste lige nu" (højst tre punkter med kilde) og ét
  kort pr. problem på OK's problemliste: teknologier, effekt hos andre,
  sammenlignelige cases, hvem man kan tale med og ét lille næste skridt.
  Kan printes med én side pr. område.
- **Teknologier:** ét kort pr. teknologi med dansk forklaring,
  forretningsværdi, leverandører (markeret "Dansk", når kilden siger det) og
  antal cases. Nye teknologier står under "Nyt i markedet".
- **Sådan gør andre:** ét kort pr. case: virksomhed, land, branche, hvad de
  gjorde, teknologi, leverandør, fase, omfang, effekt (ordret, med KPI og
  hvem der siger det), læring og kilde. Danske og nordiske cases og cases med
  effekt står først.

Regler: hver påstand har en kilde; AI-indhold publiceres automatisk og
mærkes "AI-sammenfattet · tjek kilden"; ukendt er "Ikke oplyst";
leverandørens egne tal markeres; interne OK-dokumenter vises aldrig som
markedsviden; konsulenten kan skjule et forkert fund (intet slettes, alt
står i audit-loggen). Problemlisten og teknologikataloget er kuratering i
`apps/api/app/market/catalog.py`.

## 19. Beslutning 2026-10-13: designhandoff v2 (erstatter §18's visning)

Kilde: `docs/design/design_handoff_ai_radar_v2/README.md` (godkendt
produktbeslutning; Til OK er high-fidelity). Hovedpunkter:

- Målet: en direktør, der ikke har set radaren før, kan besvare de tre
  spørgsmål på **60 sekunder**. Der kommer **ikke** et Indsigter-modul;
  indsigterne står i "Det skal du vide" på Til OK.
- Navigation i en burgundy topbjælke: **Teknologier · Sådan gør andre · Til
  OK · Kilder (Admin)**. Forsiden er Til OK.
- **Fælles statusmodel**, beregnet af data og aldrig skrevet i hånden:
  *Klar nu* (mindst 2 cases i drift eller skaleret og mindst én uafhængig
  kilde), *Værd at afprøve* (cases findes, men kun i pilot eller kun med
  leverandørens tal), *Hold øje med* (ingen cases). Sortering overalt: Klar
  nu → Værd at afprøve → Hold øje med, derefter relevans for OK.
- **Til OK:** Det skal du vide (3 punkter med kilde) · Det foreslår vi (højst
  3 skridt med ejer og varighed) · Det skal du tage stilling til (højst 2
  ja/nej-spørgsmål) · én tabel pr. område (Problem, Bedste teknologi +
  status, Stærkeste bevis, Næste skridt; foldes ud med Hvorfor beviset ligner
  OK, Flere cases, Hvem kan vi tale med) · Endnu ikke dokumenteret på én
  linje. Hver case højst én gang på siden. Print højst 2 A4-sider.
- **Teknologier:** Nyt på markedet (højst 3), derefter Klar nu / Værd at
  afprøve / Hold øje med. Kort: navn, status, hvad den gør, "Det kan betyde
  for OK" (analyse), højst 3 leverandører + "N flere", stærkeste bevis.
  Produkter, links og "✓ Dansk" vises, når kortet foldes ud. Tabellen
  Leverandører på markedet (type, teknologier, dansk). Ingen "Skjul" her.
- **Sådan gør andre:** filtre Alle / Danmark / Norden (inkl. Danmark) /
  Resten af verden + teknologi; sorteret efter lighed med OK. Kort med trin
  idé → pilot → drift → skaleret og effekt ordret; læring, omfang, start og
  kilde ved udfoldning.
- **Kilder (Admin):** tabel med type, senest læst og relevante artikler; én
  primær knap "Opdatér radaren" med toast bagefter; "Skjul" for cases og
  leverandører ligger her.
- Fakta (solid burgundy kant), analyse (stiplet ramme) og anbefaling (solid
  rød kant) skelnes på form. "AI-sammenfattet · tjek kilden" én gang pr.
  sektion. Ingen tomme kort, ingen emoji, højst 20 ord pr. sætning i
  opsummeringer.

Afvigelse fra handoffen, bevidst: radaren dækker fortsat salg og support ud
over kundeservice (beslutning 2026-10-13, §18), så relevansfilteret og
problemlisten omfatter salg.

## 20. Beslutning 2026-10-14: godkendelse af Til OK og OK's systemer

- **Konsulenten godkender Til OK, før direktøren ser den.** Kørsler skriver en
  kladde; direktøren ser den senest godkendte version. "Godkend og send"
  sender forsiden som mail, når SMTP er sat op. Bevidst afvigelse fra v2 §8
  ("intet review-flow"): én fejl på den side, der træffes beslutninger på,
  koster mere end fem minutters kontrol. Teknologier og Sådan gør andre
  publiceres fortsat automatisk.
- **OK i dag:** FocalScope (kundeservicesystem) og et legacy G4-system. Til
  OK-prompten får profilen med, så forslag passer til OK's systemer og siger
  det, når en løsning kræver integration eller skift. Radaren følger, hvad
  FocalScope lancerer af AI, og markerer FocalScope som "OK bruger i dag".
- **Case-kildepakke:** 16 ekstra nyhedsfeeds med fokus på danske og nordiske
  cases, brancher som OK, CX-konferencer og FocalScope.
