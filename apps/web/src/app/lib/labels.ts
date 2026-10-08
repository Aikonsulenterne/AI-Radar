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

/** Leverandørens egne ord — tal og påstande er leverandørens. */
export function isVendorSource(sourceType: string | null): boolean {
  return sourceType === "vendor_case" || sourceType === "vendor_claim";
}
