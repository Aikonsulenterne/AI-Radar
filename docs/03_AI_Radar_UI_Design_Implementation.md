# AI Radar — UI & Design Implementation Master

## 0. Formål og status

Dette dokument er den autoritative UI- og designspecifikation for implementeringen af AI Radar i Claude Code.

Dokumentet supplerer:

1. `01_AI_Radar_Product_Design.md`
2. `02_AI_Radar_Technical_Build.md`

De tre filer skal læses samlet. Product Master definerer formål, scope og produktadfærd. Technical Master definerer arkitektur, data, sikkerhed og deployment. Denne fil definerer det konkrete UI, designsystemet, komponenterne, states og interaktionerne.

Denne fil er tilpasset den nye MVP-arkitektur med Next.js, Vercel, Supabase og FastAPI. Den tidligere Claude Design-prototype er designreference, men prototypekoden er ikke produktionskode og må ikke kopieres direkte.

### Source-of-truth-rækkefølge

Ved konflikt gælder:

1. Låste beslutninger i Product Master og Technical Master.
2. Denne UI & Design Implementation Master.
3. `colors_and_type.css` som tokenreference.
4. `AI Radar.dc.html` som high-fidelity visuel og interaktionsmæssig reference.
5. Det oprindelige Claude Design-handoff og README.

Claude Code skal ikke anvende neutrale placeholder-tokens, når tokens i dette dokument er tilgængelige.

---

## 1. Implementeringsinstruktion til Claude Code

Claude Code skal:

- genskabe AI Radar som et high-fidelity Next.js-interface
- anvende TypeScript strict mode
- implementere designet med genbrugelige React-komponenter
- anvende CSS-variablerne i dette dokument som fælles design tokens
- bruge OKfamily til displaytekst og Fellix til brødtekst, når fontfilerne er tilgængelige og licenseret til projektet
- anvende de definerede fallbacks, hvis fontfilerne ikke er staged
- behandle `AI Radar.dc.html` som visuel reference, ikke som kode, der skal kopieres
- undgå én monolitisk komponent og undgå inline styles som primær stylingstrategi
- forbinde UI-komponenter til typed API-kontrakter frem for hardcodede production-data
- mærke seed- og demodata tydeligt i datalaget
- bevare skellet mellem fakta, analyse og anbefaling i alle relevante visninger
- implementere MVP-funktioner fuldt og øvrige prototypefunktioner som enten simple visninger eller eksplicitte placeholders uden opdigtet backendadfærd

### Må ikke gøres

- Genskab ikke prototype-DSL'en, `DCLogic`, `sc-if` eller `sc-for`.
- Kopiér ikke hele prototypen ind i én React-komponent.
- Erstat ikke brandfarverne med standard Tailwind-, shadcn- eller browserfarver.
- Brug ikke gradienter, AI-glow, glassmorphism eller robotillustrationer.
- Præsenter aldrig demodata som verificeret intelligence.
- Brug ikke farve som eneste statusmarkør.

---

## 2. Visuel retning

AI Radar skal opleves som:

- professionelt
- skandinavisk
- roligt
- moderne
- datadrevet
- ledelsesegnet
- redaktionelt
- informationsrigt uden at virke tungt

Produktet må ikke ligne:

- en nyhedsportal
- et klassisk BI-dashboard
- et AI-produktkatalog
- en statisk leverandørmatrix
- en Gartner-lignende rapport

Den visuelle kerne er:

- varm cream som sidebaggrund
- hvid som kortflade
- burgundy som navigation og redaktionel tyngde
- klar rød som handlingsfarve
- få semantiske accentfarver
- tydelig typografisk hierarki
- begrænsede, funktionelle animationer

---

## 3. Brand tokens

Opret en central fil, eksempelvis:

`apps/web/src/styles/tokens.css`

Indholdet skal mindst være:

