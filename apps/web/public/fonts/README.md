# Fonte — OKfamily og Fellix

OKfamily (display) og Fellix (body/UI) er licenserede og skal leveres fra
OK's godkendte brandpakke. De må ikke hentes fra en tilfældig ekstern
kilde (UI Master §4).

Applikationen forventer disse filnavne i denne mappe:

```text
OKfamily-Light.ttf
OKfamily-Regular.ttf
OKfamily-Medium.ttf
OKfamily-Semibold.otf
OKfamily-Bold.ttf
Fellix-Light.ttf
Fellix-Regular.ttf
Fellix-SemiBold.otf
```

Når filerne er staged, aktiveres de centralt med `next/font/local` (se
kommentaren i `src/app/layout.tsx`). Indtil da bygger appen med de
godkendte fallbacks fra tokens (`--font-display`: Georgia/Times-serif;
`--font-body`: Inter/Helvetica/Arial/system-ui) — buildet må ikke fejle
på manglende fontfiler, men **pixel-fidelity kan først accepteres, når de
licenserede fontfiler er tilført.**
