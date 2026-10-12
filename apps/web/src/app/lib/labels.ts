import type { DocumentationLevel, SignalStatus } from "./api";

// Dokumentationsstyrke (Product Master §11) — vises altid med tekst,
// aldrig kun farve.
export const DOCUMENTATION_LABELS: Record<DocumentationLevel, string> = {
  strong: "Stærk dokumentation",
  limited: "Begrænset dokumentation",
  early: "Tidligt signal",
  conflicting: "Modstridende",
};

// Farver følger evidens-/statusdesignet (UI Master §9); labelteksten
// bærer altid betydningen — farve er aldrig eneste signal.
export function documentationBadgeClass(level: DocumentationLevel): string {
  const byLevel: Record<DocumentationLevel, string> = {
    strong: "badge badge-doc-strong",
    limited: "badge badge-doc-limited",
    early: "badge badge-doc-early",
    conflicting: "badge badge-doc-conflicting",
  };
  return byLevel[level];
}

export const SIGNAL_STATUS_LABELS: Record<SignalStatus, string> = {
  draft: "Kladde",
  published: "Publiceret",
  archived: "Arkiveret",
};

export function formatDateTime(value: string | null): string {
  if (!value) return "–";
  return new Intl.DateTimeFormat("da-DK", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Copenhagen",
  }).format(new Date(value));
}

export const SOURCE_TYPE_LABELS: Record<string, string> = {
  primary: "Primær",
  independent_analysis: "Uafhængig analyse",
  vendor_case: "Leverandørcase",
  vendor_claim: "Leverandørudsagn",
  media: "Medie",
  research: "Forskning",
  early_signal: "Tidligt signal",
};

// Claim-predicates på dansk. Rækkefølgen er visningsrækkefølgen i en
// faktagruppe: tilbud, brug, fase, effekt, problemer, organisering.
export const PREDICATE_LABELS: Record<string, string> = {
  OFFERS_CAPABILITY: "Tilbyder",
  OFFERS_IN_MARKET: "Sælger i",
  SUPPORTS_LANGUAGE: "Understøtter sprog",
  USES_CAPABILITY: "Bruger",
  USES_TECHNOLOGY: "Bruger teknologi",
  USES_VENDOR: "Bruger leverandør",
  USES_FOR: "Bruger AI til",
  ADOPTION_STAGE: "Fase",
  REPORTED_EFFECT: "Rapporteret effekt",
  REPORTS_BARRIER: "Barriere",
  REPORTS_NEGATIVE_OUTCOME: "Negativt udfald",
  ABANDONED_OR_REPLACED: "Stoppet eller udskiftet",
  USES_GOVERNANCE_MODEL: "Styring",
  USES_HUMAN_REVIEW: "Menneskelig kontrol",
  REPORTS_ADOPTION_APPROACH: "Tilgang til indførelse",
  REPORTS_DATA_FOUNDATION: "Datagrundlag",
};

export function predicateLabel(predicate: string): string {
  return PREDICATE_LABELS[predicate] ?? predicate;
}

export const STAGE_LABELS: Record<string, string> = {
  Experiment: "Eksperiment",
  Pilot: "Pilot",
  Production: "I drift",
  Scale: "Skaleret",
  Unknown: "Ukendt",
};

/** Leverandørens egne ord — tal og påstande er leverandørens. */
export function isVendorSource(sourceType: string | null): boolean {
  return sourceType === "vendor_case" || sourceType === "vendor_claim";
}