```css
:root {
  --ok-200: #F7EFEB;
  --ok-600: #FF3C3C;
  --ok-800: #460019;

  --ok-cream: var(--ok-200);
  --ok-red: var(--ok-600);
  --ok-burgundy: var(--ok-800);

  --ok-red-deep: #AA2825;
  --ok-red-dark: #8C0000;
  --ok-red-pale: #FFF2F2;
  --ok-red-tint: #FFE6E6;
  --ok-red-soft: #FFBEBE;
  --ok-red-mid: #FF8C8C;
  --ok-burgundy-deep: #23000D;
  --ok-cream-warm: #F2E7E1;
  --ok-cream-cool: #FFFAF7;

  --ok-ink: #1A1614;
  --ok-ink-soft: #4D433E;
  --ok-ink-mute: #736762;
  --ok-stone: #998C85;
  --ok-stone-soft: #BFB2AA;
  --ok-stone-pale: #E6D9D2;
  --ok-white: #FFFFFF;
  --ok-black: #000000;

  --ok-blue: #0071C2;
  --ok-blue-mid: #4BB4FF;
  --ok-blue-light: #CDEBFF;
  --ok-blue-pale: #F2F9FF;
  --ok-green: #006626;
  --ok-green-light: #CFFDE1;

  --bg: var(--ok-cream);
  --bg-elev: var(--ok-white);
  --bg-inverse: var(--ok-burgundy);
  --bg-accent: var(--ok-red);
  --fg: var(--ok-ink);
  --fg-soft: var(--ok-ink-soft);
  --fg-mute: var(--ok-ink-mute);
  --fg-on-dark: var(--ok-cream);
  --fg-on-accent: var(--ok-white);
  --fg-accent: var(--ok-red);
  --border: var(--ok-stone-pale);
  --border-strong: var(--ok-stone);
  --border-on-dark: rgba(247, 239, 235, 0.15);
  --state-success: var(--ok-green);
  --state-info: var(--ok-blue);
  --state-warn: #D08A1F;
  --state-danger: var(--ok-red-deep);

  --font-display: 'OKfamily', Georgia, 'Times New Roman', serif;
  --font-body: 'Fellix', Inter, 'Helvetica Neue', Arial, system-ui, sans-serif;
  --font-mono: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;

  --t-display-1: clamp(56px, 6.6vw, 96px);
  --t-display-2: clamp(40px, 4.4vw, 64px);
  --t-h1: clamp(32px, 3.2vw, 44px);
  --t-h2: clamp(24px, 2.4vw, 32px);
  --t-h3: 20px;
  --t-body-lg: 22px;
  --t-body: 18px;
  --t-body-sm: 15px;
  --t-caption: 13px;
  --t-eyebrow: 12px;

  --lh-tight: 1.05;
  --lh-snug: 1.2;
  --lh-body: 1.45;
  --lh-loose: 1.6;
  --tracking-tight: -0.01em;
  --tracking-eyebrow: 0.12em;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;
  --space-8: 64px;
  --space-9: 96px;

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-pill: 999px;

  --shadow-sm: 0 1px 2px rgba(70, 0, 25, 0.06);
  --shadow-md: 0 4px 12px rgba(70, 0, 25, 0.08), 0 1px 2px rgba(70, 0, 25, 0.05);
  --shadow-lg: 0 12px 32px rgba(70, 0, 25, 0.12), 0 2px 4px rgba(70, 0, 25, 0.06);
}
```

### Tokenregel

Brug tokens frem for rå hexværdier i komponenter. Der må kun anvendes rå værdier, når en specifik semantisk variant endnu ikke har et token. Hvis samme rå værdi bruges mere end én gang, oprettes et token.

---

## 4. Fontimplementation

### Godkendte fonte

- Display: OKfamily
- Body/UI: Fellix

Fontfilerne er licenserede og skal hentes fra OK's godkendte brandpakke. De må ikke hentes fra en tilfældig ekstern kilde.

Forventet struktur:

```text
apps/web/public/fonts/
├── OKfamily-Light.ttf
├── OKfamily-Regular.ttf
├── OKfamily-Medium.ttf
├── OKfamily-Semibold.otf
├── OKfamily-Bold.ttf
├── Fellix-Light.ttf
├── Fellix-Regular.ttf
└── Fellix-SemiBold.otf
```

Implementér fonte centralt med `next/font/local`, når filer findes. Brug følgende fallbacks, indtil fontfilerne er staged:

- OKfamily fallback: Georgia, Times New Roman, serif
- Fellix fallback: Inter, Helvetica Neue, Arial, system-ui, sans-serif

Claude Code må ikke standse hele buildet, fordi fontfilerne mangler. Buildet skal fungere med fallbacks, men skal tydeligt rapportere, at pixel-fidelity først kan accepteres, når de licenserede fontfiler er tilført.

---

## 5. Global layout

### Desktop

- Viewportmål: 1440 px.
- Understøttet minimum for desktop/laptop: cirka 1024 px.
- Sidebaggrund: `--ok-cream`.
- Sidebar: 248 px, sticky, fuld viewporthøjde.
- Topbar: 64 px, sticky.
- Main: `padding: 26px 24px 64px`.
- Indholdscontainer: `max-width: 1392px`, centreret.
- Drawer: højre side, `width: min(700px, 94vw)`.

### Tablet

- Sidebar kan blive kompakt eller åbnes som navigationsoverlay.
- Tabeller må få vandret scroll eller skifte til cards.
- Cards skifter fra 4/3 kolonner til 2 kolonner.

### Mobil

Mobil er sekundært for MVP. Layoutet må ikke bryde, men fuld optimering er ikke et MVP-acceptance criterion.

---

## 6. Navigation tilpasset nyt MVP-scope

Den eksisterende prototype har otte navigationselementer. Det nye produkt- og technical scope skal stadig respektere prototypens informationsarkitektur, men funktionaliteten prioriteres sådan:

### Primær navigation

1. Overblik
2. AI-adoption
3. Teknologiradar
4. Opportunities
5. Briefing
6. Kilder & metode

### Sekundært eller profilbaseret

- Use cases vises som relationer, filtre og detaljer. Et selvstændigt modul kan eksistere som read-only/enkelt MVP-view, men er ikke en forudsætning for den centrale evidenskæde.
- Leverandører vises som profiler og relationer. Avanceret sammenligning er ikke MVP.

### Administration

Administrationsnavigation skal være rollebeskyttet og indeholde:

- Review
- Sources

### Sidebar

- Baggrund: `--ok-burgundy`.
- Brand: “AI Radar” i displayfont, 27 px, cream.
- Undertekst: “TECHNOLOGY INTELLIGENCE”, 12 px, 600, uppercase, `--ok-red-mid`.
- Nav-rækker: 10 px 12 px padding, 8 px radius, 14.5 px tekst.
- Aktiv række: `rgba(255,60,60,0.16)`, hvid tekst, 600 vægt, rød-mid prik.
- Hover: `rgba(247,239,235,0.1)`.
- Nederst vises seneste opdatering, aktive kilder og bruger/session, når data findes.

### Topbar

Skal mindst indeholde:

- aktuel sidetitel
- global eller kontekstuel søgning
- relevante filtre
- bruger/session-menu

Periode, land og branche vises kun på sider, hvor filtrene har effekt. Notifikationer og “Tilføj observation” må ikke vises som fungerende handlinger, før backendadfærden findes.

---

## 7. Typografisk hierarki

- Hero H1: 38 px, display, weight 400.
- Side H1: 34 px, display, weight 400.
- H2: 24 px, display.
- Drawer-title: 26 px, display.
- Store card titles: 21–22 px, display.
- Standard card titles: 18–20 px.
- Intro: 15–15.5 px.
- Brødtekst: 13.5–14 px i UI-kort.
- Input/knap: 13–13.5 px.
- Tabel: 13 px.
- Chips/badges: 11.5–12 px.
- Eyebrow: 11–12 px, 600, uppercase, tracking 0.12em.

Displayhierarki skabes primært med størrelse, ikke tunge fontvægte.

---

## 8. Semantiske visuelle mønstre

### Dokumenteret fakta

- Hvid baggrund.
- 1 px border.
- 4 px venstrekant i `--ok-burgundy`.
- Label: “Dokumenteret fakta” eller tilsvarende.

### Analyse

- `--ok-cream-cool` baggrund.
- Stiplet border i `--ok-stone-soft`.
- Label: “Analyse, ikke fakta”.

### Anbefaling

- Hvid baggrund.
- 4 px venstrekant i `--ok-red`.
- Label: “Anbefaling” eller “Næste skridt”.

Dette er et ufravigeligt designprincip. Farve alene er ikke tilstrækkeligt.

---

## 9. Evidens- og statusdesign

### Evidens A til E

- A: tekst `#006626`, baggrund `#CFFDE1`, border `#9FE0B8`.
- B: tekst `#0071C2`, baggrund `#F2F9FF`, border `#CDEBFF`.
- C: tekst `#8A5A10`, baggrund `#FBF0DC`, border `#E8D4AE`.
- D: tekst `#4D433E`, baggrund `#F2E7E1`, border `#E6D9D2`.
- E: tekst `#998C85`, baggrund `#FFFAF7`, border `#E6D9D2`.

### Brugervenligt dokumentationsniveau

- Stærk dokumentation
- Begrænset dokumentation
- Tidligt signal
- Modstridende

De brugervenlige labels skal kunne åbne de underliggende A–E metadata, claims og kilder.

### Verifikation

Brug altid symbol og tekst:

- ✓ Verificeret
- ~ Delvist verificeret
- – Ikke verificeret
- · Ikke relevant

### Horizons

- NU: grøn tekst og grøn lys baggrund.
- NÆSTE: varm gul tekst og lys gul baggrund.
- HORIZON: burgundy tekst og cream-warm baggrund.

---

## 10. Komponentbibliotek

Placér komponenter efter ansvar, eksempelvis:

```text
apps/web/src/components/
├── layout/
│   ├── app-shell.tsx
│   ├── sidebar.tsx
│   └── topbar.tsx
├── ui/
│   ├── button.tsx
│   ├── badge.tsx
│   ├── card.tsx
│   ├── drawer.tsx
│   ├── select.tsx
│   ├── table.tsx
│   ├── tabs.tsx
│   └── toast.tsx
├── evidence/
│   ├── evidence-badge.tsx
│   ├── documentation-level.tsx
│   └── provenance-list.tsx
├── signals/
│   ├── signal-card.tsx
│   └── signal-drawer.tsx
├── adoption/
│   ├── adoption-case-card.tsx
│   ├── adoption-table.tsx
│   └── company-profile.tsx
├── technologies/
│   ├── horizon-board.tsx
│   ├── technology-card.tsx
│   └── technology-profile.tsx
├── opportunities/
│   ├── opportunity-card.tsx
│   ├── opportunity-pipeline.tsx
│   └── opportunity-detail.tsx
├── review/
│   ├── review-queue.tsx
│   ├── claim-review-card.tsx
│   └── source-document-panel.tsx
└── states/
    ├── empty-state.tsx
    ├── error-state.tsx
    ├── loading-state.tsx
    └── unauthorized-state.tsx
```

Komponenterne må gerne bruge et open source primitive-bibliotek, hvis det ikke ændrer det visuelle resultat. Styling skal fortsat følge OK-tokens.

---

## 11. Overblik

### Hero

Standardvarianten er editorial:

- Burgundy blok.
- 12 px radius.
- 30 px 32 px padding.
- Eyebrow i red-mid.
- H1 i cream.
- Undertekst i stone-soft.
- Primær handling i rød.
- Sekundær handling som outline på mørk baggrund.

### KPI-række

Fire kompakte kort:

- hvid baggrund
- border
- 10 px radius
- shadow-sm
- 16 px 18 px padding
- label 12.5 px
- tal 34 px display
- kildelinje 11.5 px

Ingen tal må vises uden datakilde eller klar definition. Demo-tal skal komme fra seeddata med `is_demo=true`.

### Signalkort

- Grid med to kolonner på desktop.
- Hvid baggrund.
- 3 px rød topkant.
- Metadata: kategori, horizon, relevans og evidens.
- Titel i display 22 px.
- Kort resumé.
- Use-case chips eller mini-flow.
- Anbefaling og “Åbn signal”.

### Opportunity-preview

Fire kompakte kort, hvis data findes. Ellers vises et tydeligt empty state.

### Adoption-overblik

Landefordeling og seneste cases må vises, men alle counts beregnes fra API-data og må ikke hardcodes.

---

## 12. AI-adoption

### Header og KPI'er

Følg samme typografiske hierarki som prototypen.

### Filterbar

- Hvid kortflade.
- 14 px 16 px padding.
- Gap 12 px.
- Labels 11 px uppercase.
- Filtre arbejder sammen med AND-logik.

MVP-filtre:

- land
- branche
- capability
- implementeringsstatus
- dokumentationsstyrke

### Kortvisning

Casekort viser:

- virksomhed
- land og branche
- capability
- use case
- status
- platform/vendor, hvis dokumenteret
- effekt eller “Ingen dokumenteret effekt fundet”
- evidens
- potentiel læring markeret som analyse

### Tabelvisning

Kolonner:

- Virksomhed
- Land
- Branche
- Capability
- Use case
- Status
- Evidens
- Åbn

### Empty state

“Der er ingen dokumenterede cases, som matcher de valgte filtre.”

---

## 13. Teknologiradar

### Horizon-board

Tre kolonner:

- NU
- NÆSTE
- HORIZON

NU og NÆSTE er lyse. HORIZON er burgundy i desktop-layoutet. Teknologier vises som klikbare rækker med navn, modenhedsindikator og antal dokumenterede cases.

### Teknologikort

Viser:

- navn
- horizon
- definition
- modenhed
- adoption
- momentum
- case count
- relevans
- evidens
- anbefaling

De enkelte dimensioner må ikke kombineres i én opaque score.

---

## 14. Opportunities

### Pipeline

Seks trin:

- Identificeret
- Undersøges
- Business case
- Pilot
- Skalering
- Afsluttet

### Kort

- Titel og status.
- Problem som fakta-/problemblok med solid venstrekant.
- Hypotese som stiplet analyseblok.
- Værdi-tags.
- Modenhed, adoption og dokumentation som separate felter.
- Status og næste handling.

Ingen KPI eller status må udledes fra prototypekonstanter i production.

---

## 15. Review UI

Review er et nyt produktionsområde, som ikke var fuldt designet i prototypepakken. Det skal visuelt følge det samme system.

### Layout

Desktop two-pane:

- Venstre: dokument, metadata og originalt evidensuddrag.
- Højre: foreslåede claims og reviewhandlinger.

### Claim-review-card

Viser:

- claim type
- subject, predicate og object
- evidensuddrag
- foreslåede entities
- confidence som sorteringshjælp, aldrig sandhedsindikator
- mulige dubletter eller konflikter

Handlinger:

- Godkend
- Ret og godkend
- Kræver yderligere dokumentation
- Afvis
- Markér mulig dublet
- Markér mulig konflikt

Godkendelse må ikke ske uden synligt evidensuddrag.

---

## 16. Kilder og provenance

### Source overview

- aktive kilder
- seneste kontrol
- retrieval method
- adgangsklasse
- status
- antal dokumenter/signaler

### Provenance

Et publiceret signal skal kunne åbne:

1. Signal.
2. Underliggende claims.
3. Evidensuddrag pr. claim.
4. Dokumentmetadata.
5. Original kilde eller sikker filreference.

Flere artikler med samme oprindelse må ikke visuelt fremstilles som uafhængige beviser.

---

## 17. Drawer

Drawer er det centrale mønster for relationer mellem entities.

### Adfærd

- Åbnes fra højre.
- Maksimal bredde 700 px eller 94vw.
- Overlay i `rgba(35,0,13,0.34)`.
- Sticky header.
- Stakbaseret navigation mellem relaterede entities.
- Tilbageknap vises ved stakdybde over 1.
- Escape lukker.
- Fokus fastholdes i drawer.
- Fokus returneres til trigger ved luk.
- URL skal, hvor praktisk, afspejle den åbne entity.

### Sektionstyper

- fact
- analysis
- recommendation
- plain

Sektionstyperne følger de semantiske visuelle mønstre i afsnit 8.

---

## 18. Briefing

MVP-briefing er en enkel, redigerbar view, ikke et fuldt planlægningssystem.

Den kan indeholde:

- titel
- periode
- målgruppe
- executive summary
- tre vigtigste udviklinger
- udvalgte signaler/cases/opportunities
- anbefalede næste skridt
- kilder

Det fulde prototypefeature-set med planlagte briefinger, historik og skabelonbibliotek er ikke påkrævet i første build.

---

## 19. Interaktioner

Skal fungere i MVP:

- navigation
- filtrering
- kort-/tabelvisning på adoption
- åbning af signal, virksomhed, case, teknologi, opportunity og source
- stakbaseret drawer-navigation
- reviewhandlinger
- opportunity-oprettelse og statusændring
- tilføjelse til enkel briefing
- toasts ved succes og fejl

Kan være simple eller deaktiverede i MVP:

- notifikationscenter
- gemte filtre
- følg virksomhed
- leverandørsammenligning
- planlagte briefinger
- avanceret eksport
- ændring af horizon direkte fra technology profile

Deaktiverede funktioner må ikke foregive at være gennemført. Brug tydelig tekst som “Ikke en del af MVP”.

---

## 20. Animation og feedback

### Page entry

```css
@keyframes arIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}
```

Varighed: 260 ms. Easing: `cubic-bezier(0.2, 0, 0.2, 1)`.

### Drawer entry

```css
@keyframes arPanel {
  from { opacity: 0; transform: translateX(24px); }
  to { opacity: 1; transform: none; }
}
```

Varighed: 260 ms. Samme easing.

Respektér `prefers-reduced-motion`. Ingen bounce, spring eller parallax.

### Toast

- Burgundy baggrund.
- Cream tekst.
- Red-mid statusprik.
- `aria-live="polite"`.
- Må ikke være eneste feedback ved kritiske fejl.

---

## 21. Responsive regler

### 1440 px og større

- Fuld sidebar.
- Fire KPI-kolonner.
- To signal-kolonner.
- Tre til fire card-kolonner afhængigt af view.

### 1024 til 1439 px

- Fuld eller kompakt sidebar.
- To KPI-kolonner ved behov.
- To card-kolonner.
- Topbarfiltre kan wrappe eller flyttes til filterpanel.

### Under 1024 px

- Navigation som overlay eller compact rail.
- Én til to card-kolonner.
- Tabeller med scroll eller card-alternativ.
- Drawer kan bruge fuld viewportbredde.

---

## 22. Accessibility

Minimum WCAG 2.1 AA.

- Synlig `:focus-visible`: 2 px red outline, 2 px offset.
- Korrekte headingniveauer.
- `aria-current="page"` i navigation.
- `role="dialog"`, label, focus trap og Escape i drawer.
- `scope="col"` og `scope="row"` i tabeller.
- Ikonknapper har labels.
- Status kommunikeres med tekst/symbol og ikke kun farve.
- Primære klikmål er minimum cirka 38 px høje.
- Reduced-motion understøttes.
- Kontrast kontrolleres med de faktiske fonte og størrelser.

---

## 23. Data- og API-binding

UI'et må ikke afhænge af prototypefelter som `co`, `cap`, `st` eller navnebaserede relationer.

Brug ID-baserede typed view models fra Technical Master, eksempelvis:

```ts
type SignalCardViewModel = {
  id: string
  title: string
  summary: string
  horizon: 'now' | 'next' | 'horizon'
  documentationLevel: 'strong' | 'limited' | 'early' | 'conflicting'
  recommendation?: string
  technologyIds: string[]
  companyIds: string[]
}
```

Alle tællere beregnes fra API-data. Hardcodede tal må kun eksistere i markerede fixtures eller seeddata.

---

## 24. CSS- og stylingstrategi

Anbefalet:

- global tokenfil
- global reset/base styles
- CSS Modules eller Tailwind med CSS-variable mapping
- ingen tilfældige utility-farver uden for tokens
- style-varianter implementeres gennem typed component variants

Hvis Tailwind anvendes, mappes brand tokens i theme/config, men CSS-variablerne forbliver den autoritative tokenkilde.

Claude Code skal stage en rigtig tokenfil i repositoryet som en del af første UI-slice. Filen skal ikke ligge som en ekstern løs reference.

---

## 25. Filer, der skal findes i repositoryet

Minimum:

```text
apps/web/src/styles/tokens.css
apps/web/src/styles/globals.css
apps/web/src/components/layout/app-shell.tsx
apps/web/src/components/layout/sidebar.tsx
apps/web/src/components/layout/topbar.tsx
apps/web/public/fonts/README.md
```

`apps/web/public/fonts/README.md` skal forklare, at OKfamily og Fellix skal leveres fra OK's licenserede brandpakke, og hvilke filnavne applikationen forventer.

Den oprindelige `colors_and_type.css` kan arkiveres under `docs/design-reference/`, men production-imports skal pege på den staged tokenfil i webapplikationen.

---

## 26. MVP-prioritering af UI

### Bygges fuldt nu

1. App shell, sidebar og topbar.
2. Overblik.
3. AI-adoption.
4. Teknologiradar.
5. Opportunities.
6. Kilder og provenance.
7. Review Queue.
8. Entity drawers.
9. Centrale loading-, empty-, error- og unauthorized states.

### Bygges enkelt

- Briefing.
- Use-case relationer/profiler.
- Vendor relationer/profiler.

### Bygges ikke fuldt endnu

- Leverandørsammenligning.
- Planlagte briefinger.
- Notifikationscenter.
- Gemte filtre.
- Follow-funktioner.
- Avanceret eksport.

---

## 27. UI acceptance criteria

UI-slicen er færdig, når:

1. Ingen centrale sider bruger neutrale placeholder-tokens.
2. Brandfarverne er staged i en central tokenfil.
3. OKfamily og Fellix anvendes, når filer findes, med godkendte fallbacks ellers.
4. Layoutet matcher referenceprototypens overordnede proportioner ved cirka 1440 px.
5. Sidebar, topbar, cards, tabeller, badges og drawer følger specifikationen.
6. Fakta, analyse og anbefaling er visuelt og semantisk adskilt.
7. Evidence og verification kommunikeres med både tekst/symbol og farve.
8. Den primære brugerrejse fungerer fra signal til evidence og opportunity.
9. UI'et bruger API-view models og ikke prototypekonstanter i production.
10. Loading-, empty-, error-, partial- og unauthorized states er implementeret.
11. Desktop og laptop fungerer uden layoutbrud.
12. Focus, keyboard og drawer-adfærd er tilgængelig.
13. Demo-data er tydeligt adskilt fra production intelligence.
14. Buildet fungerer uden de licenserede fontfiler, men rapporterer manglende fontfidelity tydeligt.

---

## 28. Endelig besked til Claude Code

Implementér UI'et fra denne fil som den autoritative UI-kontrakt. Brug `AI Radar.dc.html` til visuel sammenligning og detaljer, men følg det reducerede og opdaterede scope i Product Master og Technical Master.

Stage brand tokens i kodebasen med det samme. Vent ikke på en separat CSS-upload for farver, spacing, radius og shadows, da de nødvendige tokens er defineret her. Fontfiler er den eneste brandressource, der fortsat skal leveres separat fra OK's licenserede brandpakke.

Byg ikke prototypefunktioner, der er eksplicit ude af MVP. Bevar designet og den centrale oplevelse:

**Opdag → Forstå → Kontrollér dokumentation → Vurdér → Prioritér → Handl**
